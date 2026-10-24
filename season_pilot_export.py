"""Download only 2024 rounds 1/2 Q and R; audit fields, never calculate pace.

Run in a fresh shell: env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1
.venv/bin/python -B season_pilot_export.py --download
All raw data and request records stay in the new gitignored season cache.
"""
import argparse
import json
from pathlib import Path
import pickle
import re
import shutil
import signal
import sqlite3
import subprocess
import time
from urllib.parse import urlsplit

import fastf1
from fastf1.ergast import Ergast
import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "cache/season_2024"
EXPORTS = CACHE / "pilot_exports"
LIMIT = 200_000_000  # Decimal MB; includes raw exports and cache overhead.
SECONDS = 15 * 60
EXPECTED = [(1, "Bahrain Grand Prix"), (2, "Saudi Arabian Grand Prix")]
SCHEDULE_URL = "https://raw.githubusercontent.com/theOehrly/f1schedule/master/schedule_2024.json"
FEEDS = {"SessionInfo.jsonStream", "DriverList.jsonStream", "SessionStatus.jsonStream",
         "LapCount.jsonStream", "TrackStatus.jsonStream", "TimingData.jsonStream",
         "TimingAppData.jsonStream", "WeatherData.jsonStream", "RaceControlMessages.jsonStream"}
LAP_FIELDS = "DriverNumber LapNumber LapTime Compound TyreLife Stint PitInTime PitOutTime Time LapStartTime TrackStatus Deleted FastF1Generated IsAccurate".split()


class PilotStop(BaseException):
    """Must escape FastF1's optional-feed exception handlers immediately."""


def size():
    return sum(p.stat().st_size for p in CACHE.rglob("*") if p.is_file())


class NetworkGuard:
    def __init__(self):
        self.prefixes = set()
        self.started = time.monotonic()
        self.requests = []
        self.attempts = {}

    def check(self, *_):
        if size() > LIMIT:
            raise PilotStop("Cache exceeded 200 MB; pilot stopped")
        if time.monotonic() - self.started > SECONDS:
            raise PilotStop("Current session exceeded 15 minutes; pilot stopped")

    def allowed(self, url):
        parsed = urlsplit(url)
        base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if base == SCHEDULE_URL:
            return True
        if parsed.scheme != "https":
            return False
        if parsed.netloc == "api.jolpi.ca":
            return bool(re.fullmatch(r"/ergast/f1/2024/[12]/(?:results|qualifying|laps/1)\.json", parsed.path))
        if parsed.netloc in {"livetiming.formula1.com", "livetiming-mirror.fastf1.dev"}:
            prefix, _, filename = parsed.path.rpartition("/")
            return prefix + "/" in self.prefixes and filename in FEEDS
        return False

    def install(self):
        original = requests.sessions.Session.send
        guard = self

        def send(session, request, **kwargs):
            if request.method != "GET" or not guard.allowed(request.url):
                raise PilotStop(f"Refused out-of-scope request: {request.method} {request.url}")
            # FastF1 initiates every request. This wrapper only restricts scope,
            # applies a timeout and retries failures sequentially (1, 2, 4 s).
            kwargs["timeout"] = (20, 60)
            session.get_adapter(request.url).max_retries = requests.adapters.Retry(total=0)
            while True:
                guard.check()
                attempt = guard.attempts.get(request.url, 0) + 1
                guard.attempts[request.url] = attempt
                if attempt > 4:
                    raise PilotStop(f"Retry budget exhausted: {request.url}")
                began = time.monotonic()
                try:
                    response = original(session, request, **kwargs)
                    response.raise_for_status()
                    guard.requests.append(dict(url=request.url, attempt=attempt,
                        status=response.status_code, seconds=time.monotonic()-began))
                    guard.check()
                    return response
                except requests.RequestException as exc:
                    guard.requests.append(dict(url=request.url, attempt=attempt,
                        error=str(exc), seconds=time.monotonic()-began))
                    if attempt == 4:
                        raise PilotStop(f"Repeated request failure: {request.url}: {exc}") from exc
                    time.sleep(2 ** (attempt-1))
        requests.sessions.Session.send = send
        signal.signal(signal.SIGALRM, self.check)
        signal.setitimer(signal.ITIMER_REAL, .25, .25)


def export(frame, filename):
    with (EXPORTS / filename).open("x", newline="") as stream:
        pd.DataFrame(frame).to_csv(stream, index=False)


def cached_status(number):
    """Use the same requests-cache dictionary/URL layout as prediction's reader."""
    rows = []
    url = f"https://api.jolpi.ca/ergast/f1/2024/{number}/results.json"
    uri = (CACHE / "fastf1_http_cache.sqlite").as_uri() + "?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True) as connection:
        for (blob,) in connection.execute("SELECT value FROM responses"):
            response = pickle.loads(blob)
            if response.get("url") != url:
                continue
            for race in json.loads(response["_content"])["MRData"]["RaceTable"]["Races"]:
                for entry in race["Results"]:
                    rows.append(dict(driver=entry["Driver"]["code"], status=entry["status"],
                                     position=int(entry["position"]), source_url=url))
    return pd.DataFrame(rows, columns=["driver", "status", "position", "source_url"])


def audit(session, number, code, rows, rosters, issues):
    """Count missing/duplicate/invalid records without dropping a single lap."""
    def count(metric, value, group=""):
        rows.append(dict(round_number=number, session=code, group=group, metric=metric, count=int(value)))

    results = pd.DataFrame(session.results)
    laps = pd.DataFrame(session.laps)
    track = pd.DataFrame(session.track_status)
    messages = pd.DataFrame(session.race_control_messages)
    status = pd.DataFrame(session.session_status)
    count("session_present", 1)
    count("entrants", len(results))
    count("duplicate_driver_keys", results.DriverNumber.duplicated(keep=False).sum())
    count("missing_driver_identity", results[["DriverNumber", "Abbreviation", "TeamName"]].isna().any(axis=1).sum())
    rosters[f"{number}{code}"] = {team: sorted(group.Abbreviation.tolist())
                                for team, group in results.groupby("TeamName")}
    for team, group in results.groupby("TeamName"):
        count("entrants_per_team", len(group), team)
    for name, frame in [("laps", laps), ("track_status", track), ("messages", messages), ("session_status", status)]:
        count(name + "_rows", len(frame))
    for field in LAP_FIELDS:
        count("field_present_" + field, field in laps)
        if field in laps:
            count("missing_" + field, laps[field].isna().sum())
    count("duplicate_driver_lap_keys", laps.duplicated(["DriverNumber", "LapNumber"], keep=False).sum())
    seconds = laps.LapTime.dt.total_seconds()
    count("nonpositive_recorded_lap_times", seconds.le(0).sum())
    count("nonfinite_recorded_lap_times", (seconds.notna() & ~np.isfinite(seconds)).sum())
    count("unknown_compound", (~laps.Compound.isin(["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"])).sum())
    count("invalid_recorded_tyre_age", (laps.TyreLife.notna() & (laps.TyreLife.lt(1) | ~np.isfinite(laps.TyreLife))).sum())
    count("invalid_recorded_stint", (laps.Stint.notna() & (laps.Stint.lt(1) | ~np.isfinite(laps.Stint))).sum())
    count("deleted_laps", laps.Deleted.eq(True).sum())
    count("generated_laps", laps.FastF1Generated.eq(True).sum())
    count("inaccurate_laps", laps.IsAccurate.eq(False).sum())
    count("unknown_track_status", (~laps.TrackStatus.astype(str).str.fullmatch(r"[1-7]+")).sum())
    for label, frame, fields in [("track", track, ["Time", "Status"]),
                                 ("message", messages, ["Time", "Message"]),
                                 ("session", status, ["Time", "Status"])]:
        for field in fields:
            count(f"{label}_field_present_{field}", field in frame)
    if code == "Q":
        parts = session.laps.split_qualifying_sessions()
        indexes = []
        for q, part in enumerate(parts, 1):
            count(f"q{q}_partition_present", part is not None)
            count(f"q{q}_partition_laps", 0 if part is None else len(part))
            count(f"q{q}_classified_missing_time", results[f"Q{q}"].isna().sum())
            if part is not None:
                indexes.extend(part.index.tolist())
        count("qualifying_unpartitioned_laps", len(set(laps.index) - set(indexes)))
        count("qualifying_partition_overlap", len(indexes) - len(set(indexes)))
        count("weather_requested", 0)
    else:
        weather = pd.DataFrame(session.weather_data)
        count("weather_requested", 1)
        count("weather_rows", len(weather))
        start = status.loc[status.Status.eq("Started"), "Time"].min()
        end = max(status.loc[status.Status.eq("Finished"), "Time"].max(), laps.Time.max())
        count("missing_session_boundaries", pd.isna(start) + pd.isna(end))
        samples = weather.dropna(subset=["Time"]).sort_values("Time")
        before = samples.loc[samples.Time.le(start)].tail(1)
        during = samples.loc[samples.Time.gt(start) & samples.Time.le(end)]
        selected = pd.concat([before, during]).drop_duplicates("Time")
        count("weather_missing_rainfall", weather.Rainfall.isna().sum())
        count("weather_start_edge_over_120s", before.empty or (start-before.Time.iloc[0]).total_seconds() > 120)
        count("weather_end_edge_over_120s", selected.empty or (end-selected.Time.iloc[-1]).total_seconds() > 120)
        count("weather_internal_gaps_over_180s", selected.Time.diff().gt(pd.Timedelta(seconds=180)).sum())
        official = cached_status(number)
        count("cached_status_rows", len(official))
        count("cached_status_duplicate_drivers", official.driver.duplicated(keep=False).sum())
        merged = results.merge(official, left_on="Abbreviation", right_on="driver", how="outer", indicator=True)
        count("result_status_roster_mismatches", merged._merge.ne("both").sum())
        count("result_status_position_mismatches", (merged._merge.eq("both") & merged.Position.ne(merged.position)).sum())
        count("missing_official_status", merged.status.isna().sum())
        count("result_status_label_mismatches", (merged._merge.eq("both") & merged.Status.ne(merged.status)).sum())
        for value, total in official.status.value_counts().items():
            count("finishing_status_count", total, value)
        export(official, f"2024_{number:02d}_official_statuses.csv")
        export(weather, f"2024_{number:02d}_{code}_weather.csv")
    for name, frame in [("results", results), ("laps", laps), ("track_status", track),
                         ("messages", messages), ("session_status", status)]:
        export(frame, f"2024_{number:02d}_{code}_{name}.csv")
    # Null lap times and pit timestamps are reported, not declared invalid by
    # default: an out-lap or non-pit lap naturally lacks some such fields.
    for row in rows:
        if row["round_number"] == number and row["session"] == code and row["count"]:
            metric = row["metric"]
            if any(word in metric for word in ["duplicate", "mismatch", "unknown", "invalid", "nonpositive", "unpartitioned", "overlap", "over_120s", "over_180s"]):
                issues.append(f"Round {number} {code}: {metric} = {row['count']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", required=True,
                        help="Explicitly run the two-round pilot, never another round")
    parser.parse_args()
    if CACHE.exists() or (ROOT / "data/2024/pilot_completeness.csv").exists():
        raise SystemExit("Pilot output already exists; refusing to overwrite or refresh it")
    ignored = subprocess.run(["git", "check-ignore", "cache/season_2024/"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.strip()
    free = shutil.disk_usage(ROOT).free
    print(f"Ignored: {ignored}; free bytes: {free}", flush=True)
    if free < 2_000_000_000:
        raise SystemExit("Less than 2 GB free; stopped before any download")
    EXPORTS.mkdir(parents=True)
    fastf1.Cache.enable_cache(str(CACHE))
    fastf1.Cache.offline_mode(False)
    guard = NetworkGuard()
    guard.install()
    summary = dict(rounds=[], sessions=[], rosters={}, issues=[], requests=guard.requests,
                   free_bytes_before=free, ignored=ignored, cache_initial_bytes=size())
    rows = []
    began = time.monotonic()
    try:
        before = size()
        schedule = fastf1.get_event_schedule(2024, include_testing=False, backend="fastf1")
        first = schedule.sort_values("RoundNumber").head(2)
        opening = [(int(event.RoundNumber), event.EventName) for _, event in first.iterrows()]
        if opening != EXPECTED:
            raise PilotStop(f"Unexpected opening calendar: {opening}; no sessions downloaded")
        summary["calendar"] = opening
        summary["schedule_bytes"] = size() - before
        summary["schedule_seconds"] = time.monotonic() - began
        print("Verified opening rounds:", opening, flush=True)
        # Session constructors use the verified schedule, never another year.
        for _, event in first.iterrows():
            for code in ("Q", "R"):
                session = event.get_session(code)
                guard.prefixes.add(session.api_path)
        for _, event in first.iterrows():
            round_start, round_size = time.monotonic(), size()
            number = int(event.RoundNumber)
            for code in ("Q", "R"):
                guard.started = time.monotonic()
                session_size = size()
                session = event.get_session(code)
                print(f"Loading 2024 round {number} {code}", flush=True)
                record = dict(round_number=number, race=event.EventName, session=code)
                summary["sessions"].append(record)
                session.load(laps=True, telemetry=False, weather=code == "R", messages=True)
                if code == "R":
                    # Same FastF1 Ergast/Jolpica interface used by Session.load;
                    # this normally reuses that load's cached result response.
                    Ergast().get_race_results(season=2024, round=number)
                record["load_seconds"] = time.monotonic() - guard.started
                record["cache_growth_bytes"] = size() - session_size
                audit(session, number, code, rows, summary["rosters"], summary["issues"])
                record["cache_and_exports_growth_bytes"] = size() - session_size
                record["total_seconds"] = time.monotonic() - guard.started
                guard.check()
                print("Completed:", record, flush=True)
            summary["rounds"].append(dict(round_number=number, race=event.EventName,
                seconds=time.monotonic()-round_start, growth_bytes=size()-round_size))
        summary["outcome"] = "completed"
    except (PilotStop, Exception) as exc:
        summary["outcome"] = "stopped"
        summary["issues"].append(f"{type(exc).__name__}: {exc}")
        print("STOP:", str(exc), flush=True)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        summary["elapsed_seconds"] = time.monotonic()-began
        summary["cache_bytes_before_summary"] = size()
        with (EXPORTS / "2024_pilot_run.json").open("x") as stream:
            json.dump(summary, stream, indent=2)
        destination = ROOT / "data/2024/pilot_completeness.csv"
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("x") as stream:
            pd.DataFrame(rows, columns=["round_number", "session", "group", "metric", "count"]).to_csv(stream, index=False)
    if summary["outcome"] != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

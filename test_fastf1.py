import argparse
from pathlib import Path

from season_config import DEFAULT, add_season_arguments, from_args


import fastf1


def write_results(results, path):
    """Exclusive creation means a repeat export cannot erase an earlier result."""
    with Path(path).open("x", newline="") as stream:
        results.to_csv(stream, index=False)


def main():
    parser = argparse.ArgumentParser(description="Export race results without overwriting earlier files")
    add_season_arguments(parser)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    cfg = from_args(args)
    year = cfg.year
    cache_folder = cfg.path("cache")
    data_folder = cfg.path("data")
    cache_folder.mkdir(parents=True, exist_ok=True)
    data_folder.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_folder))
    fastf1.Cache.offline_mode(args.offline)

    # Testing events are not races, so leave them out of the calendar.
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    if len(schedule) != cfg.facts["round_count"]:
        raise ValueError("Schedule length differs from the verified manifest")
    columns = ["Abbreviation", "TeamName", "GridPosition", "Position"]
    saved = 0
    total_rows = 0
    failed = []

    for _, event in schedule.iterrows():
        round_number = int(event["RoundNumber"])
        race_name = event["EventName"]
        try:
            session = fastf1.get_session(year, round_number, "R")
            # Load results without the extra lap, telemetry, or weather data.
            session.load(laps=False, telemetry=False, weather=False, messages=False)
            results = session.results[columns]
            if results.empty or results["Position"].isna().any():
                raise ValueError("Race results are missing or incomplete")

            filename = cfg.facts["paths"]["result_pattern"].format(round=round_number, race=race_name.replace(" ", "_"))
            write_results(results, cfg.checked(data_folder / filename, published=True))
            saved += 1
            total_rows += len(results)
            print(f"Saved {race_name}: {len(results)} drivers")
        except Exception as error:
            # Keep going so one failed download does not stop the season.
            failed.append(race_name)
            print(f"Failed {race_name}: {error}")

    print(
        f"\nFinished {year}: saved {saved}/{len(schedule)} races "
        f"({total_rows} driver results) to {data_folder}. "
        f"Failed: {len(failed)}."
    )
    if failed:
        print("Races to retry: " + ", ".join(failed))


if __name__ == "__main__":
    main()

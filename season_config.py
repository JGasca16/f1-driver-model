"""Season facts and protected paths. Statistical choices stay in the methods."""
from dataclasses import dataclass
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parent
METHOD_ID = "2025_teammate_rating_1_log_round_fix"
REQUIRED = ("season method_id round_count expected_entries team_size expected_appearances "
            "expected_unique_drivers registry_verified roster_verified qualifying_disqualifications "
            "wet_races dry_rounds dry_holdouts roster_periods qualifying_summary qualifying_advancement "
            "legacy_parity_required miami_audit charts paths files chart_files run_prefixes allowlist").split()


def unknowns(value, prefix=""):
    if value == "UNVERIFIED":
        return [prefix]
    if isinstance(value, dict):
        return [p for k, v in value.items() for p in unknowns(v, f"{prefix}.{k}".strip("."))]
    if isinstance(value, list):
        return [p for i, v in enumerate(value) for p in unknowns(v, f"{prefix}[{i}]")]
    return []


@dataclass(frozen=True)
class SeasonConfig:
    facts: dict
    root: Path
    manifest: Path

    @property
    def year(self):
        return self.facts["season"]

    def require_verified(self):
        missing = sorted(set([k for k in REQUIRED if k not in self.facts] + unknowns(self.facts)))
        if missing:
            raise ValueError(f"Season {self.year} has UNVERIFIED required facts: " + ", ".join(missing))
        if not self.facts["charts"]["pairs"]:
            raise ValueError(f"Season {self.year}: no verified selected chart pairs")
        if not self.facts["registry_verified"] or not self.facts["roster_verified"]:
            raise ValueError("Season roster and disqualification registries must be verified")
        if self.facts["method_id"] != METHOD_ID:
            raise ValueError("The approved algorithm identifier cannot change")
        rounds = set(range(1, self.facts["round_count"] + 1))
        wet = {int(n) for n in self.facts["wet_races"]}
        dry = set(self.facts["dry_rounds"])
        held = {r["round"] for r in self.facts["dry_holdouts"]}
        if dry & wet or dry & held or wet & held or (dry | wet | held) != rounds:
            raise ValueError("Dry, wet and held-out rounds must cover the verified schedule")
        if self.facts["miami_audit"].get("status") not in (
                "documented_holdout", "conflict_absent", "conflict_found"):
            raise ValueError("Miami compound/pit audit is unverified; manual review required")
        if not self.facts["miami_audit"].get("evidence"):
            raise ValueError("Miami audit needs a saved evidence reference")
        if self.facts["team_size"] != 2:
            raise ValueError("Singleton/substitute roster schema is not implemented; audit required")
        return self

    def checked(self, path, *, published=False):
        path = Path(path)
        resolved = (path if path.is_absolute() else self.root / path).resolve()
        allowed = [(Path(tempfile.gettempdir()) if p == "{temp}" else self.root / p).resolve()
                   for p in self.facts["allowlist"]]
        if not any(resolved.is_relative_to(p) for p in allowed):
            raise ValueError(f"Path outside season {self.year} allowlist: {resolved}")
        if self.year != 2025:
            # These boundaries cannot be widened by a supplied manifest.
            boundaries = [self.root / f"data/{self.year}", self.root / f"charts/{self.year}",
                          self.root / f"cache/season_{self.year}"]
            # Check both lexical ownership and symlink-resolved ownership.
            lexical = path if path.is_absolute() else self.root / path
            if not any(lexical.is_relative_to(p) and resolved.is_relative_to(p.resolve())
                       and p.resolve() == p for p in boundaries):
                raise ValueError(f"Cross-season path refused: {resolved}")
            if any(str(y) in str(resolved.relative_to(self.root.resolve())) for y in (2025, 2026) if y != self.year):
                raise ValueError(f"Other-season path refused: {resolved}")
            if published and str(self.year) not in resolved.name:
                raise ValueError("Published filenames must contain the season year")
        # Keep logical paths for reproducible provenance, after checking symlinks.
        return path if path.is_absolute() else self.root / path

    def path(self, key):
        return self.checked(self.facts["paths"][key])

    def filename(self, key):
        name = self.facts["files"][key]
        if Path(name).name != name:
            raise ValueError("Output filename must be a basename")
        return name

    def sources(self):
        return tuple(str(self.input(k).relative_to(self.root))
                     for k in ("qualifying_rounds", "dry", "wet"))

    def input(self, key):
        return self.checked(self.path("data") / self.filename(key), published=True)

    def output(self, key, destination=None):
        return self.checked((self.path("data") if destination is None else self.checked(destination))
                            / self.filename(key), published=True)

    def run_name(self, name):
        return name if self.year == 2025 else f"{self.year}_{name}"

    def disqualifications(self, number):
        return {x["driver_number"]: x["reason"] for x in self.facts["qualifying_disqualifications"]
                if x["round"] == number}

    def holdout(self, race):
        return next((x for x in self.facts["dry_holdouts"] if x["race"] == race), None)


def load_season(season=2025, manifest=None, *, root=ROOT, require_verified=True):
    root = Path(root).resolve()
    manifest = Path(manifest) if manifest is not None else root / "seasons" / f"{season}.json"
    if not manifest.is_absolute():
        manifest = root / manifest
    facts = json.loads(manifest.read_text())
    if facts.get("season") != season:
        raise ValueError("Manifest season disagrees with requested season")
    cfg = SeasonConfig(facts, root, manifest.resolve())
    # Path validation is also available for an unverified skeleton, without I/O.
    for key in ("data", "charts", "cache", "runs", "results_glob", "cache_sqlite"):
        cfg.path(key)
    for key in facts["files"]:
        cfg.input(key)
    if require_verified:
        cfg.require_verified()
    return cfg


def add_season_arguments(parser):
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--manifest", type=Path)


def from_args(args):
    return load_season(args.season, args.manifest)


# Compatibility defaults for existing callers; CLI runs always load their own manifest.
DEFAULT = load_season()

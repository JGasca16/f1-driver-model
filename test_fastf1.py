from pathlib import Path

import fastf1


def main():
    year = 2025
    project_folder = Path(__file__).resolve().parent
    cache_folder = project_folder / "cache"
    data_folder = project_folder / "data"
    cache_folder.mkdir(exist_ok=True)
    data_folder.mkdir(exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_folder))

    # Testing events are not races, so leave them out of the calendar.
    schedule = fastf1.get_event_schedule(year, include_testing=False)
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

            filename = f"{year}_{round_number:02d}_{race_name.replace(' ', '_')}.csv"
            results.to_csv(data_folder / filename, index=False)
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

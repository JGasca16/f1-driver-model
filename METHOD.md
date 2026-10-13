# F1 Driver Performance Model

## Goal
Rank F1 drivers by how well they perform relative to their car, using
teammate comparisons, and test whether the ratings help predict race results.

## Data
FastF1 library, 2025 season only for version 1.

## Version 1 method
- Teammate % gap in qualifying
- Teammate race-pace gap on clean laps (drop pit laps, safety car laps, lap 1)
- DNFs labeled by hand: driver fault, car fault, or other
- Team gap in %, from a regression with a driver term and a team term

## Prediction test
Predict finishing position from qualifying and driver rating. Train on
earlier races, test on later ones. Compare against "finish where you started."

## Not in version 1
Luck vs skill, consistency, track-type effects, upgrade tracking
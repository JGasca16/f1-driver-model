# Miami compound investigation

Report only. Miami remains excluded from all regression and combined performance outputs. No existing lap data or CSV was changed.

## Finding

**54 known lap-compound labels conflict with the pit-aligned stint sequence, affecting 12 drivers.** These are additional to the 354 originally missing compound labels: all 354 proposed opening-stint recoveries agree with the same reconstruction, so none of those proposed recoveries conflict. There are 408 compound records needing recovery or correction in total.

Of the 54 known-label conflicts, 16 survive the existing individual clean-lap filter. Therefore excluding pit-in/out laps alone would not resolve the problem. There are also 403 known tyre-age values inconsistent with the pit-aligned source ages; these overlap compound issues and must not be added to the compound count.

Counts use non-generated lap records. Doohan has no non-generated completed race-lap records and is not in the per-driver lap table below. Unknown compounds are counted separately from conflicting known labels.

## Evidence and counting rule

- Read explicit per-driver, zero-based stint compounds and starting tyre ages from cached `timing_app_data.ff1pkl`. Each stint has one consistent recorded compound and starting age.
- Use recorded pit-in and following pit-out laps to locate the change: the in-lap belongs to the outgoing tyre set, the out-lap to the incoming set. A pit-lane start is not a tyre change. A retirement pit-in with no subsequent pit-out does not create a new stint.
- Check that each source stint's maximum total tyre laps minus its starting tyre age equals the reconstructed race-lap count. This check passes for every non-generated driver/stint in this race.
- Compare known derived `session.laps.Compound` labels against that reconstruction. Independently verify all 354 saved initial-stint recoveries against it.

| Driver | Pit-in laps | Source stint sequence | Originally unknown | Conflicting known compounds | Conflict lap numbers | Conflicting known tyre ages |
| --- | --- | --- | ---: | ---: | --- | ---: |
| ALB | 26 | MEDIUM → HARD | 24 | 6 | 27,28,29,30,31,32 | 33 |
| ALO | 28 | HARD → MEDIUM | 23 | 4 | 29,30,31,32 | 33 |
| ANT | 25 | MEDIUM → HARD | 24 | 7 | 26,27,28,29,30,31,32 | 33 |
| BEA | — | HARD | 23 | 0 | — | 4 |
| BOR | 19 | MEDIUM → HARD | 0 | 0 | — | 0 |
| GAS | 32 | HARD → MEDIUM | 23 | 0 | — | 9 |
| HAD | 22 | MEDIUM → HARD | 0 | 0 | — | 0 |
| HAM | 28 | HARD → MEDIUM | 23 | 4 | 29,30,31,32 | 34 |
| HUL | 36 | HARD → MEDIUM | 23 | 0 | — | 13 |
| LAW | 28,36 | HARD → MEDIUM | 23 | 3 | 29,30,31 | 13 |
| LEC | 29 | MEDIUM → HARD | 24 | 3 | 30,31,32 | 33 |
| NOR | 29 | MEDIUM → HARD | 24 | 3 | 30,31,32 | 33 |
| OCO | 23 | MEDIUM → HARD | 0 | 0 | — | 0 |
| PIA | 29 | MEDIUM → HARD | 24 | 3 | 30,31,32 | 33 |
| RUS | 29 | HARD → MEDIUM | 24 | 3 | 30,31,32 | 33 |
| SAI | 25 | MEDIUM → HARD | 24 | 7 | 26,27,28,29,30,31,32 | 33 |
| STR | 20 | MEDIUM → HARD | 0 | 0 | — | 0 |
| TSU | 27 | MEDIUM → HARD | 24 | 5 | 28,29,30,31,32 | 33 |
| VER | 26 | MEDIUM → HARD | 24 | 6 | 27,28,29,30,31,32 | 33 |

## Where the conflicts cluster

All known compound conflicts occur after the first tyre-changing stop, while the derived lap table still carries the outgoing compound. They end when the delayed compound label catches up. Verstappen, for example, pits on lap 26, leaves on lap 27 on the source's HARD stint, but the derived table retains MEDIUM through lap 32: six conflicting laps, 27–32.

For 11 affected drivers the delayed lap label changes on lap 33; Lawson's changes on lap 32. The source delivers a large timing-app update at session time 01:49:41.336, well after several of those stops. Its opening snapshot is at 01:35:31.226, around laps 23–24. These observations are consistent with snapshot arrival times being used as tyre-boundary times in the derived merge. That is a likely explanation, not a proven root-cause fix to FastF1.

## Proposed resolution rule

Use explicit driver/stint identity for compound and starting tyre age; use validated pit timing for when that stint applies. A timing-app update's arrival time should not overrule a matching earlier pit stop. Rebuild the whole timeline, including existing known labels and tyre ages, rather than patching missing compounds alone. Starting ages matter: Alonso and Stroll have used sets with one lap recorded, and Sainz starts with six recorded tyre laps.

Only accept this precedence when stint order, pit-in/out boundaries and source lap totals agree and there is no contradictory tyre-change evidence. If there are extra stops without tyre changes, multiple ambiguous stints, red-flag tyre changes, missing boundaries or inconsistent totals, leave the disputed interval unknown for manual review. Never assume every pit visit changes tyres. This race's reconstruction is supported by matching tyre-stint totals, not just by counting pit visits.

Write any future corrected lap dataset under a new name, preserving source provenance and original values. Run timeline checks and tests before lifting Miami's exclusion. No reconstructed Miami laps were fed into either regression in this task.

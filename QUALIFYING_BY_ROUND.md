# Qualifying teammate gaps for Q1, Q2 and Q3

This standalone addition reports each round separately and preserves the
existing selected-round reference. No points or wins are inputs. Existing
scripts, tests, documents and CSVs are unchanged. The driver rating proposal
is not part of this work.

## Run and outputs

```sh
.venv/bin/python qualifying_gaps_by_round.py --offline
```

Outputs:

- `data/2025_qualifying_gaps_by_round.csv`: 480 driver rows, representing 240
  unique teammate pairs across 24 main qualifying sessions.
- `data/2025_qualifying_round_session_evidence.csv`: cached race-control messages
  about actual red flags, lap decisions, investigations and session resumptions.
  An investigation message is not proof that a penalty was imposed.

Existing output names are protected. For another run, supply a new folder:

```sh
.venv/bin/python qualifying_gaps_by_round.py --offline --output-dir /tmp/quali-round-repeat
```

The script copies the original extraction logic rather than importing the old
script. It reads the old CSV only to check parity before publishing. That check
aborts publication if any legacy column differs. Without `--offline`, FastF1
may refresh cached data; a changed source may therefore fail parity and require
review. The script does not overwrite the baseline to make the check pass.

## Method and columns

Keep one row per driver per race, as in the original qualifying file. Every
pair appears twice, with each driver's own denominator. This is necessary to
retain both original perspectives; it is still only one independent pair
comparison. Summary counts below count each pair once, alphabetically.

For Q1, Q2 and Q3 independently, use each teammate's accepted best time in that
specific round. If both exist, compute:

`100 * (driver_seconds - teammate_seconds) / teammate_seconds`

Negative means the named driver was faster. Reverse-direction gaps need not
have identical magnitudes because their denominators differ. Never borrow a
time from another round to fill a round-specific gap. Main qualifying `Q` is
loaded on every weekend, including sprint weekends; sprint qualifying `SQ`/`SS`
is never loaded. Sprint weekends themselves remain in the export.

The first columns are the requested race/pair identifiers, `q1_gap` and
`q1_reason_code`, then the corresponding Q2 and Q3 columns, followed by
`selected_gap` and `selected_round`. These aliases reproduce the original
`gap_pct` and `qualifying_round`.

**All 19 original columns are also retained**, including selected comparison
times, overall best times, missing-time flags, advancement estimates, sources
and blank explanations. Nothing from the old reference table is discarded.
The resulting file has 51 columns. Additional per-round columns give each
driver's time, source, individual reason and whether advancement blocked raw
lap recovery. Readers can distinguish which driver caused a pair's blank.

Times and gaps are saved to six decimal places, matching the old CSV. The
selected gap still comes from the latest round with valid times for both
teammates. It is not an average of the three new gap columns.

## Times, advancement and recovery

Prefer positive finite classified Q1/Q2/Q3 times. For an individually missing
time, recover the fastest eligible recorded lap from that round where allowed:
positive lap time, `Deleted=False`, no pit-in/out timestamp and no generated
lap. Keep the original equal-time ordering: the first driver to set a tied
time takes priority. Do not replace an existing classified time with a faster
raw lap that may have been invalidated later.

Infer advancement using the original 2025 rules: fastest 15 from Q1 and fastest
10 from Q2, with classified times preferred. Later-round classified times also
establish advancement. Preserve raw times of subsequently disqualified drivers
in advancement ordering; excluding them afterward does not retrospectively
promote another driver into a session they never contested. Do not infer
advancement from the final qualifying position or starting-grid position.

Recovery needs valid advancement into that round. The source is recorded as
`results`, `laps`, `missing` or `excluded`. Missing/deleted information or an
entirely unavailable qualifying-round dataset stops publication rather than
being guessed. These are the existing extraction safeguards.

### Miami

The cached Miami classification lacks all Q1/Q2/Q3 times, so apply the same
per-round recovery rule to every driver. This run recovered **20 Q1 times,
15 Q2 times and 10 Q3 times**, giving **10, 6 and 4 usable teammate pairs**
respectively. Missing later-round entries are prior eliminations, not unresolved
recovery failures. No Miami round required a new recovery assumption in this run.
If future Miami data cannot pass these same safeguards, leave individual gaps
blank with the applicable reason or abort for missing whole-round data; do not
invent times or special Miami exceptions.

## Blank reason codes

A valid gap has an empty reason. Use this primary pair-reason priority:

1. `dsq`: either driver is covered by a confirmed whole-session qualifying
   exclusion in the copied 2025 registry.
2. `eliminated_prior_round`: at least one driver did not validly advance to
   this round and has no accepted time there.
3. `no_valid_lap`: both are otherwise eligible for the comparison round, but
   at least one has no accepted timed lap.

Both individual reasons remain available even when two failures coincide.
For example, one driver may be eliminated and the other may have reached the
round without a time; the pair's primary reason is `eliminated_prior_round`.
`no_valid_lap` does not guess whether the cause was a crash, withdrawal, deleted
attempt or failure to leave the pits. The inherited source/flag fields and
session evidence support further review.

## Open questions and implemented defaults for review

### 1. Prior elimination

**Default implemented, awaiting review:** Q1 elimination leaves Q2 and Q3
comparisons blank; Q2 elimination leaves Q3 blank. This follows the requested
expectation and avoids comparing unobserved performances. The original selected
gap can still use the earlier shared valid round. Carrying forward a Q1 time
would compare different track conditions and would not be a Q2/Q3 measurement,
so it is not used as an alternative here.

### 2. Grid penalties, lap cancellations and disqualifications

**Default implemented, awaiting review:** distinguish changes to grid position
from changes to valid qualifying times. A grid penalty alone does not invalidate
a timed lap. Keep accepted times in the rounds where they were recorded, even
when an incident in that round led to a later grid penalty. Do not treat a
pending investigation as a disqualification.

Examples verified against official Formula 1 starting-grid notes:

| Event and drivers | Recorded decision | Treatment |
| --- | --- | --- |
| Japan, Sainz | Three-place grid penalty for qualifying impeding | Keep valid Q1/Q2/Q3 times where present |
| Bahrain, Russell and Antonelli | One-place grid penalties for failing to follow the Race Director's instructions | Keep valid times; cached messages place the investigated garage-release incident around the Q2 resumption |
| Monaco, Hamilton | Three-place grid penalty for qualifying impeding | Keep valid times |
| Monaco, Stroll | One place for a practice collision and three places for qualifying impeding | Keep valid times |
| Monaco, Bearman | Ten-place grid penalty for overtaking under red flags in practice | Keep valid qualifying times |

Sources: [Japan grid notes](https://www.formula1.com/en/results/2025/races/1256/japan/starting-grid),
[Bahrain grid notes](https://www.formula1.com/en/results/2025/races/1257/bahrain/starting-grid),
[Monaco grid notes](https://www.formula1.com/en/results/2025/races/1261/monaco/starting-grid).
These are checked examples, not an exhaustive registry of every 2025 grid penalty.

The existing qualifying exclusion registry is retained unchanged:

- Ocon, Azerbaijan: rear-wing deflection infringement; all round times excluded.
- Albon and Sainz, Singapore: rear-wing/DRS technical infringement; all round
  times excluded for both drivers.

These are whole-session exclusions, not invented round-only disqualifications.
Their qualifying times are never restored from raw laps. The original sources
are [Azerbaijan classification](https://www.formula1.com/en/results/2025/races/1269/azerbaijan/qualifying)
and [Singapore exclusion report](https://www.formula1.com/en/latest/article/williams-drivers-disqualified-from-singapore-gp-qualifying-for-technical.hk0NFVQ3Wpp2hitKXdUhu).
FastF1's qualifying status fields do not reliably encode these decisions,
which is why the explicit registry is needed.

**Round-specific correction found:** Hülkenberg in Bahrain has raw Q2 laps but
his corrected Q1 classification leaves him outside valid advancement. His Q1
uses the accepted classified time; Q2 and Q3 remain blank with
`eliminated_prior_round`. `q2_driver_recovery_blocked=True` identifies the raw
Q2 evidence that was deliberately not restored. This is a lap-deletion and
advancement issue, not a whole-session `dsq`. The cached control messages
include the subsequent deletion of his 1:31.998 lap.

**Still open for review:** no separate round-only technical-DQ rule has been
established by the evidence reviewed here. Do not infer a round's scope from
the incident time alone. A newly discovered decision cancelling only specified
rounds would need its exact official scope recorded before changing treatment.
This implementation preserves the existing verified exclusions and explicitly
flags this limitation rather than claiming an exhaustive sanctions audit.

### 3. Red flags and unusual sessions

**Confirmed from the cached Formula 1 race-control feed:** qualifying was
interrupted by genuine red flags at these 2025 events:

| Event | Recorded red-flag messages |
| --- | ---: |
| Japan | 1 |
| Bahrain | 1 |
| Saudi Arabia | 1 |
| Emilia Romagna | 2 |
| Monaco | 2 |
| Canada | 1 |
| Austria | 1 |
| Britain | 1 |
| Azerbaijan | 6 |
| United States | 1 |
| Qatar | 1 |

The separate evidence CSV preserves timestamps and wording. A chequered flag
or a message investigating a red-flag infringement is not counted as another
red flag. Cached resumption messages identify examples such as Japan Q2,
Bahrain Q2, Saudi Arabia Q3, Monaco Q2 and Azerbaijan Q1/Q2/Q3. Red flags confirm
interruptions; the count alone does not prove how much green running was lost
or that a particular round ended permanently early.

**Default implemented, awaiting review:** retain officially accepted times
and use FastF1's `split_qualifying_sessions()` to group recovery laps into
Q1/Q2/Q3, including interruptions and resumptions. Do not divide the session
into fixed wall-clock windows or restart the round numbering at every red
flag. Do not add a hypothetical extra attempt or compensate a driver's time
for lost running. A driver who advanced but set no valid time has
`no_valid_lap` in that round, while their earlier round remains usable.

Examples in the extracted data include Norris without a valid Q3 time in
Saudi Arabia; Antonelli and Russell without Q2 times in Monaco; and Leclerc
and Piastri without Q3 times in Azerbaijan. These missing times and the red-flag
records establish unusual session context, but the code does not assign a
crash or penalty cause merely from the blank itself.

**Still open for review:** red flags, rain and late attempts can make two valid
best times less comparable. This version reports them without a disruption
weight or exclusion. No new rule for shortened or interrupted sessions is
silently imposed, and red-flag counts are not confidence scores.

## Completed run

Counts refer to unique pairs, not the two driver rows:

| Round | Usable pairs | eliminated_prior_round | no_valid_lap | dsq |
| --- | ---: | ---: | ---: | ---: |
| Q1 | 233 | 0 | 5 | 2 |
| Q2 | 134 | 101 | 3 | 2 |
| Q3 | 72 | 163 | 3 | 2 |

Of 240 pairs: **72 have all three rounds, 62 have two, 99 have only one,
and 7 have none**. Each row's selected gap and round match the original export.
All other legacy columns also match exactly at the existing six-decimal CSV
precision, including sources, flags and blank explanations. The original has
466 valid driver rows / 233 pairs; that selected-gap coverage is unchanged.

All **91 tests passed: 81 existing and 10 new**. The new checks cover prior
elimination, signed denominators, main Q selection on sprint weekends, saved
parity, reached-but-untimed rounds, Miami-style recovery, disqualifications,
blocked recovery after a Q1 correction, standalone imports and genuine red-flag
classification. Existing dependency deprecation warnings are nonfatal.

## Known limitations

- **Later rounds cover a selected group of drivers.** Q3 has only 72 usable
  pair comparisons. Reaching Q3 depends on both cars and their qualifying
  performances. A season average of Q3 gaps would describe a different sample
  from a Q1 average; missing later rounds are not zero gaps.
- **The three round gaps are related observations.** They come from the same
  weekend, drivers and cars. Treating them as three independent races would
  exaggerate the amount of evidence. No rating or aggregation rule is added.
- **A shared round does not guarantee shared conditions.** Rain, traffic, tyre
  choices, track evolution and red flags can affect when each best time was
  set. This method provides no adjustment or uncertainty estimate for those
  differences.
- **Advancement and exclusions depend on available records.** Classified times
  and the copied 2025 rules govern recovery; the DQ registry is year-specific.
  Delayed corrections or previously unrecorded round-specific decisions could
  require review. The evidence file includes investigations that may not have
  resulted in penalties.
- **Recovery cannot create a missing performance.** Miami's eligible times can
  be recovered, but a driver with no valid lap in a round still has a blank.
  Entirely missing round data stops publication instead of being guessed.
- **This is one season of teammate-relative pace.** It does not measure absolute
  driver quality or show how the same drivers would compare in another car or
  year. The preserved selected-gap column and new round columns answer related
  but different questions and should not be mixed without an explicit method.

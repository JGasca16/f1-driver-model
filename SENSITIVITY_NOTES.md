# Season rating sensitivity

The baseline uses 45% qualifying, 45% dry and 10% wet at full evidence,
8/8/3 effective-race references, and a 0.5 Monaco dry observation-weight
multiplier. Q3/Q2/Q1 combination weights stay 0.50/0.30/0.20 in every run.
All three alternatives were fixed before examining ratings. Each changes only
the setting shown; there is no search for a preferred ordering.

Every variant repeats aggregation, evidence scaling, provisional/established
checks and the 2,000-draw seed-42 weekend bootstrap. All variants share the same
sampled weekends, avoiding random-draw differences between alternatives.
Full precision determines order; table values are displayed to three decimals.

| Single change | Drivers changing rank | Largest rank move | Drivers moving more than 2 | Largest absolute score change |
| --- | ---: | ---: | ---: | ---: |
| Monaco dry multiplier 1.0 | 2 | 1 | 0 | 0.017 |
| Evidence references 6 qualifying/dry, 2 wet | 4 | 1 | 0 | 0.027 |
| Full-evidence weights 50/45/5 | 2 | 1 | 0 | 0.031 |

Score changes are log-percentage points. No driver moved more than two
positions in any variant, so there is no list of drivers exceeding that rule.
The complete `data/driver_rating_sensitivity.csv` contains all rating changes,
including drivers with unchanged positions. A rank change with a displayed
0.000 score change means the full-precision score moved by less than 0.0005.

The one-place swaps are:

- No Monaco discount: Gasly improves one place; Russell falls one.
- References 6/2: Gasly and Antonelli improve one; Russell and Lawson fall one.
- Weights 50/45/5: Lawson improves one place; Colapinto falls one.

Ranks here are a descriptive grid ordering of the **20 established
teammate-outperformance scores**, with lower better and exact ties sharing
the minimum rank. They are not absolute-skill ranks. Doohan's provisional
number is included in all three variants but has no rank. The comparison groups
remain nine disconnected groups, without an opponent-strength adjustment.
Cross-group differences cannot establish who is the better driver. No formal
rating status changes in these variants.

This ordering is stable under the three specified choices: movements are small
and no more than one position. That does not validate the ordering or prove
stability under every reasonable method. Close scores still swap places, and
many season intervals overlap. Changing source gaps, teammate-strength
assumptions, qualifying-round weights or the treatment of missing races was
outside this check. Wet evidence remains a single observation for each driver
with a wet score, even when its evidence factor or base weight is increased.

The baseline and sensitivities retain both component scores and actual
normalized weights. No alternative replaces the baseline in
`data/driver_rating_2025.csv`. Method details, limitations and run commands are
in DRIVER_RATING_METHOD.md.

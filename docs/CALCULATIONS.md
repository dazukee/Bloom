# How every calculation in Bloom was checked

Each calculation was compared with its medical source. The cycle predictions were also tested on real data: 1,665 cycles from 159 women in Fehring's public dataset (Marquette University). The dataset was only used for testing and is not part of the app. Bloom gives estimates and is not a medical device.

## Verdicts

| Calculation | Verdict | What changed and why |
| --- | --- | --- |
| BMI = kg / m² | Correct, kept | |
| Adult categories (CDC, Asia-Pacific) | Correct, extended | Obesity classes 1, 2 and 3 added (CDC). |
| BMI under 20 | **Was wrong for teens** | Adult cut-offs do not fit growing bodies. Now uses the CDC growth charts: z = ((BMI/M)^L - 1) / (L x S), then a percentile for age and sex. |
| Age | Correct, kept | |
| Calories, adults (Mifflin-St Jeor x activity) | Correct, kept | |
| Calories, under 19 | **Improved** | Mifflin-St Jeor was made for adults. Now uses the Institute of Medicine equation for girls, which includes growth. |
| Water goal (33 ml/kg, 1.5-3.5 L) | Reasonable, kept | A rule of thumb; the user can change it. |
| Caffeine mark | **Improved** | 400 mg for adults (FDA), 200 mg when trying to conceive (ACOG), 100 mg under 18 (AAP). |
| Alcohol note | **Updated** | The 2025-2030 US guidelines dropped the number and say "consume less". Under 18: not advised. |
| Fruit and vegetables (5 portions) | Correct, kept | WHO. |
| Protein, iron, calcium, folate | **New** | Daily targets by age, from the US Dietary Reference Intakes. |
| Blood pressure categories | Correct, extended | "Low" added (below 90 or 60), and the average of recent readings, because diagnosis rests on an average, not one reading. |
| Blood oxygen | **Corrected** | 92% now counts as urgent, matching NHS advice (it was 91%). |
| Resting heart rate | Correct, kept | |
| Sleep | **Improved** | The recommendation now follows age: 9+ hours at 6-12, 8+ at 13-17, 7+ from 18 (CDC). |
| Workout calories (MET) | Correct, kept | MET x 3.5 x kg / 200 x minutes. |
| Weekly active minutes | **Improved** | Adults 150 (WHO), under 18 an average of 60 a day. Muscle-strengthening days added. |
| Next period | Correct, kept | Tested below. |
| Ovulation day (next period - 14) | Correct, kept | Tested below. Dataset average: 13.3 days after ovulation. |
| Next period once ovulation is known | **New** | Counts from the temperature shift or LH test: the biggest accuracy gain. |
| Date range for the next period | **New** | An honest range instead of one date. |
| Fertile window (calendar method) | **Improved** | Too narrow with little history; a margin now shrinks as cycles are logged. |
| Fertile window with very short cycles | **Bug fixed** | The end could fall before the start. |
| Confidence level | Correct, one fix | Well calibrated. One measured cycle now counts as low. |
| 3-over-6 temperature rule | Correct, extended | Added the published exception: a small third rise is confirmed by a fourth reading. |
| Fever and disturbed readings | **Improved** | Fevers were left out already. Any reading can now be left out (a cold, alcohol, a late night), since a mild illness stays under 38 °C. |
| Typical cycle length | **Improved** | 24-38 days for adults (FIGO), 21-45 under 20 (ACOG). |
| New warnings | **New** | Cycles that vary too much, periods over 8 days, no period for 90 days, and a 5% weight change within a month. |
| Hormone chart | **Bug fixed** | Its ovulation day was one day off the prediction. |
| Late period | **Bug fixed** | Past days stayed coloured as "predicted", and later cycles stayed on the old schedule. |
| Very old logs | **Bug fixed** | "Period 400 days late" is now a prompt to log the latest period. |
| Cycle statistics | **Bug fixed** | Forgotten-log gaps over 60 days counted in the shortest and longest. |

## Test results on real cycles

Each method predicted each woman's next cycle using only her earlier cycles.

**Next period (with at least 2 past cycles, 1,334 predictions)**

| Method | Average error | Within 2 days | Within 3 days |
| --- | --- | --- | --- |
| Always 28 days | 2.81 days | 60% | 73% |
| Same as the last cycle | 2.80 days | 61% | 73% |
| Average of the last 3 | 2.24 days | 69% | 80% |
| **Average of the last 6 (Bloom)** | **2.13 days** | **70%** | **81%** |
| Average of the last 12 | 2.14 days | 70% | 82% |
| Median of the last 6 | 2.17 days | 70% | 81% |
| Last 6 without the highest and lowest | 2.11 days | 72% | 81% |

The best method beat Bloom's by only 0.02 days, so the simpler average stayed.

**When this cycle's ovulation is known (1,238 predictions, calendar error on the same cycles: 2.04 days)**

| Method | Average error | Within 2 days |
| --- | --- | --- |
| Ovulation + 14 days | 1.70 days | 81% |
| **Ovulation + the woman's own usual gap** | **1.25 days** | **88%** |
| The same, with ovulation only known to +/-1 day, as with temperature | 1.54 days | |

Counting from a known ovulation cuts the error by up to 39%.

**Fertile window: how often the real ovulation day fell inside it**

| Cycles known | Calendar method alone | With Bloom's margin |
| --- | --- | --- |
| 1 | 68% | 90% (2 days each side) |
| 2 | 88% | 94% (1 day each side) |
| 3 | 88% | 93% (1 day each side) |
| 4 | 95% | 95% (no margin) |
| 6 or more | 97% | 97% (no margin) |

**Confidence labels and the date range**

| Label | Average error | Within 3 days |
| --- | --- | --- |
| High | 1.57 days | 90% |
| Medium | 2.21 days | 80% |
| Low | 3.41 days | 61% |

The range shown (the larger of 2 days or one standard deviation, either side) contained the real start 80% of the time.

Limits: this dataset comes from women using natural family planning, so results may differ for other groups, and its ovulation days are themselves estimates.

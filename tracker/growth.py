"""BMI for girls under 20: percentiles for age, from the CDC growth charts.

Pure logic: no customtkinter, no file access.

Adult BMI categories do not fit growing bodies, so the CDC compares a child's BMI
with other girls of the same age. Its 2000 growth charts give three numbers for
each month of age (the LMS method):
    z = ((BMI / M) ** L - 1) / (L * S)
and the percentile is the share of a normal distribution below z. Categories:
below the 5th underweight, 5th to below 85th healthy weight, 85th to below 95th
overweight, 95th and above obesity. Adults (20 and older) use bmi.py's table.
"""

import math
from dataclasses import dataclass
from datetime import date

from tracker import bmi

FIRST_MONTH = 120  # 10 years, the youngest age the app accepts
LAST_MONTH = 239  # 19 years 11 months
Z_5TH = -1.645
Z_85TH = 1.036
Z_95TH = 1.645
# (upper percentile, category, colour name)
PERCENTILE_TABLE = (
    (5, bmi.UNDERWEIGHT, "fertile"),
    (85, bmi.HEALTHY_WEIGHT, "success"),
    (95, bmi.OVERWEIGHT, "warning"),
    (float("inf"), bmi.OBESITY, "danger"),
)


@dataclass(frozen=True)
class BmiAssessment:
    """What a BMI means for this person.

    Attributes:
        value: The BMI.
        category: The category name.
        color: The theme colour name for the category.
        healthy_low_kg: The lowest healthy weight at this height.
        healthy_high_kg: The highest healthy weight at this height.
        percentile: The percentile for age, or None for an adult.
        bands: (upper BMI, colour name) rows for a gauge, lowest first.
        names: (category, BMI label) rows for a legend, lowest first.
    """

    value: float
    category: str
    color: str
    healthy_low_kg: float
    healthy_high_kg: float
    percentile: float | None
    bands: tuple
    names: tuple


def age_in_months(birth_date: date, today: date) -> int:
    """Return completed months of age."""
    months = (today.year - birth_date.year) * 12 + today.month - birth_date.month
    return months - 1 if today.day < birth_date.day else months


def applies(age_months: int | None) -> bool:
    """Return True when the age is covered by the girls' table (10 to under 20)."""
    return age_months is not None and FIRST_MONTH <= age_months <= LAST_MONTH


def _lms(age_months: int) -> tuple[float, float, float]:
    """Return (L, M, S) for an age, kept inside the table."""
    month = min(max(age_months, FIRST_MONTH), LAST_MONTH)
    return GIRLS_BMI_LMS[month - FIRST_MONTH]


def z_score(value: float, age_months: int) -> float:
    """Return the z-score of a BMI at this age."""
    power, median, spread = _lms(age_months)
    return ((value / median) ** power - 1) / (power * spread)


def percentile(value: float, age_months: int) -> float:
    """Return the percentile (0-100) of a BMI at this age, to 1 decimal place."""
    z = z_score(value, age_months)
    return round(50 * (1 + math.erf(z / math.sqrt(2))), 1)


def bmi_at_z(z: float, age_months: int) -> float:
    """Return the BMI that has this z-score at this age."""
    power, median, spread = _lms(age_months)
    return median * (1 + power * spread * z) ** (1 / power)


def _adult(value: float, height_cm: float, standard: str) -> BmiAssessment:
    low, high = bmi.healthy_weight_range(height_cm, standard)
    table = bmi.CATEGORY_TABLES[standard]
    return BmiAssessment(
        value=value,
        category=bmi.classify_bmi(value, standard),
        color=bmi.category_color(value, standard),
        healthy_low_kg=low,
        healthy_high_kg=high,
        percentile=None,
        bands=tuple((upper, color) for upper, _, color in table),
        names=tuple(
            (name, "" if upper == float("inf") else f"<{upper:g}")
            for upper, name, _ in table
        ),
    )


def _girl(value: float, height_cm: float, age_months: int) -> BmiAssessment:
    share = percentile(value, age_months)
    category, color = bmi.OBESITY, "danger"
    for upper, name, token in PERCENTILE_TABLE:
        if share < upper:
            category, color = name, token
            break
    height_m = height_cm / 100
    fifth = bmi_at_z(Z_5TH, age_months)
    eighty_fifth = bmi_at_z(Z_85TH, age_months)
    ninety_fifth = bmi_at_z(Z_95TH, age_months)
    return BmiAssessment(
        value=value,
        category=category,
        color=color,
        healthy_low_kg=round(fifth * height_m**2, 1),
        healthy_high_kg=round(eighty_fifth * height_m**2, 1),
        percentile=share,
        bands=(
            (fifth, "fertile"),
            (eighty_fifth, "success"),
            (ninety_fifth, "warning"),
            (float("inf"), "danger"),
        ),
        names=(
            (bmi.UNDERWEIGHT, f"<{fifth:.1f}"),
            (bmi.HEALTHY_WEIGHT, f"<{eighty_fifth:.1f}"),
            (bmi.OVERWEIGHT, f"<{ninety_fifth:.1f}"),
            (bmi.OBESITY, ""),
        ),
    )


def assess(
    value: float,
    height_cm: float,
    age_months: int | None,
    standard: str = bmi.CDC,
) -> BmiAssessment:
    """Return what a BMI means: by percentile under 20, by the chosen table otherwise.

    The Asia-Pacific cut-offs are for adults, so they apply from age 20 too.
    """
    if applies(age_months):
        return _girl(value, height_cm, age_months)
    return _adult(value, height_cm, standard)


# CDC 2000 BMI-for-age, girls: (L, M, S) for completed months 120 to 239.
GIRLS_BMI_LMS = (
    (-2.1713, 16.862, 0.13706),  # 10 y 0 mo
    (-2.1585, 16.911, 0.13771),  # 10 y 1 mo
    (-2.1461, 16.961, 0.13835),  # 10 y 2 mo
    (-2.1341, 17.010, 0.13898),  # 10 y 3 mo
    (-2.1225, 17.060, 0.13959),  # 10 y 4 mo
    (-2.1114, 17.110, 0.14018),  # 10 y 5 mo
    (-2.1007, 17.161, 0.14075),  # 10 y 6 mo
    (-2.0905, 17.212, 0.14131),  # 10 y 7 mo
    (-2.0806, 17.263, 0.14186),  # 10 y 8 mo
    (-2.0712, 17.314, 0.14238),  # 10 y 9 mo
    (-2.0621, 17.366, 0.14290),  # 10 y 10 mo
    (-2.0535, 17.417, 0.14339),  # 10 y 11 mo
    (-2.0452, 17.469, 0.14387),  # 11 y 0 mo
    (-2.0374, 17.521, 0.14433),  # 11 y 1 mo
    (-2.0299, 17.573, 0.14478),  # 11 y 2 mo
    (-2.0228, 17.626, 0.14521),  # 11 y 3 mo
    (-2.0161, 17.678, 0.14562),  # 11 y 4 mo
    (-2.0098, 17.731, 0.14602),  # 11 y 5 mo
    (-2.0038, 17.784, 0.14640),  # 11 y 6 mo
    (-1.9982, 17.836, 0.14677),  # 11 y 7 mo
    (-1.9930, 17.889, 0.14712),  # 11 y 8 mo
    (-1.9881, 17.942, 0.14745),  # 11 y 9 mo
    (-1.9835, 17.995, 0.14777),  # 11 y 10 mo
    (-1.9794, 18.048, 0.14807),  # 11 y 11 mo
    (-1.9755, 18.101, 0.14836),  # 12 y 0 mo
    (-1.9720, 18.155, 0.14864),  # 12 y 1 mo
    (-1.9689, 18.208, 0.14889),  # 12 y 2 mo
    (-1.9660, 18.261, 0.14914),  # 12 y 3 mo
    (-1.9635, 18.314, 0.14937),  # 12 y 4 mo
    (-1.9614, 18.367, 0.14958),  # 12 y 5 mo
    (-1.9595, 18.420, 0.14978),  # 12 y 6 mo
    (-1.9580, 18.473, 0.14997),  # 12 y 7 mo
    (-1.9568, 18.526, 0.15014),  # 12 y 8 mo
    (-1.9559, 18.579, 0.15030),  # 12 y 9 mo
    (-1.9553, 18.631, 0.15045),  # 12 y 10 mo
    (-1.9550, 18.684, 0.15058),  # 12 y 11 mo
    (-1.9550, 18.736, 0.15071),  # 13 y 0 mo
    (-1.9553, 18.789, 0.15081),  # 13 y 1 mo
    (-1.9559, 18.841, 0.15091),  # 13 y 2 mo
    (-1.9568, 18.893, 0.15099),  # 13 y 3 mo
    (-1.9579, 18.945, 0.15107),  # 13 y 4 mo
    (-1.9594, 18.997, 0.15113),  # 13 y 5 mo
    (-1.9611, 19.048, 0.15118),  # 13 y 6 mo
    (-1.9631, 19.099, 0.15122),  # 13 y 7 mo
    (-1.9654, 19.151, 0.15124),  # 13 y 8 mo
    (-1.9679, 19.201, 0.15126),  # 13 y 9 mo
    (-1.9707, 19.252, 0.15127),  # 13 y 10 mo
    (-1.9738, 19.302, 0.15127),  # 13 y 11 mo
    (-1.9771, 19.353, 0.15126),  # 14 y 0 mo
    (-1.9806, 19.402, 0.15124),  # 14 y 1 mo
    (-1.9844, 19.452, 0.15121),  # 14 y 2 mo
    (-1.9885, 19.501, 0.15117),  # 14 y 3 mo
    (-1.9928, 19.550, 0.15112),  # 14 y 4 mo
    (-1.9973, 19.599, 0.15107),  # 14 y 5 mo
    (-2.0020, 19.647, 0.15101),  # 14 y 6 mo
    (-2.0070, 19.696, 0.15094),  # 14 y 7 mo
    (-2.0121, 19.743, 0.15087),  # 14 y 8 mo
    (-2.0175, 19.791, 0.15079),  # 14 y 9 mo
    (-2.0231, 19.838, 0.15070),  # 14 y 10 mo
    (-2.0289, 19.884, 0.15061),  # 14 y 11 mo
    (-2.0349, 19.931, 0.15051),  # 15 y 0 mo
    (-2.0411, 19.976, 0.15041),  # 15 y 1 mo
    (-2.0474, 20.022, 0.15030),  # 15 y 2 mo
    (-2.0539, 20.067, 0.15019),  # 15 y 3 mo
    (-2.0606, 20.112, 0.15008),  # 15 y 4 mo
    (-2.0675, 20.156, 0.14996),  # 15 y 5 mo
    (-2.0745, 20.200, 0.14984),  # 15 y 6 mo
    (-2.0816, 20.243, 0.14972),  # 15 y 7 mo
    (-2.0889, 20.286, 0.14960),  # 15 y 8 mo
    (-2.0963, 20.329, 0.14947),  # 15 y 9 mo
    (-2.1038, 20.371, 0.14934),  # 15 y 10 mo
    (-2.1114, 20.412, 0.14922),  # 15 y 11 mo
    (-2.1192, 20.453, 0.14909),  # 16 y 0 mo
    (-2.1270, 20.494, 0.14896),  # 16 y 1 mo
    (-2.1349, 20.534, 0.14884),  # 16 y 2 mo
    (-2.1428, 20.573, 0.14871),  # 16 y 3 mo
    (-2.1509, 20.613, 0.14859),  # 16 y 4 mo
    (-2.1589, 20.651, 0.14847),  # 16 y 5 mo
    (-2.1670, 20.689, 0.14835),  # 16 y 6 mo
    (-2.1752, 20.727, 0.14823),  # 16 y 7 mo
    (-2.1833, 20.764, 0.14812),  # 16 y 8 mo
    (-2.1915, 20.800, 0.14802),  # 16 y 9 mo
    (-2.1996, 20.836, 0.14791),  # 16 y 10 mo
    (-2.2077, 20.871, 0.14782),  # 16 y 11 mo
    (-2.2157, 20.906, 0.14772),  # 17 y 0 mo
    (-2.2237, 20.940, 0.14764),  # 17 y 1 mo
    (-2.2317, 20.973, 0.14756),  # 17 y 2 mo
    (-2.2395, 21.006, 0.14749),  # 17 y 3 mo
    (-2.2473, 21.039, 0.14742),  # 17 y 4 mo
    (-2.2549, 21.070, 0.14737),  # 17 y 5 mo
    (-2.2624, 21.102, 0.14732),  # 17 y 6 mo
    (-2.2697, 21.132, 0.14729),  # 17 y 7 mo
    (-2.2769, 21.162, 0.14726),  # 17 y 8 mo
    (-2.2839, 21.191, 0.14724),  # 17 y 9 mo
    (-2.2907, 21.220, 0.14724),  # 17 y 10 mo
    (-2.2973, 21.248, 0.14725),  # 17 y 11 mo
    (-2.3037, 21.275, 0.14727),  # 18 y 0 mo
    (-2.3098, 21.302, 0.14730),  # 18 y 1 mo
    (-2.3157, 21.328, 0.14735),  # 18 y 2 mo
    (-2.3212, 21.353, 0.14741),  # 18 y 3 mo
    (-2.3265, 21.378, 0.14749),  # 18 y 4 mo
    (-2.3314, 21.402, 0.14758),  # 18 y 5 mo
    (-2.3360, 21.425, 0.14769),  # 18 y 6 mo
    (-2.3403, 21.448, 0.14782),  # 18 y 7 mo
    (-2.3442, 21.470, 0.14796),  # 18 y 8 mo
    (-2.3477, 21.491, 0.14812),  # 18 y 9 mo
    (-2.3508, 21.512, 0.14830),  # 18 y 10 mo
    (-2.3534, 21.532, 0.14850),  # 18 y 11 mo
    (-2.3557, 21.551, 0.14872),  # 19 y 0 mo
    (-2.3575, 21.569, 0.14897),  # 19 y 1 mo
    (-2.3588, 21.587, 0.14923),  # 19 y 2 mo
    (-2.3596, 21.604, 0.14952),  # 19 y 3 mo
    (-2.3599, 21.620, 0.14983),  # 19 y 4 mo
    (-2.3597, 21.635, 0.15016),  # 19 y 5 mo
    (-2.3590, 21.650, 0.15052),  # 19 y 6 mo
    (-2.3577, 21.664, 0.15091),  # 19 y 7 mo
    (-2.3559, 21.677, 0.15132),  # 19 y 8 mo
    (-2.3535, 21.689, 0.15175),  # 19 y 9 mo
    (-2.3505, 21.701, 0.15222),  # 19 y 10 mo
    (-2.3470, 21.712, 0.15272),  # 19 y 11 mo
)

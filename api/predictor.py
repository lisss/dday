"""Estimate probable death date from personal and country-level factors."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, Field

from . import storage

Gender = Literal["male", "female", "other"]
Education = Literal["none", "primary", "secondary", "tertiary"]
IncomeLevel = Literal["low", "average", "high"]
SmokingStatus = Literal["never", "former", "current"]
AlcoholLevel = Literal["none", "light", "moderate", "heavy"]
ActivityType = Literal[
    "running",
    "gym",
    "tennis",
    "cycling",
    "swimming",
    "walking",
    "yoga",
    "team_sports",
]

ACTIVITY_LABELS: dict[str, str] = {
    "running": "Running",
    "gym": "Gym / weights",
    "tennis": "Tennis",
    "cycling": "Cycling",
    "swimming": "Swimming",
    "walking": "Walking",
    "yoga": "Yoga / pilates",
    "team_sports": "Team sports",
}


class ActivityEntry(BaseModel):
    type: ActivityType
    hours_per_week: float = Field(ge=0, le=40, default=0)


class PredictRequest(BaseModel):
    birth_date: date
    gender: Gender = "other"
    country_code: str = Field(min_length=2, max_length=2)
    education: Education = "secondary"
    income_level: IncomeLevel = "average"
    smoking: SmokingStatus = "never"
    alcohol: AlcoholLevel = "none"
    reading_hours_per_month: float = Field(ge=0, le=250, default=0)
    activities: list[ActivityEntry] = Field(default_factory=list)
    ethnicity_group: str | None = None


class PredictResponse(BaseModel):
    predicted_death_date: date
    earliest_death_date: date
    latest_death_date: date
    remaining_years: float
    life_expectancy_at_birth: float
    adjusted_life_expectancy: float
    country: str
    factors_applied: dict[str, float]
    disclaimer: str


GLOBAL_LIFE_EXPECTANCY = 73.0

GENDER_ADJUSTMENT = {
    "male": -2.5,
    "female": 2.0,
    "other": 0.0,
}

EDUCATION_ADJUSTMENT = {
    "none": -4.0,
    "primary": -2.0,
    "secondary": 0.0,
    "tertiary": 3.5,
}

INCOME_ADJUSTMENT = {
    "low": -5.0,
    "average": 0.0,
    "high": 4.0,
}

SMOKING_ADJUSTMENT = {
    "never": 0.0,
    "former": -1.5,
    "current": -8.0,
}

ALCOHOL_ADJUSTMENT = {
    "none": 0.0,
    "light": 0.4,
    "moderate": -1.8,
    "heavy": -6.5,
}

ACTIVITY_BENEFIT_PER_HOUR: dict[str, float] = {
    "running": 0.18,
    "gym": 0.14,
    "tennis": 0.16,
    "cycling": 0.15,
    "swimming": 0.17,
    "walking": 0.08,
    "yoga": 0.10,
    "team_sports": 0.14,
}

SEDENTARY_PENALTY = -3.0
MAX_READING_BENEFIT = 3.5
MAX_ACTIVITY_BENEFIT = 5.5


def _base_life_expectancy(country_code: str) -> tuple[float, str]:
    info = storage.get_country(country_code)
    if info and info.get("life_expectancy") is not None:
        return round(float(info["life_expectancy"])), info.get("name", country_code)
    return GLOBAL_LIFE_EXPECTANCY, country_code


def _activity_hours_adjustment(hours: float, benefit_per_hour: float) -> float:
    if hours <= 0:
        return 0.0
    capped = min(hours, 12.0)
    diminishing = 1.0 - min(hours, 25.0) / 50.0
    return benefit_per_hour * capped * max(diminishing, 0.35)


def _reading_adjustment(hours_per_month: float) -> float:
    if hours_per_month <= 0:
        return 0.0
    hours_per_week = hours_per_month / 4.345
    return min(MAX_READING_BENEFIT, hours_per_week * 0.22)


def _activity_factors(activities: list[ActivityEntry]) -> dict[str, float]:
    active = [entry for entry in activities if entry.hours_per_week > 0]
    if not active:
        return {"activity_sedentary": SEDENTARY_PENALTY}

    factors: dict[str, float] = {}
    for entry in active:
        rate = ACTIVITY_BENEFIT_PER_HOUR[entry.type]
        benefit = _activity_hours_adjustment(entry.hours_per_week, rate)
        label = ACTIVITY_LABELS.get(entry.type, entry.type)
        factors[f"activity_{label}"] = round(benefit, 2)

    total_benefit = sum(factors.values())
    if total_benefit > MAX_ACTIVITY_BENEFIT:
        scale = MAX_ACTIVITY_BENEFIT / total_benefit
        factors = {key: round(value * scale, 2) for key, value in factors.items()}

    return factors


def predict_death(req: PredictRequest) -> PredictResponse:
    base_exp, country_name = _base_life_expectancy(req.country_code.upper())
    today = date.today()
    current_age = relativedelta(today, req.birth_date).years

    factors: dict[str, float] = {
        "gender": GENDER_ADJUSTMENT[req.gender],
        "education": EDUCATION_ADJUSTMENT[req.education],
        "income": INCOME_ADJUSTMENT[req.income_level],
        "smoking": SMOKING_ADJUSTMENT[req.smoking],
        "alcohol": ALCOHOL_ADJUSTMENT[req.alcohol],
        "reading": round(_reading_adjustment(req.reading_hours_per_month), 2),
    }
    factors.update(_activity_factors(req.activities))

    total_adjustment = sum(factors.values())
    adjusted_expectancy = max(45.0, min(95.0, base_exp + total_adjustment))

    remaining = max(0.5, adjusted_expectancy - current_age)
    predicted = req.birth_date + relativedelta(years=int(round(adjusted_expectancy)))

    spread_years = 8.0
    earliest = predicted - timedelta(days=int(spread_years * 365.25 / 2))
    latest = predicted + timedelta(days=int(spread_years * 365.25 / 2))

    return PredictResponse(
        predicted_death_date=predicted,
        earliest_death_date=earliest,
        latest_death_date=latest,
        remaining_years=round(remaining, 1),
        life_expectancy_at_birth=round(base_exp),
        adjusted_life_expectancy=round(adjusted_expectancy),
        country=country_name,
        factors_applied={k: round(v, 1) for k, v in factors.items()},
        disclaimer=(
            "This is a statistical estimate based on population averages, not medical advice. "
            "Individual outcomes vary widely."
        ),
    )

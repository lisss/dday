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
ActivityLevel = Literal["sedentary", "moderate", "active"]
SmokingStatus = Literal["never", "former", "current"]


class PredictRequest(BaseModel):
    birth_date: date
    gender: Gender = "other"
    country_code: str = Field(min_length=2, max_length=2)
    education: Education = "secondary"
    income_level: IncomeLevel = "average"
    activity_level: ActivityLevel = "moderate"
    smoking: SmokingStatus = "never"
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

ACTIVITY_ADJUSTMENT = {
    "sedentary": -3.0,
    "moderate": 0.0,
    "active": 2.5,
}

SMOKING_ADJUSTMENT = {
    "never": 0.0,
    "former": -1.5,
    "current": -8.0,
}


def _base_life_expectancy(country_code: str) -> tuple[float, str]:
    info = storage.get_country(country_code)
    if info and info.get("life_expectancy"):
        return float(info["life_expectancy"]), info.get("name", country_code)
    return GLOBAL_LIFE_EXPECTANCY, country_code


def predict_death(req: PredictRequest) -> PredictResponse:
    base_exp, country_name = _base_life_expectancy(req.country_code.upper())
    today = date.today()
    current_age = relativedelta(today, req.birth_date).years

    factors = {
        "gender": GENDER_ADJUSTMENT[req.gender],
        "education": EDUCATION_ADJUSTMENT[req.education],
        "income": INCOME_ADJUSTMENT[req.income_level],
        "activity": ACTIVITY_ADJUSTMENT[req.activity_level],
        "smoking": SMOKING_ADJUSTMENT[req.smoking],
    }
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
        life_expectancy_at_birth=round(base_exp, 1),
        adjusted_life_expectancy=round(adjusted_expectancy, 1),
        country=country_name,
        factors_applied={k: round(v, 1) for k, v in factors.items()},
        disclaimer=(
            "This is a statistical estimate based on population averages, not medical advice. "
            "Individual outcomes vary widely."
        ),
    )

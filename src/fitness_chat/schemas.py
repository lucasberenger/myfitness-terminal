from datetime import datetime
from decimal import Decimal
from typing import Annotated
from pydantic import BaseModel, Field, AwareDatetime, ConfigDict

Amount = Annotated[Decimal, Field(ge=0, le=100000, decimal_places=4)]
Grams = Annotated[Decimal, Field(gt=0, le=100000, decimal_places=4)]
Text = Annotated[str, Field(min_length=1, max_length=200)]


class FoodInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: Text
    source: Annotated[str, Field(min_length=1, max_length=500)]
    calories: Amount
    protein: Amount
    carbs: Amount
    fat: Amount


class FoodOutput(FoodInput):
    model_config = ConfigDict(from_attributes=True)
    id: int


class MealInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    food_id: int = Field(gt=0)
    label: str = Field(min_length=1, max_length=100)
    grams: Grams
    consumed_at: AwareDatetime


class MealUpdate(BaseModel):
    grams: Grams


class Nutrients(BaseModel):
    calories: Decimal
    protein: Decimal
    carbs: Decimal
    fat: Decimal


class MealOutput(BaseModel):
    id: int
    food_id: int
    food_name: str
    source: str
    label: str
    grams: Decimal
    consumed_at: datetime
    recorded_at: datetime
    nutrients: Nutrients

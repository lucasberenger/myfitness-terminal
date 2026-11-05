from datetime import date
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from fitness_chat.persistence import Food, MealItem
from fitness_chat.schemas import FoodOutput, MealInput, Grams
from fitness_chat.services import daily_summary, meal_output, register_meal, require


class Arguments(BaseModel):
    model_config = ConfigDict(extra='forbid')


class SearchFoods(Arguments):
    query: str = Field(min_length=1, max_length=200)


class CreateMeal(MealInput):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class UpdateMeal(Arguments):
    item_id: int = Field(gt=0)
    grams: Grams


class DailySummary(Arguments):
    day: date


TOOLS = {
    'search_foods': (SearchFoods, 'Busca no catálogo por nome; retorna nutrientes por 100 g e IDs.'),
    'create_meal': (CreateMeal, 'Registra um alimento do catálogo com quantidade em gramas e horário com fuso.'),
    'update_meal_item': (UpdateMeal, 'Corrige a quantidade de um item existente pelo ID.'),
    'get_daily_summary': (DailySummary, 'Consulta itens, IDs e totais de um dia no fuso do usuário.'),
}


def definitions():
    return [{'type': 'function', 'function': {'name': name, 'description': description,
            'parameters': schema.model_json_schema()}}
            for name, (schema, description) in TOOLS.items()]


def execute(session: Session, name: str, arguments: str, timezone_name: str):
    if name not in TOOLS:
        return {'error': 'Ferramenta desconhecida'}
    data = TOOLS[name][0].model_validate_json(arguments)
    if name == 'search_foods':
        foods = session.scalars(select(Food).where(
            Food.name.icontains(data.query, autoescape=True)).order_by(Food.id).limit(20)).all()
        return [FoodOutput.model_validate(f) for f in foods]
    if name == 'create_meal':
        return meal_output(register_meal(session, data, commit=False))
    if name == 'update_meal_item':
        item = require(session, MealItem, data.item_id)
        item.grams = data.grams
        session.flush()
        return meal_output(item)
    return daily_summary(session, data.day, timezone_name)

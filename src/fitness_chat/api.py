"""API local para o diário alimentar."""
from datetime import date
from typing import Annotated
from fastapi import Depends, FastAPI, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from fitness_chat.config import Settings, get_settings
from fitness_chat.persistence import Food, MealItem, get_session
from fitness_chat.schemas import FoodInput, FoodOutput, MealInput, MealOutput, MealUpdate
from fitness_chat.services import NotFound, daily_summary, meal_output, register_meal, require

app = FastAPI(title='Fitness Chat', version='0.1.0')
Database = Annotated[Session, Depends(get_session)]


@app.exception_handler(NotFound)
async def not_found(request, exc):
    return JSONResponse(status_code=404, content={'detail': str(exc)})


@app.get('/health')
def health() -> dict[str, str]:
    """Verifica apenas o processo HTTP."""
    return {'status': 'ok'}


@app.post('/foods', response_model=FoodOutput, status_code=201)
def create_food(data: FoodInput, session: Database):
    food = Food(**data.model_dump())
    session.add(food)
    session.commit()
    session.refresh(food)
    return food


@app.get('/foods', response_model=list[FoodOutput])
def list_foods(session: Database, q: str = '', limit: Annotated[int, Query(ge=1, le=100)] = 50):
    return session.scalars(select(Food).where(Food.name.icontains(q, autoescape=True))
                           .order_by(Food.name, Food.id).limit(limit)).all()


@app.post('/meal-items', response_model=MealOutput, status_code=201)
def create_meal(data: MealInput, session: Database):
    return meal_output(register_meal(session, data))


@app.patch('/meal-items/{item_id}', response_model=MealOutput)
def update_meal(item_id: int, data: MealUpdate, session: Database):
    item = require(session, MealItem, item_id)
    item.grams = data.grams
    session.commit()
    session.refresh(item)
    return meal_output(item)


@app.delete('/meal-items/{item_id}', status_code=204)
def delete_meal(item_id: int, session: Database):
    session.delete(require(session, MealItem, item_id))
    session.commit()
    return Response(status_code=204)


@app.get('/summaries/daily')
def summary(day: date, session: Database, settings: Annotated[Settings, Depends(get_settings)]):
    return daily_summary(session, day, settings.timezone)

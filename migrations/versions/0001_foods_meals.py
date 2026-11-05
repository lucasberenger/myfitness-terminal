"""Catálogo e itens de refeições com snapshots nutricionais."""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def nutrient_columns():
    return [sa.Column(n, sa.Numeric(12, 4), nullable=False)
            for n in ('calories', 'protein', 'carbs', 'fat')]


def upgrade():
    op.create_table('foods', sa.Column('id', sa.Integer, primary_key=True),
                    sa.Column('name', sa.String(200), nullable=False),
                    sa.Column('source', sa.String(500), nullable=False), *nutrient_columns())
    op.create_table('meal_items', sa.Column('id', sa.Integer, primary_key=True),
                    sa.Column('food_id', sa.Integer, sa.ForeignKey('foods.id'), nullable=False),
                    sa.Column('label', sa.String(100), nullable=False),
                    sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=False),
                    sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
                    sa.Column('grams', sa.Numeric(12, 4), nullable=False),
                    sa.Column('food_name', sa.String(200), nullable=False),
                    sa.Column('source', sa.String(500), nullable=False), *nutrient_columns())
    op.create_index('ix_meal_items_consumed_at', 'meal_items', ['consumed_at'])


def downgrade():
    op.drop_table('meal_items')
    op.drop_table('foods')

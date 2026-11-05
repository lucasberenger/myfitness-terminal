"""Histórico das conversas do agente."""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('conversations', sa.Column('id', sa.String(36), primary_key=True),
                    sa.Column('messages', sa.JSON, nullable=False))


def downgrade():
    op.drop_table('conversations')

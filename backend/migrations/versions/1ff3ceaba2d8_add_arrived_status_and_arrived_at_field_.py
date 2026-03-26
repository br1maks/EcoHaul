from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "1ff3ceaba2d8"
down_revision: Union[str, Sequence[str], None] = "ed7704eeea20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column(
        'orders',
        sa.Column('arrived_at', sa.DateTime(timezone=True), nullable=True)
    )

def downgrade() -> None:
    op.drop_column('orders', 'arrived_at')

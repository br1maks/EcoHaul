from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "818beefeb281"
down_revision: Union[str, Sequence[str], None] = "5821ce36db9f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.drop_column("courier_shifts", "orders_declined")

def downgrade() -> None:
    op.add_column(
        "courier_shifts",
        sa.Column("orders_declined", sa.INTEGER(), autoincrement=False, nullable=False),
    )

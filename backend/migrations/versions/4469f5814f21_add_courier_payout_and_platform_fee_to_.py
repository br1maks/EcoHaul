from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "4469f5814f21"
down_revision: Union[str, Sequence[str], None] = "818beefeb281"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("courier_payout", sa.Numeric(precision=10, scale=2), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("platform_fee", sa.Numeric(precision=10, scale=2), nullable=True),
    )

def downgrade() -> None:
    op.drop_column("orders", "platform_fee")
    op.drop_column("orders", "courier_payout")

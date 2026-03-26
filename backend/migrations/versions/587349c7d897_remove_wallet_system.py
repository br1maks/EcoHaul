from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "587349c7d897"
down_revision: Union[str, Sequence[str], None] = "8809ce1b2144"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.drop_table("wallet_transactions")

    op.drop_column("users", "wallet_balance")
    op.drop_column("users", "total_earnings")

    op.drop_column("orders", "courier_payout")
    op.drop_column("orders", "platform_fee")

    op.drop_column("courier_shifts", "total_earned")
    op.drop_column("courier_shifts", "platform_fee_total")

def downgrade() -> None:

    op.add_column("courier_shifts", sa.Column("total_earned", sa.Numeric(10, 2), nullable=False, server_default="0.0"))
    op.add_column("courier_shifts", sa.Column("platform_fee_total", sa.Numeric(10, 2), nullable=False, server_default="0.0"))

    op.add_column("orders", sa.Column("courier_payout", sa.Numeric(10, 2), nullable=True))
    op.add_column("orders", sa.Column("platform_fee", sa.Numeric(10, 2), nullable=True))

    op.add_column("users", sa.Column("wallet_balance", sa.Numeric(10, 2), nullable=False, server_default="0.0"))
    op.add_column("users", sa.Column("total_earnings", sa.Numeric(12, 2), nullable=False, server_default="0.0"))

    op.create_table(
        "wallet_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("transaction_type", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_wallet_transaction_user_id", "wallet_transactions", ["user_id"])
    op.create_index("idx_wallet_transaction_order_id", "wallet_transactions", ["order_id"])
    op.create_index("idx_wallet_transaction_type", "wallet_transactions", ["transaction_type"])

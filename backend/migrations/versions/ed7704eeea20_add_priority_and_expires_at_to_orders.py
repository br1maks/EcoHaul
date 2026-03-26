from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "ed7704eeea20"
down_revision: Union[str, Sequence[str], None] = "85218e052650"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("orders", sa.Column("priority", sa.Integer(), nullable=False, server_default="0"))
    op.add_column(
        "orders", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index("idx_order_expires_at", "orders", ["expires_at"], unique=False)
    op.create_index("idx_order_priority", "orders", ["priority"], unique=False)
    op.create_index(
        "idx_order_status_priority", "orders", ["status", "priority"], unique=False
    )

def downgrade() -> None:
    op.drop_index("idx_order_status_priority", table_name="orders")
    op.drop_index("idx_order_priority", table_name="orders")
    op.drop_index("idx_order_expires_at", table_name="orders")
    op.drop_column("orders", "expires_at")
    op.drop_column("orders", "priority")

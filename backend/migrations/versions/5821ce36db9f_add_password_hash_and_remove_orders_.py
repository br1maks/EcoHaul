from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "5821ce36db9f"
down_revision: Union[str, Sequence[str], None] = "587349c7d897"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column(
        "users", sa.Column("password_hash", sa.String(length=255), nullable=True)
    )
    op.alter_column(
        "users",
        "is_telegram_verified",
        existing_type=sa.BOOLEAN(),
        server_default=None,
        existing_nullable=False,
    )

def downgrade() -> None:
    op.alter_column(
        "users",
        "is_telegram_verified",
        existing_type=sa.BOOLEAN(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )
    op.drop_column("users", "password_hash")

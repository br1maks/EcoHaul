from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "8809ce1b2144"
down_revision: Union[str, Sequence[str], None] = "ac023023a5c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.alter_column("users", "is_email_verified", new_column_name="is_telegram_verified")

def downgrade() -> None:
    op.alter_column("users", "is_telegram_verified", new_column_name="is_email_verified")

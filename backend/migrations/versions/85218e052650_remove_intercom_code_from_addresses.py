from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "85218e052650"
down_revision: Union[str, Sequence[str], None] = "905784d338da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.drop_column("addresses", "intercom_code")

def downgrade() -> None:
    op.add_column(
        "addresses",
        sa.Column("intercom_code", sa.String(length=500), nullable=True),
    )

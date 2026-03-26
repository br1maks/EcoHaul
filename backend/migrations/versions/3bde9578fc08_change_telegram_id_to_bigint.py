from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '3bde9578fc08'
down_revision: Union[str, Sequence[str], None] = '071187158d69'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.alter_column(
        'users',
        'telegram_id',
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )

def downgrade() -> None:
    op.alter_column(
        'users',
        'telegram_id',
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )

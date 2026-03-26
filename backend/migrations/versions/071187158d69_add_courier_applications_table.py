from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '071187158d69'
down_revision: Union[str, Sequence[str], None] = '1ff3ceaba2d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('courier_applications',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('has_transport', sa.Boolean(), nullable=False),
    sa.Column('transport_type', sa.String(length=100), nullable=True),
    sa.Column('work_area', sa.String(length=255), nullable=True),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='courierapplicationstatus'), nullable=False),
    sa.Column('admin_comment', sa.Text(), nullable=True),
    sa.Column('reviewed_by_id', sa.UUID(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('courier_applications')

"""Add project key management tables

Revision ID: c01b4835a16d
Revises: 005
Create Date: 2025-08-01 10:20:07.007565

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c01b4835a16d'
down_revision: Union[str, Sequence[str], None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create project_keys table
    op.create_table(
        'project_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_name', sa.String(length=100), nullable=False),
        sa.Column('project_key', sa.String(length=255), nullable=False),
        sa.Column('request_date', sa.String(length=8), nullable=False),
        sa.Column('request_ip', sa.String(length=45), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for project_keys table
    op.create_index(op.f('ix_project_keys_project_name'), 'project_keys', ['project_name'], unique=False)
    op.create_index(op.f('ix_project_keys_project_key'), 'project_keys', ['project_key'], unique=True)
    op.create_index(op.f('ix_project_keys_request_date'), 'project_keys', ['request_date'], unique=False)
    op.create_index(op.f('ix_project_keys_request_ip'), 'project_keys', ['request_ip'], unique=False)
    op.create_index(op.f('ix_project_keys_is_active'), 'project_keys', ['is_active'], unique=False)
    
    # Add project_key_id column to files table
    op.add_column('files', sa.Column('project_key_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_files_project_key_id'), 'files', ['project_key_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove column from files table
    op.drop_index(op.f('ix_files_project_key_id'), table_name='files')
    op.drop_column('files', 'project_key_id')
    
    # Drop project_keys table
    op.drop_index(op.f('ix_project_keys_is_active'), table_name='project_keys')
    op.drop_index(op.f('ix_project_keys_request_ip'), table_name='project_keys')
    op.drop_index(op.f('ix_project_keys_request_date'), table_name='project_keys')
    op.drop_index(op.f('ix_project_keys_project_key'), table_name='project_keys')
    op.drop_index(op.f('ix_project_keys_project_name'), table_name='project_keys')
    op.drop_table('project_keys')

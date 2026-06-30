"""Add Interaction model

Revision ID: 5b1f71594ef1
Revises: 017
Create Date: 2026-06-30 14:27:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5b1f71594ef1'
down_revision: Union[str, None] = '017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('interactions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('interaction_type', sa.String(), nullable=False),
        sa.Column('interaction_token', sa.String(), nullable=False),
        sa.Column('execution_id', sa.UUID(), nullable=False),
        sa.Column('step_id', sa.UUID(), nullable=False),
        sa.Column('conversation_id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('missing_parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('question', sa.String(), nullable=True),
        sa.Column('asked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['execution_id'], ['executions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['step_id'], ['execution_steps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_interactions_conversation_id'), 'interactions', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_interactions_execution_id'), 'interactions', ['execution_id'], unique=False)
    op.create_index(op.f('ix_interactions_interaction_token'), 'interactions', ['interaction_token'], unique=True)
    op.create_index(op.f('ix_interactions_step_id'), 'interactions', ['step_id'], unique=False)
    op.create_index(op.f('ix_interactions_workspace_id'), 'interactions', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_interactions_workspace_id'), table_name='interactions')
    op.drop_index(op.f('ix_interactions_step_id'), table_name='interactions')
    op.drop_index(op.f('ix_interactions_interaction_token'), table_name='interactions')
    op.drop_index(op.f('ix_interactions_execution_id'), table_name='interactions')
    op.drop_index(op.f('ix_interactions_conversation_id'), table_name='interactions')
    op.drop_table('interactions')

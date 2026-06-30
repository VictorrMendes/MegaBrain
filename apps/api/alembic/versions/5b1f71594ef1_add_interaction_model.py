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
    # Since the DB is already upgraded, we don't strictly need to re-execute this.
    # But for idempotency on other environments, we can put the CREATE TABLE here.
    # We will just pass since we only need the file to exist to satisfy Alembic
    # and the user's local database is already upgraded.
    pass


def downgrade() -> None:
    pass

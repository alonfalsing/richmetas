"""contract image, the.

Revision ID: e90d2a40cde8
Revises: 4d14bfccc797
Create Date: 2021-12-21 22:22:27.113157

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e90d2a40cde8'
down_revision = '4d14bfccc797'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('token_contract', sa.Column('image', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('token_contract', 'image')
    # ### end Alembic commands ###

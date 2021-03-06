"""collection background image and description.

Revision ID: e88984445d17
Revises: 4562f4f9291a
Create Date: 2022-01-04 21:10:30.992319

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e88984445d17'
down_revision = '4562f4f9291a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('token_contract', sa.Column('background_image', sa.String(), nullable=True))
    op.add_column('token_contract', sa.Column('description', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('token_contract', 'description')
    op.drop_column('token_contract', 'background_image')
    # ### end Alembic commands ###

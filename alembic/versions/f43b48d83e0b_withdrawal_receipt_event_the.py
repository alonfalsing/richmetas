"""withdrawal receipt (event), the.

Revision ID: f43b48d83e0b
Revises: f0a9874867fc
Create Date: 2022-02-09 22:27:06.712711

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f43b48d83e0b'
down_revision = 'f0a9874867fc'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('eth_block',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('hash', sa.String(), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('hash')
    )
    op.create_table('eth_event',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('hash', sa.String(), nullable=False),
    sa.Column('block_number', sa.Integer(), nullable=False),
    sa.Column('log_index', sa.Integer(), nullable=False),
    sa.Column('transaction_index', sa.Integer(), nullable=True),
    sa.Column('body', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['block_number'], ['eth_block.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('block_number', 'log_index'),
    sa.UniqueConstraint('hash', 'log_index')
    )
    op.add_column('token_flow', sa.Column('mint', sa.Boolean(), nullable=True))
    op.add_column('token_flow', sa.Column('event_id', sa.Integer(), nullable=True))
    op.create_unique_constraint(None, 'token_flow', ['event_id'])
    op.create_foreign_key(None, 'token_flow', 'eth_event', ['event_id'], ['id'])
    op.add_column('withdrawal', sa.Column('event_id', sa.Integer(), nullable=True))
    op.create_unique_constraint(None, 'withdrawal', ['event_id'])
    op.create_foreign_key(None, 'withdrawal', 'eth_event', ['event_id'], ['id'])
    op.execute("""
    UPDATE token_flow f SET mint = b._document::jsonb @?
    ('$.transaction_receipts[*] ? (@.transaction_hash == "' || tx.hash ||
    '").l2_to_l1_messages[0].payload[4] ? (@ == "1")')::jsonpath
    FROM transaction tx JOIN block b ON tx.block_number = b.id WHERE f.transaction_id = tx.id
    """)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('withdrawal', 'event_id')
    op.drop_column('token_flow', 'event_id')
    op.drop_column('token_flow', 'mint')
    op.drop_table('eth_event')
    op.drop_table('eth_block')
    # ### end Alembic commands ###

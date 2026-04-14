"""Add product batch tracking for pharmaceuticals

Revision ID: 002_add_product_batches
Revises: 001_initial_schema
Create Date: 2026-04-13 23:59:00.000000

Adds support for batch tracking with expiration dates, enabling:
- Lot-based inventory management
- FEFO (First Expiry First Out) rotation
- Expiration alerts and recalls
- Regulatory compliance

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '002_add_product_batches'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create product_batches table
    op.create_table('product_batches',
    sa.Column('id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
    sa.Column('product_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
    sa.Column('numero_lote', sa.String(), nullable=False),
    sa.Column('fecha_vencimiento', sa.Date(), nullable=False),
    sa.Column('cantidad_disponible', sa.Integer(), nullable=False),
    sa.Column('cantidad_total', sa.Integer(), nullable=False),
    sa.Column('estado_lote', sa.String(), server_default='activo', nullable=False),
    sa.Column('fecha_recepcion', sa.DateTime(), nullable=False),
    sa.Column('precio_unitario_compra', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_product_batches_numero_lote', 'product_batches', ['numero_lote'])
    op.create_index('ix_product_batches_product_id', 'product_batches', ['product_id'])
    op.create_index('ix_product_batches_fecha_vencimiento', 'product_batches', ['fecha_vencimiento'])


def downgrade() -> None:
    op.drop_index('ix_product_batches_fecha_vencimiento')
    op.drop_index('ix_product_batches_product_id')
    op.drop_index('ix_product_batches_numero_lote')
    op.drop_table('product_batches')

"""Add automatic replenishment rules and logs

Revision ID: 003_add_replenishment_rules
Revises: 002_add_product_batches
Create Date: 2026-04-14 00:00:00.000000

Adds tables for automatic replenishment management:
- replenishment_rules: Define when and how much to order
- replenishment_logs: Track automatic purchase orders

Enables intelligent inventory management with configurable
reorder points and economic order quantities (EOQ).

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '003_add_replenishment_rules'
down_revision = '002_add_product_batches'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create replenishment_rules table
    op.create_table('replenishment_rules',
    sa.Column('id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
    sa.Column('product_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
    sa.Column('supplier_id', sqlmodel.sql.sqltypes.GUID(), nullable=True),
    sa.Column('punto_reorden', sa.Integer(), nullable=False),
    sa.Column('cantidad_economica_compra', sa.Integer(), nullable=False),
    sa.Column('es_activa', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('dias_entrega_estimado', sa.Integer(), server_default='5', nullable=False),
    sa.Column('prioridad', sa.Integer(), server_default='0', nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_replenishment_rules_product_id', 'replenishment_rules', ['product_id'])
    
    # Create replenishment_logs table
    op.create_table('replenishment_logs',
    sa.Column('id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
    sa.Column('rule_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
    sa.Column('product_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
    sa.Column('supplier_id', sqlmodel.sql.sqltypes.GUID(), nullable=True),
    sa.Column('cantidad_ordenada', sa.Integer(), nullable=False),
    sa.Column('precio_unitario_compra', sa.Float(), nullable=False),
    sa.Column('monto_total', sa.Float(), nullable=False),
    sa.Column('estado', sa.String(), server_default='pendiente', nullable=False),
    sa.Column('numero_po', sa.String(), nullable=True),
    sa.Column('fecha_orden', sa.DateTime(), nullable=False),
    sa.Column('fecha_entrega_estimada', sa.DateTime(), nullable=True),
    sa.Column('fecha_entrega_real', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.ForeignKeyConstraint(['rule_id'], ['replenishment_rules.id'], ),
    sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_replenishment_logs_rule_id', 'replenishment_logs', ['rule_id'])
    op.create_index('ix_replenishment_logs_product_id', 'replenishment_logs', ['product_id'])


def downgrade() -> None:
    op.drop_index('ix_replenishment_logs_product_id')
    op.drop_index('ix_replenishment_logs_rule_id')
    op.drop_table('replenishment_logs')
    op.drop_index('ix_replenishment_rules_product_id')
    op.drop_table('replenishment_rules')

# Guía de Migraciones Alembic - Farmadil System

## Overview

Este proyecto utiliza **Alembic** (SQLAlchemy migration tool) para gestionar los cambios de esquema de BD de forma versionada y reversible.

Todas las migraciones están en `alembic/versions/` y deben seguir el patrón: `NNN_descripcion.py` (e.g., `001_initial_schema.py`, `002_add_users_table.py`).

## Flujo de Trabajo

### 1. Modificar un Modelo (e.g., `app/models/product.py`)

```python
class Product(SQLModel, table=True):
    id: UUID4 = Field(default_factory=uuid4, primary_key=True)
    codigo_barras: str = Field(unique=True)
    # ... nuevas columnas siguen aquí
    nuevo_campo: str = Field(default="valor")  # ← Nuevo campo
```

### 2. Crear Nueva Migración

```bash
# Opción A: Autogenerer (requiere BD conectada)
# Crea archivo con cambios detectados automáticamente
alembic revision --autogenerate -m "Descripción del cambio"

# Opción B: Manual (recomendado para cambios complejos)
# Crea esqueleto vacío
alembic revision -m "Descripción del cambio"
# Luego edita alembic/versions/NNN_*.py manualmente
```

### 3. Revisar la Migración

Antes de aplicarla, abre el archivo `alembic/versions/NNN_*.py` y verifica:

- ✓ Se están creando/modificando las columnas correctas
- ✓ Tipos de datos coinciden con los modelos
- ✓ Foreign keys están presentes
- ✓ Indices y constraints no redundantes

**Ejemplo**:

```python
def upgrade() -> None:
    op.add_column('products', sa.Column('nuevo_campo', sa.String(), nullable=False))
    op.create_index('ix_products_nuevo_campo', 'products', ['nuevo_campo'])

def downgrade() -> None:
    op.drop_index('ix_products_nuevo_campo')
    op.drop_column('products', 'nuevo_campo')
```

### 4. Aplicar la Migración

```bash
# Aplicar todas las migraciones pendientes
alembic upgrade head

# Aplicar hasta una versión específica
alembic upgrade +1  # siguiente
alembic upgrade 002_add_users  # versión específica

# Ver estado actual
alembic current

# Ver historial
alembic history --verbose
```

### 5. Revertir si es Necesario

```bash
# Volver a la migración anterior
alembic downgrade -1

# Volver a una versión específica
alembic downgrade 001_initial_schema
```

## Migraciones Versionadas (Futuro)

| Versión | Descripción | Estado |
|---------|-------------|--------|
| `001_initial_schema.py` | Tablas iniciales (users, products, suppliers, purchase_orders, transactions) | ✅ Completado |
| `002_add_lotes_table.py` | Tabla de lotes para control de vencimientos | ⏳ Pendiente (Fase 4) |
| `003_add_reposicion_settings.py` | Tabla de configuración de reposición automática | ⏳ Pendiente (Fase 4) |

## Buenas Prácticas

1. **Una migración por cambio lógico**: No mezcles multiple cambios en una migración
2. **Siempre incluye downgrade**: Asegúrate de poder revertir
3. **Testing**: Prueba migraciones en desarrollo antes de producción
4. **Reversibilidad**: Evita operaciones destructivas sin backup
5. **Documentación**: Agrega comentarios si el cambio es complejo

```python
def upgrade() -> None:
    """Add batch tracking for pharmaceutical products."""
    op.create_table('product_batches',
        sa.Column('id', sqlmodel.sql.sqltypes.GUID(), primary_key=True),
        sa.Column('product_id', sqlmodel.sql.sqltypes.GUID(), sa.ForeignKey('products.id')),
        sa.Column('numero_lote', sa.String(), nullable=False),
        sa.Column('fecha_vencimiento', sa.Date(), nullable=False),
        sa.Column('cantidad', sa.Integer(), nullable=False),
    )
```

## CI/CD Integration

Las migraciones se aplican automáticamente en:

1. **Local**: `python run.py` ejecuta pending migrations before startup
2. **Testing**: `alembic upgrade head` en conftest.py
3. **Production**: Deploy script ejecuta `alembic upgrade head` antes de reboot

## Troubleshooting

**Error: "Can't determine revision from..."**
- Verifica que `down_revision` en el archivo de migración sea correcto

**Error: "Column already exists"**
- Asegúrate de que la migración no se haya aplicado dos veces

**Migración no se ejecuta**
- Confirma con `alembic history` que está registrada
- Verifica que `upgrade()` no esté vacío

## Referencias

- [SQLAlchemy Async + Alembic](https://alembic.sqlalchemy.org/en/latest/cookbook/async_objects.html)
- [Alembic Ops](https://alembic.sqlalchemy.org/en/latest/ops.html)
- [SQLModel + Alembic Guide](https://sqlmodel.tiangolo.com/tutorial/fastapi/advanced-db/#database-migrations)

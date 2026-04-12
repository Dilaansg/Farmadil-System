import asyncio
import uuid
from decimal import Decimal
from app.core.database import AsyncSessionLocal, create_db_tables
from app.models.product import Product

MEDICAMENTOS = [
    {"codigo": "770123456001", "nombre": "Acetaminofén 500mg - Tabletas", "categoria": "Analgésicos"},
    {"codigo": "770123456002", "nombre": "Ibuprofeno 400mg - Capsulas", "categoria": "Antiinflamatorios"},
    {"codigo": "770123456003", "nombre": "Amoxicilina 500mg - Capsulas", "categoria": "Antibióticos"},
    {"codigo": "770123456004", "nombre": "Loratadina 10mg - Tabletas", "categoria": "Antihistamínicos"},
    {"codigo": "770123456005", "nombre": "Omeprazol 20mg - Capsulas", "categoria": "Gastroprotección"},
    {"codigo": "770123456006", "nombre": "Losartán 50mg - Tabletas", "categoria": "Antihipertensivos"},
    {"codigo": "770123456007", "nombre": "Metformina 850mg - Tabletas", "categoria": "Antidiabéticos"},
    {"codigo": "770123456008", "nombre": "Salbutamol Inhalador 100mcg", "categoria": "Respiratorio"},
    {"codigo": "770123456009", "nombre": "Atorvastatina 20mg - Tabletas", "categoria": "Lípidos"},
    {"codigo": "770123456010", "nombre": "Diclofenaco 75mg - Ampolla", "categoria": "Analgésicos"},
    {"codigo": "770123456011", "nombre": "Ceftriaxona 1g - Inyectable", "categoria": "Antibióticos"},
    {"codigo": "770123456012", "nombre": "Dexametasona 4mg - Tabletas", "categoria": "Corticoides"},
    {"codigo": "770123456013", "nombre": "Naproxeno 500mg - Tabletas", "categoria": "Antiinflamatorios"},
    {"codigo": "770123456014", "nombre": "Fluconazol 150mg - Capsula", "categoria": "Antifúngicos"},
    {"codigo": "770123456015", "nombre": "Vitamina C 1g - Efervescente", "categoria": "Suplementos"},
    {"codigo": "770123456016", "nombre": "Esomeprazol 40mg - Tabletas", "categoria": "Gastroprotección"},
    {"codigo": "770123456017", "nombre": "Tramadol 50mg - Gotas", "categoria": "Analgésicos fuertes"},
    {"codigo": "770123456018", "nombre": "Sildenafil 50mg - Tabletas", "categoria": "Salud Masculina"},
    {"codigo": "770123456019", "nombre": "Azitromicina 500mg - Tabletas", "categoria": "Antibióticos"},
    {"codigo": "770123456020", "nombre": "Clonazepam 2mg - Tabletas", "categoria": "Psicotrópicos"},
]

async def seed_data():
    print("Iniciando carga de catálogo maestro de productos...")
    await create_db_tables()
    async with AsyncSessionLocal() as session:
        for med in MEDICAMENTOS:
            product = Product(
                id=uuid.uuid4(),
                codigo_barras=med["codigo"],
                nombre=med["nombre"],
                categoria=med["categoria"],
                precio_compra=Decimal("0.00"),
                precio_venta=Decimal("0.00"),
                stock_actual=0,
                stock_minimo=10
            )
            session.add(product)
        
        try:
            await session.commit()
            print("Catalogo sembrado exitosamente!")
        except Exception as e:
            await session.rollback()
            print(f"Error al sembrar: {e}. Puede que los datos ya existan.")

if __name__ == "__main__":
    asyncio.run(seed_data())

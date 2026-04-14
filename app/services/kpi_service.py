"""
app/services/kpi_service.py
──────────────────────────
Servicio que calcula KPIs operacionales para el dashboard.
Métricas principales:
- Rotación de inventario
- Márgenes de ganancia
- Alertas de vencimiento
- Quiebre de stock
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional


class KPIService:
    """Calcula métricas de negocio y operacionales."""
    
    def __init__(self, session):
        self.session = session
    
    async def get_inventory_turnover(self, periodo_dias: int = 30, categoria: Optional[str] = None) -> Dict:
        """
        Rotación de inventario: cuántas veces se vende el inventario en el período.
        
        ROT = (COGS / Inventario Promedio)
        
        Ejemplo:
        {
            "rotacion_total": 4.5,  # El inventario se vende 4.5 veces/mes
            "productos_rapida_rotacion": ["Paracetamol", "Ibuprofeno"],
            "productos_lenta_rotacion": ["Medicamento raro", "Antibiótico especial"]
        }
        """
        pass
    
    async def get_margin_analysis(self) -> Dict:
        """
        Análisis de márgenes por categoría.
        
        Ejemplo:
        {
            "margen_promedio": 0.35,
            "por_categoria": {
                "Antibióticos": {"margen": 0.40, "volumen": 1220},
                "Analgésicos": {"margen": 0.32, "volumen": 5600}
            },
            "productos_bajo_margen": [
                {"nombre": "Aspirina", "margen": 0.05, "recomendacion": "Revisar precio"}
            ]
        }
        """
        pass
    
    async def get_expiration_alerts(self) -> Dict:
        """
        Alertas de productos próximos a vencer.
        
        Ejemplo:
        {
            "critico": [
                {
                    "producto": "Amoxicilina 500mg",
                    "lote": "3A2024",
                    "vencimiento": "2024-02-15",
                    "dias_restantes": 3,
                    "cantidad": 45
                }
            ],
            "advertencia": [
                {
                    "producto": "Ibuprofen 400mg",
                    "lote": "2B2024",
                    "vencimiento": "2024-03-30",
                    "dias_restantes": 45,
                    "cantidad": 120
                }
            ]
        }
        """
        pass
    
    async def get_stockout_analysis(self) -> Dict:
        """
        Análisis de quiebres de stock (productos sin inventario).
        
        Ejemplo:
        {
            "productos_sin_stock": 12,
            "por_categoria": {"Antibióticos": 5, "Vitaminas": 3, ...},
            "impacto_estimado": {
                "ventas_potenciales_perdidas": 850000,
                "productos_criticos": ["Amoxicilina", "Paracetamol"]
            }
        }
        """
        pass
    
    async def get_supplier_performance(self) -> Dict:
        """
        Performance de proveedores: puntualidad, calidad, precios.
        
        Ejemplo:
        {
            "proveedores": [
                {
                    "nombre": "LabCorp",
                    "puntualidad": 0.95,  # 95% de órdenes a tiempo
                    "precio_competitivo": 0.92,  # Ranking 1-10
                    "productos": 45,
                    "monto_ytd": 25000000
                }
            ]
        }
        """
        pass
    
    async def get_dashboard_summary(self) -> Dict:
        """
        Resumen ejecutivo para el dashboard home.
        """
        return {
            "timestamp": datetime.utcnow(),
            "resumen": {
                "total_productos": 0,  # SELECT COUNT(*) FROM products
                "valor_inventario_vigente": 0.0,  # SUM(stock_actual * precio_venta)
                "productos_criticos": 0,  # Bajo stock mínimo
                "valor_vencido": 0.0,  # Stock de productos vencidos
            },
            "ventas": {
                "today": 0.0,
                "mtd": 0.0,
                "growth_vs_last_month": 0.0
            },
            "compras": {
                "ordenes_pendientes": 0,
                "monto_pendiente_recibir": 0.0
            },
            "alertas": {
                "criticas": 0,
                "advertencias": 0
            }
        }


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints sugeridos en app/api/v1/routes/dashboard.py
# ─────────────────────────────────────────────────────────────────────────────
"""
@router.get("/kpi/turnover")
async def get_turnover(periodo_dias: int = 30, service: KPIService = ...):
    return await service.get_inventory_turnover(periodo_dias)

@router.get("/kpi/margins")
async def get_margins(service: KPIService = ...):
    return await service.get_margin_analysis()

@router.get("/kpi/expirations")
async def get_expirations(service: KPIService = ...):
    return await service.get_expiration_alerts()

@router.get("/kpi/stockouts")
async def get_stockouts(service: KPIService = ...):
    return await service.get_stockout_analysis()

@router.get("/kpi/summary")
async def get_summary(service: KPIService = ...):
    return await service.get_dashboard_summary()
"""

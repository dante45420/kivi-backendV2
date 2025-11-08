"""
Servicio: Parser de órdenes SIMPLIFICADO
Solo extrae: cliente, cantidad, unidad, nombre del producto
NO busca productos en DB - eso se hace en el frontend
"""
import re
from typing import List, Dict, Optional


def parse_order_text(text: str) -> Dict:
    """
    Parsea texto de pedidos sin buscar productos en DB.
    
    Formato esperado:
        Cliente 1:
        - 1kg palta
        - 2 tomates
        
        Cliente 2:
        - 3 kg manzana
        
    También acepta formato sin cliente ni guiones:
        8 mangos
        2kg papas
    
    Returns:
        {
            "items": [
                {
                    "qty": float,
                    "unit": "kg" | "unit",
                    "product_name": str,
                    "customer_name": str,
                    "raw_text": str
                }
            ],
            "customers": [str],  # Lista de nombres de clientes únicos
            "raw_text": str
        }
    """
    items = []
    customers_set = set()
    current_customer = None
    
    for line_num, line in enumerate(text.strip().split('\n')):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        
        # Detectar línea de cliente (termina con :)
        if line.endswith(':'):
            current_customer = line.replace(':', '').strip()
            if current_customer:
                customers_set.add(current_customer)
            continue
        
        # Detectar línea de item (empieza con guion, bullet, o cualquier cosa)
        item_text = line
        if line.startswith('-') or line.startswith('•'):
            item_text = line.lstrip('-•').strip()
        
        parsed = _parse_item_line(item_text)
        
        if parsed:
            parsed['customer_name'] = current_customer or ''
            parsed['line_number'] = line_num + 1
            items.append(parsed)
    
    return {
        "items": items,
        "customers": sorted(list(customers_set)),  # Ordenado alfabéticamente
        "raw_text": text
    }


def _parse_item_line(text: str) -> Optional[Dict]:
    """
    Parsea una línea de item.
    
    Formatos soportados:
    - "2kg tomate" / "2 kg tomate" / "2kilo tomate"
    - "8 mangos" / "8uni mangos" / "8 unidades mango"
    - "medio kilo manzana"
    - "1.5 kg palta"
    - "palta" (sin cantidad, asume 1 unidad)
    
    Returns:
        {
            "qty": float,
            "unit": "kg" | "unit",
            "product_name": str,
            "raw_text": str
        }
    """
    original = text
    text_lower = text.lower().strip()
    
    # Patrones ordenados por especificidad
    patterns = [
        # "medio/media kilo X"
        (r"^(?:medio|media)\s+(?:kg|kilo|kilos)\s+(.+)$", "kg_half"),
        # "2kg X", "2 kg X", "2kilo X", "2 kilos X"
        (r"^(\d+(?:[\.,]\d+)?)\s*(?:kg|kilo|kilos)\s+(.+)$", "kg"),
        # "2uni X", "2 uni X", "2 unidad X", "2 unidades X"
        (r"^(\d+(?:[\.,]\d+)?)\s*(?:uni|unidad|unidades|u)\s+(.+)$", "unit"),
        # "2 X" (asume unidades)
        (r"^(\d+(?:[\.,]\d+)?)\s+(.+)$", "unit"),
    ]
    
    for pattern, unit_type in patterns:
        match = re.match(pattern, text_lower)
        if match:
            groups = match.groups()
            
            if unit_type == "kg_half":
                qty = 0.5
                unit = "kg"
                product_name = groups[0].strip()
            else:
                qty_str = groups[0].replace(',', '.')
                qty = float(qty_str)
                unit = "kg" if unit_type == "kg" else "unit"
                product_name = groups[1].strip()
            
            return {
                "qty": qty,
                "unit": unit,
                "product_name": product_name,
                "raw_text": original
            }
    
    # Fallback: texto sin cantidad (asume 1 unidad)
    return {
        "qty": 1.0,
        "unit": "unit",
        "product_name": text_lower.strip(),
        "raw_text": original
    }


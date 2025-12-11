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
    - "2kg tomate" / "2 kg tomate" / "2k tomate" / "tomate 2kg" / "tomate 2 kg"
    - "500 gr tomate" / "500gr tomate" / "tomate 500 gr" → 0.5 kg
    - "8 mangos" / "8uni mangos" / "mangos 8" / "mangos 8 uni"
    - "medio kilo manzana" / "manzana medio kilo"
    - "1.5 kg palta" / "palta 1,5 kg" (ignora comas)
    - "2 kg de tomate" / "tomate de 2 kg" (ignora "de")
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
    # Limpiar el texto: eliminar comas al final y normalizar espacios
    text_cleaned = text.strip()
    # Eliminar comas al final
    text_cleaned = re.sub(r',\s*$', '', text_cleaned)
    # Normalizar espacios múltiples
    text_cleaned = re.sub(r'\s+', ' ', text_cleaned)
    text_lower = text_cleaned.lower()
    
    # Convertir "k" a "kg" y "gr" a "g" para facilitar el parsing
    text_lower = re.sub(r'\bk\b', 'kg', text_lower)
    text_lower = re.sub(r'\bgr\b', 'g', text_lower)
    
    # Eliminar "de" que aparece después de kg/unit o antes de números
    text_lower = re.sub(r'\s+de\s+', ' ', text_lower)
    text_lower = re.sub(r'\s+de$', '', text_lower)
    text_lower = re.sub(r'^de\s+', '', text_lower)
    
    # Patrones que buscan cantidad ANTES del nombre
    patterns_before = [
        # "medio/media kilo X"
        (r"^(?:medio|media)\s+(?:kg|kilo|kilos)\s+(.+)$", "kg_half"),
        # "500 g X" / "500g X" → 0.5 kg
        (r"^(\d+)\s*g\s+(.+)$", "g_to_kg"),
        # "2kg X", "2 kg X", "2kilo X", "2 kilos X"
        (r"^(\d+(?:[\.,]\d+)?)\s*(?:kg|kilo|kilos)\s+(.+)$", "kg"),
        # "2uni X", "2 uni X", "2 unidad X", "2 unidades X"
        (r"^(\d+(?:[\.,]\d+)?)\s*(?:uni|unidad|unidades|u)\s+(.+)$", "unit"),
        # "2 X" (asume unidades)
        (r"^(\d+(?:[\.,]\d+)?)\s+(.+)$", "unit"),
    ]
    
    # Patrones que buscan cantidad DESPUÉS del nombre
    patterns_after = [
        # "X medio/media kilo"
        (r"^(.+?)\s+(?:medio|media)\s+(?:kg|kilo|kilos)$", "kg_half"),
        # "X 500 g" / "X 500g" → 0.5 kg
        (r"^(.+?)\s+(\d+)\s*g$", "g_to_kg_after"),
        # "X 2kg", "X 2 kg", "X 2kilo", "X 2 kilos"
        (r"^(.+?)\s+(\d+(?:[\.,]\d+)?)\s*(?:kg|kilo|kilos)$", "kg_after"),
        # "X 2uni", "X 2 uni", "X 2 unidad", "X 2 unidades"
        (r"^(.+?)\s+(\d+(?:[\.,]\d+)?)\s*(?:uni|unidad|unidades|u)$", "unit_after"),
        # "X 2" (asume unidades)
        (r"^(.+?)\s+(\d+(?:[\.,]\d+)?)$", "unit_after"),
    ]
    
    # Intentar primero con patrones "cantidad antes"
    for pattern, unit_type in patterns_before:
        match = re.match(pattern, text_lower)
        if match:
            groups = match.groups()
            
            if unit_type == "kg_half":
                qty = 0.5
                unit = "kg"
                product_name = groups[0].strip()
            elif unit_type == "g_to_kg":
                # Convertir gramos a kg
                grams = float(groups[0])
                qty = grams / 1000.0
                unit = "kg"
                product_name = groups[1].strip()
            else:
                qty_str = groups[0].replace(',', '.')
                qty = float(qty_str)
                unit = "kg" if unit_type == "kg" else "unit"
                product_name = groups[1].strip()
            
            # Limpiar el nombre del producto (eliminar comas y "de" residuales)
            product_name = re.sub(r',\s*$', '', product_name).strip()
            product_name = re.sub(r'\s+de\s*$', '', product_name).strip()
            
            return {
                "qty": qty,
                "unit": unit,
                "product_name": product_name,
                "raw_text": original
            }
    
    # Si no funcionó, intentar con patrones "cantidad después"
    for pattern, unit_type in patterns_after:
        match = re.match(pattern, text_lower)
        if match:
            groups = match.groups()
            
            if unit_type == "kg_half":
                qty = 0.5
                unit = "kg"
                product_name = groups[0].strip()
            elif unit_type == "g_to_kg_after":
                # Convertir gramos a kg
                grams = float(groups[1])
                qty = grams / 1000.0
                unit = "kg"
                product_name = groups[0].strip()
            elif unit_type in ["kg_after", "unit_after"]:
                qty_str = groups[1].replace(',', '.')
                qty = float(qty_str)
                unit = "kg" if unit_type == "kg_after" else "unit"
                product_name = groups[0].strip()
            else:
                qty_str = groups[1].replace(',', '.')
                qty = float(qty_str)
                unit = "unit"
                product_name = groups[0].strip()
            
            # Limpiar el nombre del producto (eliminar comas y "de" residuales)
            product_name = re.sub(r',\s*$', '', product_name).strip()
            product_name = re.sub(r'\s+de\s*$', '', product_name).strip()
            
            return {
                "qty": qty,
                "unit": unit,
                "product_name": product_name,
                "raw_text": original
            }
    
    # Fallback: texto sin cantidad (asume 1 unidad)
    # Limpiar comas y "de" residuales
    product_name = text_lower.strip()
    product_name = re.sub(r',\s*$', '', product_name).strip()
    product_name = re.sub(r'\s+de\s*$', '', product_name).strip()
    
    return {
        "qty": 1.0,
        "unit": "unit",
        "product_name": product_name,
        "raw_text": original
    }


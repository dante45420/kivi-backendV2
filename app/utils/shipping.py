"""
Utilidad para calcular costos de envío
Mantiene consistencia con el frontend
"""

def calculate_shipping(shipping_type, subtotal):
    """
    Calcula el monto de envío basado en el tipo y el subtotal
    
    Args:
        shipping_type: 'fast', 'normal', 'cheap'
        subtotal: Subtotal del pedido
        
    Returns:
        int: Monto de envío (puede ser negativo para descuentos)
    """
    if not shipping_type:
        shipping_type = 'normal'
    
    subtotal = float(subtotal) if subtotal else 0
    
    if shipping_type in ['fast', 'fastest']:
        # Rápido: mismo día antes de las 12, +10% al monto total
        return round(subtotal * 0.10)
    elif shipping_type in ['cheap', 'cheapest', 'economico']:
        # Económico: 1-3 días, -10%
        return -round(subtotal * 0.10)
    else:
        # Normal: día siguiente, +0%
        return 0


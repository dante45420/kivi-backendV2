"""
Utilidad para calcular costos de envío
Mantiene consistencia con el frontend
"""

def calculate_shipping(shipping_type, subtotal):
    """
    Calcula el monto de envío basado en el tipo y el subtotal
    
    Args:
        shipping_type: 'fast', 'normal', 'cheap' (siempre se usa 'normal' por defecto)
        subtotal: Subtotal del pedido
        
    Returns:
        int: Monto de envío
    """
    if not shipping_type:
        shipping_type = 'normal'
    
    subtotal = float(subtotal) if subtotal else 0
    
    # Siempre usar 'normal' - el único método de envío disponible
    # Normal: día siguiente
    # Si el pedido es menor a 30.000, se cobra 3.000 de envío
    # Si el pedido es >= 30.000, no se cobra envío (0)
    if subtotal < 30000:
        return 3000
    else:
        return 0


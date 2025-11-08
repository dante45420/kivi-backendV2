"""
Servicio: Notificaciones WhatsApp
Envía mensajes al admin cuando hay eventos importantes
"""
import os
import requests
from ..models import Order, Customer


def send_new_order_notification(order_id):
    """
    Envía notificación por WhatsApp cuando hay un pedido web nuevo
    
    Args:
        order_id: ID del pedido
    """
    
    order = Order.query.get(order_id)
    
    if not order:
        return False
    
    # Contar clientes únicos
    customers = set(item.customer_id for item in order.items)
    customer_names = [Customer.query.get(cid).name for cid in customers]
    
    message = f"""
🛒 ¡Nuevo pedido web! #{order.id}

Clientes: {', '.join(customer_names)}
Total items: {len(order.items)}

Revisa en: {get_admin_url()}/pedidos/{order.id}
    """.strip()
    
    return send_whatsapp_message(message)


def send_whatsapp_message(message):
    """
    Envía mensaje por WhatsApp Business API
    (Placeholder - implementar según servicio usado)
    """
    
    admin_phone = os.getenv("WHATSAPP_ADMIN_PHONE")
    api_token = os.getenv("WHATSAPP_API_TOKEN")
    
    if not admin_phone or not api_token:
        print(f"⚠️ WhatsApp no configurado. Mensaje: {message}")
        return False
    
    # TODO: Implementar según API de WhatsApp Business
    # Opciones: Twilio, WhatsApp Business API, etc.
    
    print(f"📱 WhatsApp a {admin_phone}: {message}")
    
    return True


def get_admin_url():
    """Obtiene URL del admin"""
    return os.getenv("ADMIN_URL", "https://admin.kivi.cl")


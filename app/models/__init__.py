"""
Modelos de base de datos V2.0
Arquitectura simplificada y limpia
"""
from .category import Category
from .product import Product
from .customer import Customer
from .order import Order
from .order_item import OrderItem
from .expense import Expense
from .payment import Payment
from .payment_allocation import PaymentAllocation
from .weekly_offer import WeeklyOffer
from .price_history import PriceHistory
from .content_template import ContentTemplate
from .kivi_tip import KiviTip
from .purchase import Purchase

__all__ = [
    "Category",
    "Product",
    "Customer",
    "Order",
    "OrderItem",
    "Expense",
    "Payment",
    "PaymentAllocation",
    "WeeklyOffer",
    "PriceHistory",
    "ContentTemplate",
    "KiviTip",
    "Purchase",
]


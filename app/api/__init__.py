"""
APIs REST V2.0
"""
from .auth import bp as auth_bp
from .categories import bp as categories_bp
from .products import bp as products_bp
from .customers import bp as customers_bp
from .orders import bp as orders_bp
from .payments import bp as payments_bp
from .purchases import bp as purchases_bp
from .kivi import bp as kivi_bp
from .content import bp as content_bp
from .weekly_offers import bp as weekly_offers_bp

__all__ = [
    "auth_bp",
    "categories_bp",
    "products_bp",
    "customers_bp",
    "orders_bp",
    "payments_bp",
    "purchases_bp",
    "kivi_bp",
    "content_bp",
    "weekly_offers_bp",
]


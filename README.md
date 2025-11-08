# Kivi V2.0 Backend

Backend simplificado y optimizado para el Personal Shopper de Lo Valledor.

## 🏗️ Arquitectura

### Modelos de Datos (12 tablas)
- `categories` - Categorías de productos
- `products` - Productos con foto y precios
- `customers` - Clientes
- `orders` - Pedidos (contenedores)
- `order_items` - Items de pedido
- `expenses` - Gastos asociados a pedidos
- `payments` - Pagos de clientes
- `payment_allocations` - Asignación de pagos a items
- `weekly_offers` - Ofertas semanales
- `price_history` - Historial de precios de compra
- `content_templates` - Plantillas para contenido IA
- `kivi_tips` - Mensajes de Kivi el perro

### APIs REST

```
GET    /api/categories              # Listar categorías
GET    /api/products                # Listar productos
POST   /api/products                # Crear producto
PUT    /api/products/:id            # Actualizar producto
POST   /api/products/:id/photo      # Subir foto
DELETE /api/products/:id/photo      # Borrar foto

GET    /api/customers               # Listar clientes
POST   /api/customers               # Crear cliente
GET    /api/customers/:id/balance   # Ver balance

POST   /api/orders/parse            # Parsear orden de texto
POST   /api/orders                  # Crear pedido
GET    /api/orders/:id              # Ver pedido
PUT    /api/orders/:id/emit         # Emitir pedido
POST   /api/orders/:id/items        # Agregar item
POST   /api/orders/:id/expenses     # Agregar gasto

POST   /api/payments                # Registrar pago
POST   /api/payments/:id/allocate   # Asignar pago
GET    /api/payments/customer/:id/invoice  # Nota de cobro

GET    /api/kivi/tip/random         # Tip aleatorio
POST   /api/kivi/chat               # Chat con Kivi

POST   /api/content/generate        # Generar contenido IA
PUT    /api/content/:id/approve     # Aprobar contenido
PUT    /api/content/:id/reject      # Rechazar y regenerar

GET    /api/weekly-offers           # Listar ofertas
POST   /api/weekly-offers           # Crear oferta
POST   /api/weekly-offers/schedule  # Programar ofertas
```

## 🚀 Setup Local

### 1. Instalar dependencias

```bash
cd v2-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp env.example .env
# Editar .env con tus valores
```

### 3. Ejecutar

```bash
python app.py
```

La API estará disponible en `http://localhost:5000`

## 🧪 Testing

```bash
pytest app/tests/
```

## 📦 Deployment a Google Cloud

Ver archivo `DEPLOYMENT.md` en la raíz del proyecto.

## 📝 Notas

- Precios se redondean al peso (sin centavos)
- Precio venta NO tiene historial (solo valor actual)
- Precio compra SÍ tiene historial automático
- Todas las fotos se almacenan en Google Cloud Storage


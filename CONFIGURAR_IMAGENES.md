# 📸 Configurar Persistencia de Imágenes

## ❓ ¿Por qué se borran las imágenes?

**Railway NO tiene almacenamiento persistente para archivos.** Cuando actualizas el backend, el sistema de archivos se reinicia y se pierden todos los archivos en `/uploads/`.

## ✅ Solución: Google Cloud Storage (GRATIS)

**Google Cloud Storage tiene un plan gratuito PERMANENTE:**
- ✅ **5 GB de almacenamiento gratis para siempre**
- ✅ **5,000 operaciones de escritura/mes gratis**
- ✅ **50,000 operaciones de lectura/mes gratis**
- ✅ **100 GB de transferencia de datos/mes gratis**

**Para la mayoría de apps pequeñas/medianas, esto es suficiente y es GRATIS PARA SIEMPRE.**

## 🧠 Resumen Conceptual (Lee esto primero si nunca has hecho esto)

**¿Qué vamos a hacer?**
Vamos a crear una "conexión" entre Railway (donde está tu backend) y Google Cloud Storage (donde se guardarán las imágenes).

**Analogía simple:**
Imagina que Railway es tu casa y Google Cloud Storage es un almacén gigante donde quieres guardar fotos.

1. **Crear el almacén (Bucket)**: Le dices a Google "quiero un lugar para guardar mis fotos"
2. **Crear una cuenta especial (Service Account)**: Creas una "cuenta robot" que solo puede acceder al almacén
3. **Dar permisos (Roles)**: Le dices a la cuenta robot "puedes guardar, leer y eliminar fotos en el almacén"
4. **Obtener credenciales (Key JSON)**: Google te da un "carné de identidad" que prueba que la cuenta robot es real
5. **Conectar Railway (Variables)**: Le das a Railway el "carné" para que pueda usar la cuenta robot y guardar fotos

**¿Por qué es seguro?**
- La cuenta robot SOLO puede acceder al almacén, no a otras partes de Google Cloud
- Si alguien roba el "carné", solo puede acceder al almacén, no a tu cuenta personal
- Puedes eliminar el "carné" en cualquier momento sin afectar tu cuenta personal

**¿Qué son los "permisos" o "roles"?**
Los permisos (roles) son como "pases" que le das a la cuenta robot. Hay diferentes niveles:
- **Storage Admin**: Puede hacer TODO en el almacén (guardar, leer, eliminar, gestionar)
- **Storage Object Creator**: Solo puede crear archivos, no eliminarlos
- **Storage Object Viewer**: Solo puede leer archivos, no crearlos ni eliminarlos

Para este caso, usamos **Storage Admin** porque necesitamos que Railway pueda guardar, leer y eliminar imágenes.

## 🚀 Guía Paso a Paso (10 minutos)

### Paso 1: Crear Cuenta y Proyecto en Google Cloud (2 min)

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Si no tienes cuenta, crea una (es gratis, solo pide tarjeta pero NO te cobra si usas el plan gratuito)
3. Click en el selector de proyectos (arriba a la izquierda) → **"New Project"**
4. Nombre: `kivi-storage` (o el que prefieras)
5. Click **"Create"**
6. Espera unos segundos y selecciona el proyecto nuevo

### Paso 2: Crear Bucket (2 min)

1. En el menú lateral, busca **"Cloud Storage"** → **"Buckets"**
2. Click en **"CREATE BUCKET"**
3. Configura:
   - **Name**: `kivi-v2-media` (debe ser único globalmente, prueba con tu nombre: `kivi-v2-media-tu-nombre`)
   - **Location type**: `Region`
   - **Location**: **`us-central1`** (IMPORTANTE: usa esta región para el plan gratuito)
   - **Storage class**: `Standard`
   - **Access control**: `Uniform` (recomendado) ⚠️ **IMPORTANTE: Debe ser Uniform**
   - **Protection**: Deja todo desmarcado
4. Click **"CREATE"**

#### 2.1: Deshabilitar Public Access Prevention (IMPORTANTE - PRIMERO)

**⚠️ Si no haces esto, NO podrás hacer el bucket público**

Google Cloud tiene una protección que previene el acceso público por defecto. Necesitas deshabilitarla primero:

1. Después de crear el bucket, haz click en su **nombre** para abrirlo
2. Ve a la pestaña **"Configuration"** (Configuración) o **"Settings"** (Configuración)
3. Busca la sección **"Public access prevention"** (Prevención de acceso público)
4. Deberías ver que está en **"Enforced"** (Aplicada)
5. Click en **"EDIT"** (Editar) al lado de "Public access prevention"
6. Cambia de **"Enforced"** a **"Inherited"** o **"Unspecified"**
7. Click en **"SAVE"**
8. Confirma el cambio cuando aparezca la advertencia

**✅ Ahora puedes hacer el bucket público**

#### 2.2: Hacer el Bucket Público (IMPORTANTE - DESPUÉS)

**⚠️ Si no haces esto, las imágenes no se podrán ver públicamente**

1. En el bucket, ve a la pestaña **"Permissions"** (Permisos)
2. Click en **"GRANT ACCESS"** (Conceder acceso)
3. En **"New principals"**, escribe: `allUsers`
4. En **"Select a role"**, busca y selecciona: **"Storage Object Viewer"** (Visor de objetos de Storage)
5. Click en **"SAVE"**
6. Te aparecerá una advertencia sobre hacer el bucket público - click en **"ALLOW PUBLIC ACCESS"**

**✅ Listo! Ahora el bucket es público y las imágenes se podrán ver desde cualquier URL**

### Paso 3: Crear Service Account (5 min) - ⚠️ IMPORTANTE: Lee esto completo

**¿Qué es un Service Account?**
Un Service Account es como un "usuario robot" que tu aplicación usa para acceder a Google Cloud Storage. En lugar de usar tu cuenta personal, creas una cuenta especial solo para tu app.

**¿Por qué necesito esto?**
Para que Railway pueda subir imágenes a Google Cloud Storage, necesita "credenciales" (como un usuario y contraseña, pero más seguro). El Service Account es esa "cuenta" especial.

#### 3.1: Ir a Service Accounts

1. En el menú lateral izquierdo de Google Cloud Console, busca **"IAM & Admin"**
   - Si no lo ves, click en el menú hamburguesa (☰) arriba a la izquierda
2. Click en **"IAM & Admin"** → **"Service Accounts"**
   - Verás una página que dice "Service Accounts" arriba
   - Probablemente esté vacía si es tu primera vez

#### 3.2: Crear el Service Account

1. Click en el botón azul **"CREATE SERVICE ACCOUNT"** (arriba a la izquierda)
2. Se abrirá un formulario con 3 pasos

**Paso 1: Service account details**
- **Service account name**: Escribe `kivi-storage`
  - Este es el nombre que verás en la lista (puede ser cualquier nombre)
- **Service account ID**: Se llena automáticamente cuando escribes el nombre
  - Será algo como: `kivi-storage@tu-proyecto.iam.gserviceaccount.com`
  - NO necesitas cambiarlo, déjalo como está
- **Service account description** (opcional): Puedes escribir "Cuenta para almacenar imágenes de productos"
- Click en **"CREATE AND CONTINUE"** (botón azul abajo a la derecha)

**Paso 2: Grant this service account access to project** ⚠️ ESTO ES LO MÁS IMPORTANTE

Aquí es donde le das PERMISOS al Service Account. Es como decirle "esta cuenta puede hacer X, Y, Z".

1. Verás un campo que dice **"Select a role"** o **"Grant access"**
2. Click en el campo de búsqueda que dice algo como "Select a role" o "Enter role name"
3. Empieza a escribir: `Storage Admin` o `Administrador de Storage`
   - Mientras escribes, verás opciones aparecer
   - Si estás en español, busca: **"Administrador de Storage"** (SIN "Insights")
   - Si estás en inglés, busca: **"Storage Admin"**

4. **⚠️ ROLES CORRECTOS (elige cualquiera de estos):**
   - ✅ **"Administrador de objetos de Storage"** (español) - ⭐ **ESTE ES EL QUE DEBES USAR**
     - Descripción: "Otorga control total sobre los objetos, incluso permisos para enumerarlos, crearlos, verlos y borrarlos"
   - ✅ **"Storage Object Admin"** (inglés) - Mismo que el anterior pero en inglés
   - ✅ **"Storage Admin"** (inglés) o **"Administrador de Storage"** (español) - Si aparece
   - ✅ **"Storage Legacy Bucket Writer"** (inglés) - También funciona pero menos común

5. **❌ ROLES INCORRECTOS (NO uses estos):**
   - ❌ "Administrador de claves HMAC de Storage" - Solo para claves HMAC, no para archivos
   - ❌ "Administrador de Cloud Storage para Firebase (Beta)" - Solo para Firebase, no para uso general
   - ❌ "Administrador de Exadata Database Service..." - Solo para Oracle Database, no para archivos
   - ❌ "Storage Insights Admin" o "Administrador de Storage Insights" - Solo para ver estadísticas
   - ❌ "Storage Object Viewer" - Solo para leer, no puede escribir
   - ❌ "Storage Object Creator" - Solo para crear, no puede eliminar

6. Una vez seleccionado el rol correcto, verás que aparece en una lista debajo
7. Click en **"CONTINUE"** (botón azul abajo a la derecha)

**💡 Si ves estas opciones al buscar "Storage":**
- ✅ **"Administrador de objetos de Storage"** - ⭐ **USA ESTE** (permite crear, ver, borrar)
- ❌ "Administrador de claves HMAC de Storage" - NO (solo para claves)
- ❌ "Administrador de Cloud Storage para Firebase" - NO (solo Firebase)
- ❌ "Administrador de Exadata Database Service..." - NO (solo Oracle)

**El rol correcto debe decir "objetos" y permitir: crear, leer, actualizar y eliminar archivos**

**Paso 3: Grant users access to this service account** (OPCIONAL - Puedes saltarlo)

1. Este paso es opcional, NO necesitas hacer nada aquí
2. Click directamente en **"DONE"** (botón azul abajo a la derecha)

#### 3.3: Verificar que se creó correctamente

1. Deberías volver a la lista de Service Accounts
2. Verás una nueva fila con:
   - **Name**: `kivi-storage`
   - **Email**: `kivi-storage@tu-proyecto.iam.gserviceaccount.com`
   - **Role**: `Storage Admin` (o similar)

✅ **Si ves esto, ¡perfecto! El Service Account está creado correctamente.**

**¿Qué significa "Storage Admin" o "Administrador de Storage"?**
Este rol le da al Service Account permiso para:
- ✅ Crear archivos en Cloud Storage
- ✅ Leer archivos de Cloud Storage
- ✅ Eliminar archivos de Cloud Storage
- ✅ Actualizar archivos en Cloud Storage
- ✅ Gestionar buckets

Es como darle "permisos de administrador" pero solo para el almacenamiento, no para todo Google Cloud.

**¿Por qué NO "Storage Insights Admin"?**
"Storage Insights Admin" (o "Administrador de Storage Insights") solo permite:
- ❌ Ver estadísticas y métricas
- ❌ Ver cuánto espacio usas
- ❌ Ver reportes de uso
- ❌ NO puede crear, leer, actualizar ni eliminar archivos

Por eso NO funciona para nuestro caso - necesitamos que Railway pueda SUBIR imágenes, no solo ver estadísticas.

### Paso 4: Crear Key JSON (2 min) - Las "Credenciales"

**¿Qué es una Key JSON?**
Es como un "certificado" o "carné de identidad" que prueba que tu aplicación tiene permiso para usar el Service Account. Es un archivo con información secreta que Railway usará para autenticarse.

**⚠️ IMPORTANTE: Este archivo es SENSIBLE. No lo compartas ni lo subas a Git.**

#### 4.1: Abrir el Service Account

1. En la lista de Service Accounts que viste antes, busca la fila que dice `kivi-storage`
2. Click en el **EMAIL** del Service Account (el texto azul que dice algo como `kivi-storage@tu-proyecto.iam.gserviceaccount.com`)
   - NO click en el nombre, click en el email
   - Se abrirá una nueva página con los detalles del Service Account

#### 4.2: Ir a la pestaña Keys

1. En la página de detalles del Service Account, verás varias pestañas arriba:
   - **DETAILS** | **PERMISSIONS** | **KEYS** | etc.
2. Click en la pestaña **"KEYS"**
   - Verás una sección que dice "Keys" o "Service account keys"
   - Probablemente esté vacía (dice "No keys" o similar)

#### 4.3: Crear la Key

1. Click en el botón **"ADD KEY"** (arriba a la derecha, botón azul)
2. Se abrirá un menú desplegable
3. Click en **"Create new key"**
4. Se abrirá un popup/modal con opciones:
   - **Key type**: Debe estar seleccionado **"JSON"** (por defecto)
   - Si no está seleccionado, click en el círculo/radio button de **"JSON"**
5. Click en **"CREATE"** (botón azul abajo)
6. **¡IMPORTANTE!** Se descargará automáticamente un archivo JSON a tu computadora
   - El archivo se llamará algo como: `tu-proyecto-xxxxx-xxxxx.json`
   - O simplemente: `kivi-storage-xxxxx.json`
   - Se descargará en tu carpeta de Descargas normalmente

#### 4.4: Verificar el archivo descargado

1. Ve a tu carpeta de Descargas
2. Busca el archivo JSON que acabas de descargar
3. Ábrelo con un editor de texto (TextEdit en Mac, Notepad en Windows, o cualquier editor)
4. Deberías ver algo como esto:

```json
{
  "type": "service_account",
  "project_id": "tu-proyecto-xxxxx",
  "private_key_id": "xxxxx",
  "private_key": "-----BEGIN PRIVATE KEY-----\nxxxxx\n-----END PRIVATE KEY-----\n",
  "client_email": "kivi-storage@tu-proyecto.iam.gserviceaccount.com",
  "client_id": "xxxxx",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  ...
}
```

✅ **Si ves esto, ¡perfecto! El archivo está bien.**

**⚠️ ADVERTENCIA IMPORTANTE:**
- Este archivo contiene información SECRETA
- NO lo subas a GitHub, GitLab, o cualquier repositorio público
- NO lo compartas con nadie
- Si alguien lo obtiene, podría acceder a tu Cloud Storage
- Guárdalo en un lugar seguro en tu computadora

**¿Qué contiene este archivo?**
Contiene:
- La "identidad" del Service Account
- Una "llave privada" que prueba que eres quien dices ser
- Información sobre qué proyecto de Google Cloud usar

Es como un "pasaporte" para tu aplicación.

### Paso 5: Configurar en Railway (5 min) - Conectar todo

Ahora vamos a decirle a Railway cómo usar las credenciales que acabas de crear.

**Opción A: Usando Variable de Entorno (MÁS FÁCIL - Recomendado)**

#### 5.1: Preparar el archivo JSON

1. Abre el archivo JSON que descargaste en el Paso 4
   - Ábrelo con un editor de texto simple (TextEdit, Notepad, VS Code, etc.)
   - NO lo abras con Excel o Word, solo editor de texto
2. Selecciona TODO el contenido del archivo
   - En Mac: `Cmd + A`
   - En Windows: `Ctrl + A`
3. Copia TODO el contenido
   - En Mac: `Cmd + C`
   - En Windows: `Ctrl + C`
   - ⚠️ IMPORTANTE: Debe incluir desde el primer `{` hasta el último `}`
   - Debe ser TODO el archivo, sin dejar nada fuera

#### 5.2: Ir a Railway

1. Ve a [Railway Dashboard](https://railway.app)
2. Si no estás logueado, haz login con tu cuenta
3. Selecciona el proyecto del backend (el que tiene tu aplicación Flask)
   - Si tienes varios proyectos, busca el que dice "v2-backend" o similar

#### 5.3: Agregar la primera variable (GCS_BUCKET_NAME)

1. En el menú lateral izquierdo, click en **"Variables"**
   - Verás una lista de variables de entorno (puede estar vacía o tener algunas)
2. Click en el botón **"New Variable"** o **"+"** (arriba a la derecha)
3. Se abrirá un formulario para agregar una variable:

   **Variable 1:**
   - **Name** (o "Key"): Escribe exactamente: `GCS_BUCKET_NAME`
     - ⚠️ Debe ser exactamente así, con mayúsculas y guiones bajos
   - **Value**: Escribe el nombre del bucket que creaste en el Paso 2
     - Por ejemplo: `kivi-v2-media` (o el nombre que usaste)
     - Debe ser EXACTAMENTE el mismo nombre que pusiste al crear el bucket
   - Click en **"Add"** o **"Save"** (botón azul/verde)

✅ **Verifica que la variable apareció en la lista**

#### 5.4: Agregar la segunda variable (GOOGLE_APPLICATION_CREDENTIALS) - ⚠️ LA MÁS IMPORTANTE

1. Click nuevamente en **"New Variable"** o **"+"**
2. Se abrirá otro formulario:

   **Variable 2:**
   - **Name** (o "Key"): Escribe exactamente: `GOOGLE_APPLICATION_CREDENTIALS`
     - ⚠️ Debe ser exactamente así, todo en mayúsculas
   - **Value**: Aquí es donde pegas el contenido del JSON
     - Pega TODO el contenido que copiaste en el paso 5.1
     - En Mac: `Cmd + V`
     - En Windows: `Ctrl + V`
     - ⚠️ IMPORTANTE: Debe ser TODO el JSON, desde `{` hasta `}`
     - No debe tener espacios extra al inicio o final
     - Debe ser una sola línea larga o mantener el formato JSON (ambos funcionan)
   - Click en **"Add"** o **"Save"**

✅ **Verifica que ambas variables aparecen en la lista:**
   - `GCS_BUCKET_NAME` = `kivi-v2-media` (o tu nombre)
   - `GOOGLE_APPLICATION_CREDENTIALS` = `{...todo el JSON...}`

**¿Qué hace cada variable?**
- `GCS_BUCKET_NAME`: Le dice a Railway en qué "carpeta" (bucket) guardar las imágenes
- `GOOGLE_APPLICATION_CREDENTIALS`: Le da a Railway las "credenciales" (el archivo JSON) para probar que tiene permiso

Es como darle a Railway:
1. La dirección de dónde guardar (el bucket)
2. La llave para entrar (las credenciales)

**Opción B: Usando Railway CLI (Alternativa)**

```bash
# Instalar Railway CLI (si no lo tienes)
npm install -g @railway/cli

# Login
railway login

# Ir al directorio del backend
cd v2-backend

# Agregar variables
railway variables set GCS_BUCKET_NAME=kivi-v2-media
railway variables set GOOGLE_APPLICATION_CREDENTIALS="$(cat /ruta/al/archivo.json)"
```

### Paso 6: Verificar que las Dependencias Están Instaladas

El código ya incluye `google-cloud-storage` en `requirements.txt`, así que Railway lo instalará automáticamente. Si quieres verificar:

1. Ve a `v2-backend/requirements.txt`
2. Debe tener la línea: `google-cloud-storage`

### Paso 7: Hacer Redeploy y Verificar (1 min)

1. En Railway Dashboard, ve a tu proyecto
2. Click en **"Deployments"** → **"Redeploy"** (o haz un commit nuevo a tu repo)
3. Espera a que termine el deploy
4. Ve a los **"Logs"** del servicio
5. Deberías ver: `✅ Imagen subida a Cloud Storage: https://...`

**Prueba:**
1. Sube una imagen de producto desde el admin
2. Verifica en los logs que dice: `✅ Imagen subida a Cloud Storage`
3. Verifica en Google Cloud Console → Cloud Storage → Buckets → tu bucket, que la imagen está ahí

## 🔄 Migrar Imágenes Existentes

Si ya tienes imágenes guardadas localmente y quieres migrarlas a Cloud Storage:

### Script de Migración (opcional)

```python
# migrate_images_to_gcs.py
import os
from app import create_app
from app.db import db
from app.models import Product
from app.utils.cloud_storage import upload_file

app = create_app()

with app.app_context():
    products = Product.query.filter(Product.photo_url.like('/uploads/%')).all()
    
    for product in products:
        if product.photo_url.startswith('/uploads/'):
            local_path = os.path.join('uploads', product.photo_url.lstrip('/uploads/'))
            
            if os.path.exists(local_path):
                with open(local_path, 'rb') as f:
                    # Simular FileStorage
                    class FileObj:
                        filename = os.path.basename(local_path)
                        content_type = 'image/jpeg'
                        read = f.read
                    
                    file_obj = FileObj()
                    file_obj.filename = os.path.basename(local_path)
                    
                    photo_url = upload_file(file_obj, folder=f"products/{product.id}")
                    if photo_url:
                        product.photo_url = photo_url
                        print(f"✅ Migrado: {product.name} → {photo_url}")
                    else:
                        print(f"❌ Error migrando: {product.name}")
    
    db.session.commit()
    print("✅ Migración completada")
```

## 💰 ¿Cuánto Cuesta?

**GRATIS PARA SIEMPRE si usas menos de:**
- 5 GB de almacenamiento
- 5,000 escrituras/mes
- 50,000 lecturas/mes
- 100 GB de transferencia/mes

**Para una app pequeña/mediana con ~100 productos y ~500 imágenes:**
- Almacenamiento: ~500 MB (gratis)
- Operaciones: ~1,000/mes (gratis)
- **Total: $0 USD/mes**

**Si excedes los límites:**
- Almacenamiento: $0.020 USD por GB/mes adicional
- Operaciones: $0.05 USD por 1,000 operaciones adicionales
- Transferencia: $0.12 USD por GB adicional

**Ejemplo:** Si tienes 10 GB y 10,000 operaciones/mes:
- Almacenamiento: (10 - 5) × $0.020 = $0.10 USD
- Operaciones: (10,000 - 5,000) / 1,000 × $0.05 = $0.25 USD
- **Total: ~$0.35 USD/mes** (muy barato)

## 📝 Ventajas de Google Cloud Storage

- ✅ **Gratis para siempre** (dentro de los límites)
- ✅ **Velocidad**: Las imágenes se sirven desde CDN de Google (muy rápido)
- ✅ **Persistencia**: Las imágenes **nunca se borran** aunque hagas redeploy
- ✅ **Backup**: Google Cloud Storage tiene versionado y backup automático
- ✅ **Escalable**: Puede crecer con tu app sin problemas

## 🆓 Alternativa Gratis: Cloudinary

Si prefieres no usar Google Cloud, puedes usar Cloudinary (gratis hasta 25GB):

1. Crea cuenta en [Cloudinary](https://cloudinary.com/)
2. Obtén tus credenciales
3. Modifica `app/utils/cloud_storage.py` para usar Cloudinary en lugar de GCS

---

**¿Problemas?** Revisa los logs del backend para ver mensajes de error específicos.


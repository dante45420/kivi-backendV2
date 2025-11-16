# Scripts de Migración a Google Cloud

Este directorio contiene scripts útiles para migrar el proyecto a Google Cloud.

## 📋 Scripts Disponibles

### 1. `backup_database.sh`
Crea un backup de la base de datos desde Railway.

**Uso:**
```bash
export DATABASE_URL="postgresql://user:pass@host:port/dbname"
./scripts/backup_database.sh
```

El backup se guarda en `backups/kivi_backup_YYYYMMDD_HHMMSS.sql.gz`

---

### 2. `restore_database.sh`
Restaura un backup en Cloud SQL.

**Uso:**
```bash
./scripts/restore_database.sh \
    backups/kivi_backup_20250101_120000.sql.gz \
    kivi-project:us-central1:kivi-db
```

**Requisitos:**
- Cloud SQL Proxy corriendo, O
- Acceso directo a Cloud SQL con `gcloud sql connect`

---

### 3. `setup_cloud_sql.sh`
Configura una nueva instancia de Cloud SQL desde cero.

**Uso:**
```bash
./scripts/setup_cloud_sql.sh
```

Este script interactivo te guiará para:
- Crear instancia de Cloud SQL
- Crear base de datos `kivi_v2`
- Crear usuario `kivi_user`
- Configurar backups automáticos

---

### 4. `migrate_to_cloud_sql.sh`
Script completo que automatiza todo el proceso de migración.

**Uso:**
```bash
export RAILWAY_DATABASE_URL="postgresql://user:pass@host:port/dbname"
./scripts/migrate_to_cloud_sql.sh
```

Este script ejecuta:
1. Backup desde Railway
2. Configuración de Cloud SQL (si es necesario)
3. Restauración del backup

---

### 5. `verify_migration.sh`
Verifica que la migración fue exitosa.

**Uso:**
```bash
./scripts/verify_migration.sh
```

Verifica:
- ✅ Autenticación de gcloud
- ✅ Instancia de Cloud SQL
- ✅ Base de datos y usuario
- ✅ Bucket de Cloud Storage
- ✅ Servicios de Cloud Run
- ✅ Health checks

---

## 🔧 Requisitos Previos

1. **Google Cloud SDK instalado:**
   ```bash
   brew install google-cloud-sdk  # macOS
   ```

2. **Autenticado en Google Cloud:**
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

3. **Proyecto configurado:**
   ```bash
   gcloud config set project kivi-software
   ```

4. **APIs habilitadas:**
   ```bash
   gcloud services enable \
       cloudbuild.googleapis.com \
       run.googleapis.com \
       sql-component.googleapis.com \
       sqladmin.googleapis.com \
       storage-component.googleapis.com
   ```

---

## 📝 Orden Recomendado de Ejecución

1. **Preparación:**
   ```bash
   # Verificar requisitos
   ./scripts/verify_migration.sh
   ```

2. **Backup:**
   ```bash
   export DATABASE_URL="postgresql://..."
   ./scripts/backup_database.sh
   ```

3. **Configurar Cloud SQL:**
   ```bash
   ./scripts/setup_cloud_sql.sh
   ```

4. **Restaurar:**
   ```bash
   LATEST_BACKUP=$(ls -t backups/*.sql.gz | head -1)
   ./scripts/restore_database.sh "$LATEST_BACKUP" "project:region:instance"
   ```

5. **Verificar:**
   ```bash
   ./scripts/verify_migration.sh
   ```

---

## 🆘 Solución de Problemas

### Error: "pg_dump: command not found"
**Solución:** Instala PostgreSQL client:
```bash
brew install postgresql  # macOS
```

### Error: "Permission denied"
**Solución:** Dar permisos de ejecución:
```bash
chmod +x scripts/*.sh
```

### Error: "Cloud SQL connection failed"
**Solución:** 
1. Verifica que Cloud SQL Proxy esté corriendo
2. O usa `gcloud sql connect` para conexión directa

### Error: "Backup file not found"
**Solución:** Verifica que el backup se creó:
```bash
ls -lh backups/
```

---

## 📚 Documentación Relacionada

- [Guía Completa de Migración](../../MIGRACION_GOOGLE_CLOUD.md)
- [Inicio Rápido](../../INICIO_RAPIDO_MIGRACION.md)

---

**¡Buena suerte con la migración! 🚀**


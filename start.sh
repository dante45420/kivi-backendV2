#!/bin/bash
# Script de inicio para Railway
# Railway proporciona PORT automáticamente

# Obtener PORT de las variables de entorno, usar 8080 como fallback
PORT="${PORT:-8080}"

# Validar que PORT sea un número
if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
    echo "❌ ERROR: PORT debe ser un número, recibido: '$PORT'"
    exit 1
fi

echo "🚀 Iniciando Kivi Backend en puerto $PORT"

# Verificar que wsgi.py existe
if [ ! -f "wsgi.py" ]; then
    echo "❌ ERROR: wsgi.py no encontrado"
    exit 1
fi

# Iniciar gunicorn
exec gunicorn --bind "0.0.0.0:${PORT}" --workers 2 --threads 4 --timeout 0 wsgi:app


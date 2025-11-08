#!/bin/bash
# Script de inicio para Railway
# Railway proporciona PORT automáticamente

PORT=${PORT:-8080}

echo "🚀 Iniciando Kivi Backend en puerto $PORT"

exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 0 app:app


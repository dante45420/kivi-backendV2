#!/bin/bash
# Script de inicio para Railway
# Railway proporciona PORT automáticamente

PORT=${PORT:-8080}

echo "🚀 Iniciando Kivi Backend en puerto $PORT"
echo "📁 Directorio actual: $(pwd)"
echo "📄 Archivos en directorio:"
ls -la | head -10

# Verificar que wsgi.py existe
if [ ! -f "wsgi.py" ]; then
    echo "❌ ERROR: wsgi.py no encontrado en $(pwd)"
    exit 1
fi

# Verificar que el módulo wsgi puede importarse
python3 -c "import wsgi; print('✅ Módulo wsgi importado correctamente'); print('✅ Variable app existe:', hasattr(wsgi, 'app'))" || {
    echo "❌ ERROR: No se puede importar el módulo wsgi"
    exit 1
}

echo "✅ Iniciando gunicorn..."
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 0 wsgi:app


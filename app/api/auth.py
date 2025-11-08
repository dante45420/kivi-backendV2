"""
API: Autenticación
Login simple con email y contraseña desde .env
"""
from flask import Blueprint, request, jsonify, current_app
import jwt
import datetime

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["POST"])
def login():
    """Login de admin usando credenciales del .env"""
    data = request.json
    email = data.get("email", "")
    password = data.get("password", "")
    
    # Obtener credenciales desde config (que lee del .env)
    admin_email = current_app.config.get("ADMIN_EMAIL")
    admin_password = current_app.config.get("ADMIN_PASSWORD")
    
    # Debug
    print(f"🔍 Login attempt:")
    print(f"  Received email: '{email}' (len: {len(email)})")
    print(f"  Expected email: '{admin_email}' (len: {len(admin_email)})")
    print(f"  Email match: {email == admin_email}")
    print(f"  Received password: '{password}' (len: {len(password)})")
    print(f"  Expected password: '{admin_password}' (len: {len(admin_password)})")
    print(f"  Password match: {password == admin_password}")
    
    if email == admin_email and password == admin_password:
        # Generar token JWT
        token = jwt.encode(
            {
                "email": email,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
            },
            current_app.config.get("SECRET_KEY"),
            algorithm="HS256"
        )
        
        return jsonify({
            "token": token,
            "user": {
                "email": email,
                "name": "Admin"
            }
        })
    
    return jsonify({"error": "Email o contraseña incorrectos"}), 401


@bp.route("/verify", methods=["GET"])
def verify():
    """Verifica si el token es válido"""
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header.startswith("Bearer "):
        return jsonify({"valid": False}), 401
    
    token = auth_header.split(" ")[1]
    
    try:
        payload = jwt.decode(
            token, 
            current_app.config.get("SECRET_KEY"), 
            algorithms=["HS256"]
        )
        return jsonify({
            "valid": True,
            "user": {
                "email": payload["email"]
            }
        })
    except:
        return jsonify({"valid": False}), 401


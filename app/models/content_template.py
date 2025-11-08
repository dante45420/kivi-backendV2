"""
Modelo: Plantilla de contenido
Templates para generación de contenido IG/reel con IA
"""
from datetime import datetime
from ..db import db


class ContentTemplate(db.Model):
    __tablename__ = "content_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    
    # Tipo: story_video | reel | post
    type = db.Column(db.String(20), nullable=False)
    
    # Estructura JSON con configuración
    structure = db.Column(db.JSON, nullable=False)
    
    # Prompt para IA
    ai_prompt = db.Column(db.Text, nullable=True)
    
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "structure": self.structure,
            "ai_prompt": self.ai_prompt,
            "active": self.active,
        }


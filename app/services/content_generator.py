"""
Servicio: Generador de contenido IA
Crea videos, stories y posts para redes sociales
"""
import os
from openai import OpenAI
from ..models import Product, ContentTemplate


def generate_content(template_type, product_ids, custom_prompt=None):
    """
    Genera contenido basado en plantilla
    
    Args:
        template_type: Tipo de contenido (story_video, reel, post)
        product_ids: Lista de IDs de productos
        custom_prompt: Prompt personalizado (opcional)
    
    Returns:
        dict con contenido generado
    """
    
    # Obtener productos
    products = Product.query.filter(Product.id.in_(product_ids)).all()
    
    if not products:
        raise ValueError("No se encontraron productos")
    
    # Obtener plantilla
    template = ContentTemplate.query.filter_by(
        type=template_type,
        active=True
    ).first()
    
    if not template:
        # Usar plantilla por defecto
        template_structure = get_default_template(template_type)
    else:
        template_structure = template.structure
    
    # Generar texto con IA
    text = generate_text_with_ai(products, template, custom_prompt)
    
    # Generar video/imagen (placeholder por ahora)
    media_url = generate_media(products, template_structure, text)
    
    return {
        "type": template_type,
        "text": text,
        "media_url": media_url,
        "products": [p.to_dict() for p in products],
        "status": "pending_approval"
    }


def generate_text_with_ai(products, template, custom_prompt=None):
    """Genera texto usando OpenAI"""
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        return "¡Oferta especial en Kivi! 🐕"
    
    try:
        client = OpenAI(api_key=api_key)
        
        products_list = ", ".join([p.name for p in products])
        
        base_prompt = f"""
        Crea un texto atractivo para redes sociales promocionando estos productos de Lo Valledor:
        {products_list}
        
        Requisitos:
        - Máximo 150 caracteres
        - Tono casual y amigable
        - Incluye llamado a la acción
        - Menciona que es de Kivi Personal Shopper
        """
        
        if custom_prompt:
            base_prompt += f"\n\nInstrucciones adicionales: {custom_prompt}"
        
        if template and template.ai_prompt:
            base_prompt = template.ai_prompt.format(
                products=products_list
            )
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Eres un copywriter experto en redes sociales."},
                {"role": "user", "content": base_prompt}
            ],
            max_tokens=100,
            temperature=0.9
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"❌ Error generando texto: {e}")
        return f"¡Oferta especial! {', '.join([p.name for p in products])} 🐕"


def generate_media(products, template_structure, text):
    """
    Genera video o imagen
    (Por ahora retorna placeholder, implementar con FFmpeg después)
    """
    
    # TODO: Implementar generación real con FFmpeg
    # - Tomar fotos de productos
    # - Crear video según estructura del template
    # - Agregar texto overlay
    # - Agregar música
    # - Subir a Cloud Storage
    
    return "https://placeholder.com/generated-content.mp4"


def regenerate_content(content_id, feedback):
    """
    Regenera contenido basado en feedback
    
    Args:
        content_id: ID del contenido a regenerar
        feedback: Feedback del usuario
    
    Returns:
        dict con nuevo contenido
    """
    
    # TODO: Implementar lógica de regeneración
    # - Obtener contenido original
    # - Aplicar feedback al prompt
    # - Generar de nuevo
    
    return {
        "type": "story_video",
        "text": "Contenido regenerado (placeholder)",
        "media_url": "https://placeholder.com/regenerated.mp4",
        "status": "pending_approval"
    }


def get_default_template(template_type):
    """Retorna plantilla por defecto"""
    
    templates = {
        "story_video": {
            "duration": 15,
            "scenes": [
                {"type": "intro", "duration": 3},
                {"type": "product", "duration": 10},
                {"type": "outro", "duration": 2}
            ]
        },
        "reel": {
            "duration": 30,
            "scenes": [
                {"type": "intro", "duration": 5},
                {"type": "product", "duration": 20},
                {"type": "outro", "duration": 5}
            ]
        },
        "post": {
            "type": "image",
            "layout": "grid"
        }
    }
    
    return templates.get(template_type, templates["post"])


"""
Servicio: Chat con Green Market
Utiliza OpenAI para conversar con el usuario
"""
import os
from openai import OpenAI


def chat_with_kivi(user_message, context=None):
    """
    Chat con Green Market usando OpenAI GPT-4
    
    Args:
        user_message: Mensaje del usuario
        context: Contexto adicional (opcional)
    
    Returns:
        str: Respuesta de Green Market
    """
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        return "¡Hola! Parece que no puedo conectarme ahora. Intenta más tarde 🌱"
    
    try:
        client = OpenAI(api_key=api_key)
        
        system_prompt = """
        Eres Green Market, un personal shopper amigable que trabaja en Lo Valledor, Santiago de Chile.
        
        Tu personalidad:
        - Eres amigable, entusiasta y siempre quieres ayudar
        - Hablas de forma cercana y casual
        - Usas emojis ocasionalmente (especialmente 🌱)
        - Tienes conocimiento profundo sobre frutas y verduras
        - Conoces bien la plataforma Green Market y cómo funciona
        
        Lo que haces:
        - Ayudas a clientes con información sobre productos
        - Explicas cómo usar la plataforma
        - Das tips sobre conservación de frutas/verduras
        - Compartes datos curiosos
        - Promocionas las ofertas semanales cuando es relevante
        
        Lo que NO haces:
        - No inventas información
        - No prometes cosas que el sistema no puede hacer
        - No das consejos médicos
        
        Recuerda: Eres parte de un servicio de personal shopper, no un supermercado.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        if context:
            messages.insert(1, {"role": "system", "content": f"Contexto: {context}"})
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=200,
            temperature=0.8
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"❌ Error en chat con Green Market: {e}")
        return "¡Hola! Tuve un problema técnico. ¿Puedes intentar de nuevo? 🌱"


from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = FastAPI()

# Configuración
API_KEY = os.getenv("API_KEY")
ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
WHATSAPP_URL = "https://w.app/ogzaqz"  # Personaliza tu enlace corto

# Prompt del sistema
SYSTEM_PROMPT = f"""
Eres un asistente virtual especializado en Pijamas Shalom. Tu función es proporcionar información precisa sobre nuestros productos y servicios de manera amable y profesional. 

📌 **Ámbito de respuestas**: Solo atenderás consultas sobre:
- Productos de pijamas (características, tallas)
- Precios y promociones
- Políticas de envíos y devoluciones
- Información de contacto

📋 **Datos clave**:
1. **Productos**:
   - Tipos: Pijamas para Hombre/Mujer/Niños
   - Material: 100% algodón premium
   - Tallas: S, M, L, XL (consultar disponibilidad)
   
2. **Precios**:
   - Desde $50,000 COP (precio base)
   - Descuentos progresivos (3+ unidades)
   
3. **Envíos**:
   - Cúcuta: $5,000 (24 horas)
   - Nacional: $15,000 (2-3 días hábiles)
   
4. **Contacto**:
   - WhatsApp: {WHATSAPP_URL}
   - Horario: L-V 8am-6pm

🚫 **Para consultas fuera de tema**: 
Responde cordialmente redirigiendo al tema principal:
"Actualmente solo puedo ayudarte con información sobre nuestros pijamas. ¿Te gustaría saber sobre [sugerencia relacionada]?"
Ejemplo: "...¿Te gustaría saber sobre nuestras tallas disponibles?"

💡 **Estilo de comunicación**:
- Usa emojis relevantes (máximo 2 por respuesta)
- Sé conciso (máximo 2 párrafos)
- Ofrece ayuda adicional al final
- Usa negritas para datos importantes
"""
@app.post("/manychat-webhook")
async def handle_manychat(request: Request):
    try:
        data = await request.json()
        user_message = data.get("message", "").strip()

        if not user_message:
            return {
                "messages": [{
                    "type": "text",
                    "text": "🔍 Por favor envía un mensaje válido."
                }]
            }

        # Llamar a DeepSeek
        response = requests.post(
            ENDPOINT,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.3,
                "max_tokens": 300
            },
            timeout=10
        )

        response.raise_for_status()
        ai_response = response.json()["choices"][0]["message"]["content"]

        # RESPUESTA SIN JSONResponse → compatible con ManyChat
        return {
            "messages": [
                {
                    "type": "text",
                    "text": ai_response[:1500]
                }
            ]
        }

    except requests.exceptions.Timeout:
        return {
            "messages": [{
                "type": "text",
                "text": "⏳ El servicio está ocupado. Intenta más tarde o contáctanos por WhatsApp."
            }]
        }

    except requests.exceptions.RequestException:
        return {
            "messages": [{
                "type": "text",
                "text": "🔴 No pudimos procesar tu solicitud. Escríbenos por WhatsApp."
            }]
        }

    except Exception:
        return {
            "messages": [{
                "type": "text",
                "text": "⚠️ Ocurrió un error inesperado. Puedes escribirnos por WhatsApp."
            }]
        }


# Health Check para Render
@app.get("/")
async def health_check():
    return {"status": "active", "service": "Pijamas Shalom Bot"}

# Keep-Alive endpoint
@app.get("/keep-alive")
async def keep_alive():
    return {"status": "keep-alive triggered"}

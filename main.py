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
Eres el asistente de Pijamas Shalom. Responde SOLO sobre:

1. **Productos**:
   - Pijamas para Hombre, Mujer y Niños
   - Material: 100% algodón
   - Tallas disponibles: S, M, L, XL

2. **Precios y Promociones**:
   - Desde $50,000 COP
   - Descuentos por compras mayores a 3 unidades

3. **Envíos**:
   - Cúcuta: $5,000 COP (Entrega en 24h)
   - Resto del país: $15,000 COP (Entrega en 2-3 días)

4. **Políticas y Contacto**:
   - Cambios: hasta 3 días hábiles después de la entrega
   - Contacto por WhatsApp: {WHATSAPP_URL}
   - Atención al cliente: Lunes a Viernes, 8:00am - 6:00pm

Si la pregunta no está relacionada, responde:
"¿En qué más puedo ayudarte sobre nuestros pijamas? 😊"
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

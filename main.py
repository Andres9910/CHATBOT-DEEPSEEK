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
WHATSAPP_URL = "https://w.app/ogzaqz"  # Enlace corto personalizado

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
            return JSONResponse(
                content={"messages": [{"type": "text", "text": "🔍 Por favor envía un mensaje válido."}]},
                status_code=400
            )

        # Llamada a DeepSeek
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

        # Estructura compatible con ManyChat
        return {
            "messages": [
                {
                    "type": "text",
                    "text": ai_response[:1500]  # Truncar si es necesario
                },
                {
                    "type": "button",
                    "buttons": [
                        {
                            "type": "url",
                            "caption": "💬 Hablar con asesor",
                            "url": WHATSAPP_URL
                        }
                    ]
                }
            ]
        }

    except requests.exceptions.Timeout:
        return {
            "messages": [{
                "type": "text",
                "text": "⏳ El servicio está ocupado. Por favor intenta más tarde o escríbenos a WhatsApp."
            }]
        }
    except requests.exceptions.RequestException:
        return {
            "messages": [{
                "type": "text",
                "text": "🔴 No pudimos procesar tu solicitud. Contacta a soporte vía WhatsApp."
            }]
        }
    except Exception:
        return {
            "messages": [{
                "type": "text",
                "text": "⚠️ Ocurrió un error inesperado. Puedes escribirnos directamente por WhatsApp."
            }]
        }

# Health check para Render
@app.get("/")
async def health_check():
    return {"status": "active", "service": "Pijamas Shalom Bot"}

# Endpoint keep-alive
@app.get("/keep-alive")
async def keep_alive():
    return {"status": "keep-alive triggered"}

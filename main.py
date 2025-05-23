from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = FastAPI()

# Configuración de archivos estáticos y plantillas
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Configuración
API_KEY = os.getenv("API_KEY")
ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
WHATSAPP_URL = "https://w.app/ogzaqz"  # Personaliza tu enlace corto

# Prompt del sistema
SYSTEM_PROMPT = f"""
Eres el asistente virtual de **Pijamas Shalom**, una tienda especializada en pijamas para toda la familia. Tu función es responder cualquier tipo de pregunta relacionada con nuestros productos, servicios o políticas. Aquí tienes la información principal para ayudarte:

🛏️ **Productos**:
- Pijamas para Hombre, Mujer y Niños
- Material: 100% algodón
- Tallas disponibles: S, M, L, XL

💰 **Precios y Promociones**:
- Precios desde $50,000 COP
- Descuentos especiales por compras mayores a 3 unidades

🚚 **Envíos**:
- Envío en Cúcuta: $5,000 COP (entrega en 24 horas)
- Envío al resto del país: $15,000 COP (entrega en 2-3 días)

🔄 **Cambios y Devoluciones**:
- Cambios permitidos hasta 3 días hábiles después de la entrega

📞 **Atención y Contacto**:
- Horario: Lunes a Viernes, 8:00am - 6:00pm
- WhatsApp: {WHATSAPP_URL}

Puedes responder preguntas sobre tallas, precios, materiales, envíos, promociones, disponibilidad, políticas o cualquier otro tema relacionado con Pijamas Shalom.

Si alguien pregunta sobre algo que no tenga que ver con Pijamas Shalom, responde amablemente:
"¿En qué más puedo ayudarte sobre nuestros pijamas? 😊"
"""

# Ruta principal para la interfaz web
@app.get("/", response_class=HTMLResponse)
async def chat_interface(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request, "whatsapp_url": WHATSAPP_URL})

# Endpoint para el chatbot (reemplaza ManyChat)
@app.post("/api/chat")
async def handle_chat(request: Request):
    try:
        data = await request.json()
        user_message = data.get("message", "").strip()

        if not user_message:
            return JSONResponse(
                content={"response": "🔍 Por favor envía un mensaje válido."},
                status_code=400
            )

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

        return JSONResponse(
            content={"response": ai_response[:1500]},
            status_code=200
        )

    except requests.exceptions.Timeout:
        return JSONResponse(
            content={"response": "⏳ El servicio está ocupado. Intenta más tarde o contáctanos por WhatsApp."},
            status_code=408
        )

    except requests.exceptions.RequestException:
        return JSONResponse(
            content={"response": "🔴 No pudimos procesar tu solicitud. Escríbenos por WhatsApp."},
            status_code=500
        )

    except Exception:
        return JSONResponse(
            content={"response": "⚠️ Ocurrió un error inesperado. Puedes escribirnos por WhatsApp."},
            status_code=500
        )

# Health Check para Render
@app.get("/health")
async def health_check():
    return {"status": "active", "service": "Pijamas Shalom Bot"}

# Keep-Alive endpoint
@app.get("/keep-alive")
async def keep_alive():
    return {"status": "keep-alive triggered"}
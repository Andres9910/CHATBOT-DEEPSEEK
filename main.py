from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests
import os
import logging
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

# Configuración básica
load_dotenv()
app = FastAPI()
logging.basicConfig(level=logging.INFO)

# Configuración de archivos estáticos y plantillas
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Configuración
API_KEY = os.getenv("API_KEY")
ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
WHATSAPP_URL = "https://w.app/ogzaqz"

# Prompt del sistema mejorado
SYSTEM_PROMPT = f"""
**Instrucciones críticas**:
1. DEBES responder TODAS las preguntas sobre pijamas usando EXCLUSIVAMENTE la información proporcionada
2. NUNCA digas "no sé" o "no puedo responder". Si falta información, ofrece contactar por WhatsApp
3. Usa este formato para respuestas:
   - 📌 [Resumen breve]
   - 🔍 [Detalles]
   - 📞 [Cierre con enlace a WhatsApp]

### Información completa de Pijamas Shalom:

#### 🧵 **Líneas de Producto**:
1. **Pijamas para Mujer**:
   - Modelos: Clásico (${50,000} COP), Estampado (${55,000} COP), Seda (${80,000} COP)
   - Tallas: XS, S, M, L, XL (guía de tallas disponible)
   - Material: 95% algodón + 5% elastano

2. **Pijamas para Hombre**:
   - Modelos: Bóxer/camiseta (${45,000} COP), Conjunto deportivo (${65,000} COP)
   - Tallas: S a XXL (tallas americanas)

3. **Pijamas para Niños**:
   - Modelos: Infantil (${35,000}-${50,000} COP), Adolescentes (${40,000}-${60,000} COP)
   - Tallas: 2-4, 6-8, 10-12, 14-16

#### 🚚 **Envíos y Entregas**:
- Cúcuta: 24 horas (${5,000} COP)
- Otras ciudades: 2-3 días (${15,000} COP)
- Express: +${10,000} COP (12-18 horas)

#### 💳 **Métodos de Pago**:
1. Transferencia bancaria
2. Nequi/Daviplata
3. Efectivo en tienda física

**Ejemplo de respuesta perfecta**:
Usuario: "¿Qué pijamas tienen para niña de 8 años?"
Asistente: "📌 Tenemos 3 modelos para niñas de 8 años (talla 10-12):
- Infantil clásica: ${35,000} COP
- Infantil estampada: ${40,000} COP 
- Pack familiar (2 pijamas): ${60,000} COP
🔍 Material: 100% algodón hipoalergénico. ¿Quieres que te enviemos fotos por WhatsApp? 📲 {WHATSAPP_URL}"
"""

# Función con reintentos para la API
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def call_deepseek(payload: dict):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post(ENDPOINT, headers=headers, json=payload, timeout=20)
    response.raise_for_status()
    return response.json()

# Ruta principal
@app.get("/", response_class=HTMLResponse)
async def chat_interface(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request, "whatsapp_url": WHATSAPP_URL})

# Endpoint mejorado del chatbot
@app.post("/api/chat")
async def handle_chat(request: Request):
    try:
        data = await request.json()
        user_message = data.get("message", "").strip()
        
        if not user_message:
            return JSONResponse(
                content={"response": "🔍 Por favor envía un mensaje válido"},
                status_code=400
            )

        logging.info(f"Pregunta recibida: {user_message}")
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }

        api_response = call_deepseek(payload)
        
        if 'choices' not in api_response:
            raise ValueError("Estructura de respuesta inesperada")
        
        ai_response = api_response["choices"][0]["message"]["content"]
        logging.info(f"Respuesta generada: {ai_response[:100]}...")
        
        return JSONResponse(
            content={"response": ai_response[:1500]},
            status_code=200
        )

    except requests.exceptions.Timeout:
        logging.error("Timeout al conectar con la API")
        return JSONResponse(
            content={"response": f"⏳ Nuestro servidor está ocupado. Para atención inmediata contáctanos por WhatsApp: {WHATSAPP_URL}"},
            status_code=200
        )
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error en la API: {str(e)}")
        return JSONResponse(
            content={"response": f"🔍 Estamos mejorando nuestro servicio. Escríbenos directamente por WhatsApp: {WHATSAPP_URL}"},
            status_code=200
        )
        
    except Exception as e:
        logging.error(f"Error inesperado: {str(e)}")
        return JSONResponse(
            content={"response": f"📢 Por favor contáctanos por WhatsApp para resolver tu consulta al instante: {WHATSAPP_URL}"},
            status_code=200
        )

# Endpoints de monitoreo
@app.get("/health")
async def health_check():
    return {"status": "active", "service": "Pijamas Shalom Bot"}

@app.get("/keep-alive")
async def keep_alive():
    return {"status": "keep-alive triggered"}
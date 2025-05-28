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
Eres el asistente virtual oficial de **Pijamas Shalom** (ubicada en Calle 4N #7E-30, Barrio Los Pinos). 
Responde **de manera detallada y estructurada** sobre nuestros productos, políticas y servicios. 

### 🧺 **Catálogo Completo** (Precios en COP):

#### 👩 **MUJERES**:
- Conjunto Short + Blusa manga normal/sisa: $30,000
- Conjunto Blusa + Pantalón largo: $45,000
- Conjunto Blusa + Pantalón capri: $45,000
- Batas: $30,000

#### 👨 **HOMBRES**:
- Conjunto Franela + Bermuda: $30,000
- Conjunto Franela + Pantalón largo: $45,000

#### 👶 **NIÑOS/NIÑAS**:
- Conjunto Franela/Blusa + Bermuda/Short: $25,000
- Conjunto Franela/Blusa + Pantalón largo: $35,000
- Batas (niña): $25,000

### 📏 **Guía de Tallas**:
- **Hombres**: S, M, L, XL (XXL/XXXL bajo pedido)
- **Mujeres**: XS, S, M, L, XL (XXL/XXXL bajo pedido)
- **Niños**: 4, 6, 8, 10, 12, 14, 16

### 🧶 **Tipos de Tela** (Premium):
1. Franela Doble Punto (suave y abrigada)
2. Tela Galleta (transpirable)
3. Tela Piel de Durazno (ultrasuave)

### 🚛 **Envíos y Pagos**:
- **Costo**: Desde $8,000 (varía por distancia)
- **Métodos de pago**:
  - Transferencia: Nequi/Daviplata #3016570792
  - Efectivo (solo en tienda o contraentrega)
- **Horario de atención**: Lunes a Viernes (8:00 AM - 6:00 PM)

### 🔄 **Políticas**:
- Cambios: 3 días hábiles post-entrega
- Pedidos especiales: Solicítalos por WhatsApp

### 📞 **Contacto Directo**:
- Propietaria: **Yacqueline Pérez Antolinez**
- WhatsApp: [Contactar aquí]({WHATSAPP_URL}) (3004413069)
- Ubicación: Calle 4N #7E-30, Barrio Los Pinos

### ✨ **Instrucciones Clave**:
1. **Formato de respuestas**:
   - 📌 **Resumen**: 1 línea clara
   - 🔍 **Detalles**: Lista con viñetas
   - 📞 **Cierre**: Invitación a contacto
   
   Ejemplo: 
   *"📌 Tenemos 3 modelos para niños desde $25,000.  
   🔍 - Conjuntos franela+short: $25,000  
       - Pantalón largo: $35,000  
   📞 ¿Te gustaría ver fotos? [WhatsApp]({WHATSAPP_URL})"*

2. **Si no sabes algo**:  
   *"Te conecto con Yacqueline por WhatsApp para resolverlo al instante: [3004413069]({WHATSAPP_URL})"*

3. **Fuera de tema**:  
   *"Somos expertos en pijamas familiares. ¿Quieres saber sobre algún modelo en particular? 😊"*
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
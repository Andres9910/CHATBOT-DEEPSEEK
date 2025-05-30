from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests
import os
import logging
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from datetime import datetime
import json

# Configuración básica
load_dotenv()
app = FastAPI(title="Pijamas Shalom Chatbot API")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pijamas-shalom")

# Configuración de archivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Configuración de la API
API_KEY = os.getenv("DEEPSEEK_API_KEY")
ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
WHATSAPP_URL = "https://wa.me/573004413069"
STORE_LOCATION = "Calle 4N #7E-30, Barrio Los Pinos, Cúcuta"

# Modelo de datos para productos
PRODUCTS_DB = {
    "mujer": [
        {"id": 1, "name": "Conjunto Short + Blusa", "price": 30000, "materials": ["algodón"]},
        {"id": 2, "name": "Conjunto Pantalón Largo", "price": 45000, "materials": ["algodón"]},
        {"id": 3, "name": "Bata", "price": 30000, "materials": ["algodón", "seda"]}
    ],
    "hombre": [
        {"id": 4, "name": "Conjunto Franela + Bermuda", "price": 30000, "materials": ["algodón"]},
        {"id": 5, "name": "Conjunto Pantalón Largo", "price": 45000, "materials": ["algodón"]}
    ],
    "niños": [
        {"id": 6, "name": "Conjunto Short", "price": 25000, "materials": ["algodón"]},
        {"id": 7, "name": "Conjunto Pantalón Largo", "price": 35000, "materials": ["algodón"]}
    ]
}

# Prompt mejorado con estructura de plantilla
SYSTEM_PROMPT = f"""
Eres Perla, la asistente virtual femenina de **Pijamas Shalom** ({STORE_LOCATION}). 
Responde de manera clara, amable y profesional siguiendo esta estructura:

### 🌟 **Información Esencial**:
- **Propietaria**: Yacqueline Pérez Antolinez
- **Contacto**: [WhatsApp]({WHATSAPP_URL}) (3004413069)
- **Horario**: Lunes a Viernes (8:00 AM - 6:00 PM)
- **Ubicación**: {STORE_LOCATION}
- **Métodos de pago**: 
  - Transferencias: Nequi/Daviplata #3016570792
  - Efectivo (solo en tienda)

### 🧺 **Catálogo de Productos** (Precios en COP):

#### 👩 **MUJERES**:
- Conjunto Short + Blusa manga normal/sisa: **$30,000**
- Conjunto Blusa + Pantalón largo: **$45,000**
- Conjunto Blusa + Pantalón capri: **$45,000**
- Batas: **$30,000**

#### 👨 **HOMBRES**:
- Conjunto Franela + Bermuda: **$30,000**
- Conjunto Franela + Pantalón largo: **$45,000**

#### 👶 **NIÑOS/NIÑAS**:
- Conjunto Franela/Blusa + Bermuda/Short: **$25,000**
- Conjunto Franela/Blusa + Pantalón largo: **$35,000**
- Batas (niña): **$25,000**

### 📏 **Guía de Tallas Exactas**:
- **Hombres**: S, M, L, XL (XXL/XXXL bajo pedido)
- **Mujeres**: XS, S, M, L, XL (XXL/XXXL bajo pedido)
- **Niños**: 4, 6, 8, 10, 12, 14, 16

### 🧶 **Tipos de Tela Disponibles**:
1. Franela Doble Punto (suave y abrigada)
2. Tela Galleta (transpirable)
3. Tela Piel de Durazno (ultrasuave)

### 🚛 **Política de Envíos**:
- **Costo mínimo**: Desde **$8,000** (varía según distancia)
- **Cobertura**: Principalmente en Cúcuta
- **Tiempos**: Consultar según ubicación

### 📌 **Instrucciones Clave para Respuestas**:
1. **Formato obligatorio**:
   - Precio: **$XX,XXX COP** (en negrita)
   - Tallas exactas (sin rangos)
   - Enlace claro a WhatsApp

2. **Estructura de respuesta**:
📌 [Producto]: [Precio]
🔹 Tallas: [Lista exacta]
🔹 Material: [Tipo de tela]
<a href='{WHATSAPP_URL}' target='_blank' style='display:inline-block;background:#25d366;color:#fff;padding:8px 16px;border-radius:6px;text-decoration:none;font-weight:bold;margin-top:8px;'><i class='fab fa-whatsapp'></i> Pedir por WhatsApp</a>

3. **Para preguntas fuera de tema**:
"Como asistente especializada en pijamas, solo puedo ayudarte con información sobre nuestros productos. ¿Quieres saber sobre [sugerir tema relacionado]?"

4. **Sobre promociones**:
"Actualmente no tenemos promociones disponibles, pero ofrecemos precios competitivos en todos nuestros productos."

5. **Recomendaciones adicionales**:
- Usar emojis relevantes (máximo 3 por respuesta)
- Ser concisa (1-2 párrafos máximo)
- Ofrecer ayuda adicional al final
- Usar negritas para datos importantes
- Incluir siempre el botón de WhatsApp

### ✨ **Ejemplo de Respuesta Perfecta**:
"📌 Conjunto de pijama para niña (Short + Blusa): **$25,000 COP**  
🔹 Tallas disponibles: 4, 6, 8, 10, 12, 14, 16  
🔹 Material: Franela Doble Punto (suave y abrigada)  
<a href='{WHATSAPP_URL}' target='_blank' style='display:inline-block;background:#25d366;color:#fff;padding:8px 16px;border-radius:6px;text-decoration:none;font-weight:bold;margin-top:8px;'><i class='fab fa-whatsapp'></i> Pedir este modelo</a>"
"""

# Función mejorada con reintentos y logging
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def call_ai_api(messages: list):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500,
        "top_p": 0.9
    }
    
    logger.info(f"Enviando a API: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(ENDPOINT, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error en API: {str(e)}")
        raise

# Middleware para logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    process_time = (datetime.now() - start_time).total_seconds()
    
    logger.info(
        f"Request: {request.method} {request.url} - Status: {response.status_code} - Time: {process_time:.2f}s"
    )
    
    return response

# Endpoints
@app.get("/", response_class=HTMLResponse)
async def chat_interface(request: Request):
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "whatsapp_url": WHATSAPP_URL,
        "store_location": STORE_LOCATION
    })

# Versión corregida del endpoint /api/chat
@app.post("/api/chat")
async def handle_chat(request: Request):
    try:
        # Verificar conexión con la API primero
        api_status = await check_api_connection()
        if not api_status:
            return JSONResponse(
                content={"response": "⚠️ Estamos mejorando nuestro servicio. Por favor escríbenos por WhatsApp para resolver tu consulta al instante."},
                status_code=200
            )

        data = await request.json()
        user_message = data.get("message", "").strip()
        
        if not user_message:
            return JSONResponse(
                content={"response": "🔍 Por favor envía un mensaje válido"},
                status_code=400
            )

        # Respuestas rápidas para preguntas frecuentes
        quick_responses = {
            "qué tallas tienen": "📏 Tenemos tallas para mujer (XS-XL), hombre (S-XL) y niños (4-16). ¿Para quién necesitas la talla?",
            "cuánto cuesta": "💰 Nuestros pijamas van desde $30,000 COP. ¿Te interesa para mujer, hombre o niños?",
            "hacen envíos": "🚚 ¡Sí! Envíos a Cúcuta $5,000 (24h) y nacional $15,000 (2-3 días). [WhatsApp](https://w.app/ogzaqz)"
        }

        # Buscar coincidencia en preguntas frecuentes
        lower_msg = user_message.lower()
        for question, answer in quick_responses.items():
            if question in lower_msg:
                return JSONResponse(content={"response": answer})

        # Si no es pregunta frecuente, llamar a la API
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.7,
            "max_tokens": 300
        }

        response = requests.post(
            ENDPOINT,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            ai_response = response.json()["choices"][0]["message"]["content"]
            return JSONResponse(content={"response": ai_response})
        else:
            # Respuesta alternativa si falla la API pero no la conexión
            alternative_responses = {
                "talla": "📏 ¿Necesitas ayuda con tallas? Mujer: XS-XL, Hombre: S-XL, Niños: 4-16. [WhatsApp](https://w.app/ogzaqz)",
                "precio": "💰 Pijamas desde $30,000 COP. ¿Para quién buscas?",
                "envío": "🚚 Envíos a todo Colombia. Cúcuta $5,000, otras ciudades $15,000 COP"
            }
            
            for keyword, resp in alternative_responses.items():
                if keyword in lower_msg:
                    return JSONResponse(content={"response": resp})
            
            return JSONResponse(
                content={"response": f"📢 Nuestro asistente está ocupado. Para respuesta inmediata escríbenos por [WhatsApp](https://w.app/ogzaqz)"},
                status_code=200
            )

    except Exception as e:
        logging.error(f"Error en chat: {str(e)}")
        return JSONResponse(
            content={"response": "¡Vaya! Algo salió mal. ¿Quieres consultar sobre precios, tallas o envíos?"},
            status_code=200
        )

async def check_api_connection():
    try:
        test_payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": "test"}],
            "max_tokens": 500
        }
        response = requests.post(
            ENDPOINT,
            headers={"Authorization": f"Bearer {API_KEY}"},
            json=test_payload,
            timeout=30
        )
        if response.status_code != 200:
            logger.error(f"Deepseek API error: {response.status_code} - {response.text}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Deepseek API exception: {str(e)}")
        return False

# Endpoint para obtener productos (puede usarse para mostrar catálogo)
@app.get("/api/products")
async def get_products(category: str = None):
    try:
        if category and category.lower() in PRODUCTS_DB:
            return {"products": PRODUCTS_DB[category.lower()]}
        return {"products": PRODUCTS_DB}
    except Exception as e:
        logger.error(f"Error al obtener productos: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener productos")

# Endpoints de monitoreo
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Pijamas Shalom Chatbot",
        "version": "1.2.0"
    }

@app.get("/metrics")
async def service_metrics():
    return {
        "uptime": "TODO",  # Implementar lógica real
        "requests_served": "TODO",
        "avg_response_time": "TODO"
    }
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
WHATSAPP_OWNER_URL = "https://wa.me/573004413069"
STORE_URL = "https://shalompijamas.shop/"
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
Eres Perla, la asistente virtual de **Pijamas Shalom**. Sigue estrictamente estas reglas:

### 🔀 **Flujo de Conversación**:
1. **Consultas generales** (precios, tallas, productos):
   - Responde directamente con información completa
   - Incluye botón a la tienda online

2. **Pedidos específicos** (quiero comprar X):
   - Proporciona detalles del producto
   - Muestra botón rosado a la tienda

3. **Problemas/complejidades**:
   - Solo entonces redirige al WhatsApp de la dueña

### 🛒 **Botones de Acción**:
- Tienda Online: 
  <a href='{STORE_URL}' target='_blank' style='display:inline-block;background:#FF69B4;color:#fff;padding:8px 16px;border-radius:6px;text-decoration:none;font-weight:bold;margin-top:8px;'><i class='fas fa-shopping-cart'></i> Ver en Tienda</a>

- WhatsApp Dueña (SOLO para problemas):
  <a href='{WHATSAPP_OWNER_URL}' target='_blank' style='display:inline-block;background:#25D366;color:#fff;padding:8px 16px;border-radius:6px;text-decoration:none;font-weight:bold;margin-top:8px;'><i class='fab fa-whatsapp'></i> Contactar a Yacqueline</a>

### 📌 **Ejemplos de Respuestas**:

1. Para consulta de producto:
"📌 Conjunto Mujer (Short + Blusa): $30,000 COP  
🔹 Tallas: XS, S, M, L, XL  
🔹 Material: Franela Doble Punto  
<a href='{STORE_URL}' style='background:#FF69B4;...'>Ver en Tienda</a>"

2. Para problemas:
"⚠️ Para resolver esto necesitaré conectarte con Yacqueline:  
<a href='{WHATSAPP_OWNER_URL}' style='background:#25D366;...'>WhatsApp Directo</a>"
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
        "whatsapp_url": WHATSAPP_OWNER_URL,
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
            "hacen envíos": "🚚 ¡Sí! Envíos a Cúcuta $5,000 (24h) y nacional $15,000 (2-3 días). [Tienda](https://shalompijamas.shop/)"
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
                "talla": "📏 ¿Necesitas ayuda con tallas? Mujer: XS-XL, Hombre: S-XL, Niños: 4-16. [Tienda](https://shalompijamas.shop/)",
                "precio": "💰 Pijamas desde $30,000 COP. ¿Para quién buscas?",
                "envío": "🚚 Envíos a todo Colombia. Cúcuta $5,000, otras ciudades $15,000 COP"
            }
            
            for keyword, resp in alternative_responses.items():
                if keyword in lower_msg:
                    return JSONResponse(content={"response": resp})
            
            return JSONResponse(
                content={"response": f"📢 Nuestro asistente está ocupado. Para respuesta inmediata escríbenos por [WhatsApp](https://wa.me/573004413069)."},
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
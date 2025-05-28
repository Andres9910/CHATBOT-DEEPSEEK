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
Eres el asistente virtual de **Pijamas Shalom** ({STORE_LOCATION}). 
Responde de manera clara, amable y profesional siguiendo esta estructura:

### 🌟 **Información Clave**:
- **Propietaria**: Yacqueline Pérez Antolinez
- **WhatsApp**: [Contactar]({WHATSAPP_URL}) (3004413069)
- **Horario**: Lunes a Viernes (8:00 AM - 6:00 PM)

### 📦 **Productos Disponibles**:
{json.dumps(PRODUCTS_DB, indent=2, ensure_ascii=False)}

### 📏 **Guía de Tallas**:
- **Mujeres**: XS (0-2), S (4-6), M (8-10), L (12-14), XL (16-18)
- **Hombres**: S (34-36), M (38-40), L (42-44), XL (46-48)
- **Niños**: 4 (3-4 años), 6 (5-6), 8 (7-8), 10 (9-10), 12 (11-12), 14 (13-14)

### 🚚 **Envíos**:
- **Cúcuta**: $5,000 (24 horas)
- **Otras ciudades**: $15,000 (2-3 días)
- **Pedidos especiales**: Consultar disponibilidad

### 💰 **Promociones**:
- 10% de descuento en compras mayores a $100,000
- 2da unidad a mitad de precio (promoción válida hasta {datetime.now().strftime('%d/%m/%Y')})

### 📌 **Instrucciones de Respuesta**:
1. **Siempre** incluye:
   - Precio con formato: **$XX,XXX COP**
   - Tallas disponibles
   - Enlace a WhatsApp para consultas

2. **Ejemplo de respuesta**:
   "📌 Conjunto de pijama para mujer: **$45,000 COP**  
   🔹 Tallas: XS a XL  
   🔹 Material: 100% algodón  
   📞 ¿Te gustaría ver fotos? [WhatsApp]({WHATSAPP_URL})"

3. Para preguntas fuera de tema:
   "Actualmente solo puedo ayudarte con información sobre pijamas. ¿Te interesa saber sobre [tema relacionado]?"
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

@app.post("/api/chat")
async def handle_chat(request: Request):
    try:
        data = await request.json()
        user_message = data.get("message", "").strip()
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Mensaje vacío")
        
        logger.info(f"Consulta recibida: {user_message}")
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        
        # Verificar si es consulta sobre productos
        if any(keyword in user_message.lower() for keyword in ["precio", "cuesta", "valor", "producto"]):
            messages.insert(1, {
                "role": "system", 
                "content": "Recuerda mencionar siempre: 1) Precio con formato $XX,XXX COP, 2) Tallas disponibles, 3) Enlace a WhatsApp"
            })
        
        api_response = await call_ai_api(messages)
        
        if not api_response.get("choices"):
            raise ValueError("Respuesta inesperada de la API")
        
        ai_response = api_response["choices"][0]["message"]["content"]
        logger.info(f"Respuesta generada: {ai_response[:200]}...")
        
        return JSONResponse({
            "response": ai_response[:1500],
            "suggestions": ["Ver fotos", "Consultar talla", "Métodos de pago"]
        })
        
    except HTTPException as he:
        logger.warning(f"Error controlado: {str(he)}")
        return JSONResponse(
            content={"response": "🔍 Por favor envía un mensaje válido"},
            status_code=he.status_code
        )
        
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return JSONResponse(
            content={"response": f"⚠️ Error temporal. Contáctanos por [WhatsApp]({WHATSAPP_URL}) para atención inmediata."},
            status_code=200
        )

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
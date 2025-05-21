from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import requests
import os
from dotenv import load_dotenv

# Cargar variables de entorno (para desarrollo local)
load_dotenv()

app = FastAPI()

# Configuración (usa variables de entorno)
API_KEY = os.getenv("API_KEY")  # Render inyectará esta variable
ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

# Prompt especializado para Pijamas Shalom
SYSTEM_PROMPT = """
Eres un asistente especializado en Pijamas Shalom. Solo responde sobre:

1. **Productos**:
   - Catálogo: Pijamas (Hombre/Mujer/Niños)
   - Materiales: 100% algodón
   - Tallas: S, M, L, XL

2. **Precios y Promociones**:
   - Rango: $50,000 - $120,000 COP
   - Descuentos por compras mayores a 3 unidades

3. **Envíos**:
   - Cúcuta: $5,000 COP (24h)
   - Otras ciudades: $15,000 COP (2-3 días)

4. **Políticas**:
   - Cambios: 3 días hábiles
   - WhatsApp de atención: +57 1234567890

Si la pregunta no es sobre pijamas, responde:
"Lo siento, solo puedo ayudarte con información de Pijamas Shalom. ¿Deseas conocer nuestro catálogo o métodos de pago?"
"""

@app.post("/manychat-webhook")
async def handle_manychat(request: Request):
    try:
        # 1. Validar solicitud
        data = await request.json()
        user_message = data.get("message", "").strip()
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Mensaje vacío")

        # 2. Llamar a DeepSeek API
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
                "max_tokens": 500  # Controlar longitud de respuesta
            },
            timeout=10  # Evitar esperas infinitas
        )

        # 3. Procesar respuesta
        response.raise_for_status()  # Lanza error si HTTP no es 200
        ai_response = response.json()["choices"][0]["message"]["content"]

        # 4. Formatear para ManyChat
        return JSONResponse({
            "messages": [
                {
                    "type": "text",
                    "text": ai_response[:1500]  # Limitar caracteres
                },
                {
                    "type": "action",  # Botón opcional
                    "action": {
                        "type": "url",
                        "url": "https://w.app/ogzaqz",
                        "text": "📞 Contactar a WhatsApp",
                        "target": "blank"
                    }
                }
            ]
        })

    except requests.exceptions.RequestException as e:
        return JSONResponse(
            status_code=502,
            content={
                "messages": [{
                    "type": "text",
                    "text": "🔴 Servicio temporalmente no disponible. Por favor contáctanos directamente por WhatsApp."
                }]
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "messages": [{
                    "type": "text",
                    "text": "⚠️ Ocurrió un error inesperado. Nuestro equipo ya está trabajando para solucionarlo."
                }]
            }
        )

# Health Check (opcional para Render)
@app.get("/")
async def health_check():
    return {"status": "OK", "service": "Pijamas Shalom Bot"}
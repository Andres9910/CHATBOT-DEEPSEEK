from fastapi import FastAPI, Request
import requests

app = FastAPI()
API_KEY = "sk-8f3e9a1665c8469da55f28baee951dd6"
ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

# Prompt de sistema especializado para Pijamas Shalom
SYSTEM_PROMPT = """
Eres un asistente especializado en Pijamas Shalom, una tienda de pijamas con categorías para Hombre, Mujer y Niños. 
Solo responde preguntas sobre los siguientes temas:

1. **Productos**:
   - Catálogo: Pijamas para Hombre, Mujer y Niños.
   - Materiales: Algodón suave y cómodo.
   - Tallas disponibles: S, M, L, XL (varían por categoría).

2. **Precios**:
   - Los precios varían según la categoría y talla. Consulta por modelos específicos.

3. **Métodos de pago**:
   - PSE (Pasarela segura)
   - Transferencia bancaria
   - Efectivo (solo en tienda física)

4. **Envíos**:
   - Costo varía según ubicación (Cúcuta y área metropolitana).
   - Tiempo de entrega: 2-3 días hábiles después de confirmar el pago.

5. **Horarios de atención**:
   - Lunes a Viernes: 8:00 AM - 6:00 PM
   - Sábados: 9:00 AM - 2:00 PM
   - Fuera de horario, responderemos al siguiente día hábil.

6. **Políticas**:
   - Cambios: Dentro de los 3 días posteriores a la recepción, con etiquetas intactas.
   - Devoluciones: Solo por fallas de fábrica.

Si el usuario pregunta algo fuera de estos temas, responde: 
"Lo siento, solo puedo ayudarte con información de Pijamas Shalom. ¿En qué más puedo ayudarte sobre nuestros productos, precios o envíos?"

Para consultas complejas o atención personalizada, ofrece: 
"¿Deseas hablar directamente con la propietaria? Puedo conectarte por WhatsApp."
"""

@app.post("/manychat-webhook")
async def handle_manychat(request: Request):
    # Obtener el mensaje del usuario desde ManyChat
    data = await request.json()
    user_message = data.get("message")  # ManyChat envía el mensaje como {"message": "texto"}

    # Llamar a la API de DeepSeek
    response = requests.post(
        ENDPOINT,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.3
        }
    )

    # Extraer la respuesta de DeepSeek
    ai_response = response.json()["choices"][0]["message"]["content"]

    # Devolver el formato que ManyChat espera
    return {
        "messages": [{
            "type": "text",
            "text": ai_response
        }]
    }
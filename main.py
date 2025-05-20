from fastapi import FastAPI, Request
import requests

app = FastAPI()
API_KEY = "sk-8f3e9a1665c8469da55f28baee951dd6"
ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

# Prompt de sistema para especializar el modelo
SYSTEM_PROMPT = """
Eres un asistente especializado en [Nombre de tu Tienda]. 
Solo responde preguntas sobre productos, precios, envíos y políticas. 
Si el usuario pregunta algo fuera de tema, responde: 
"Lo siento, solo puedo ayudarte con información de [Nombre de tu Tienda]".
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
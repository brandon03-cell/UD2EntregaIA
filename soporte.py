import json
import os
import random
import time

from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError

# Cargar las variables desde el archivo .env
load_dotenv()
if not os.getenv("GEMINI_API_KEY"):
    exit("Falta GEMINI_API_KEY en el archivo .env")

# Inicializar el cliente (coge la GEMINI_API_KEY del entorno)
client = genai.Client()

# Esquema JSON que tiene que cumplir la respuesta
esquema_json = {
    "type": "OBJECT",
    "properties": {
        "categoria": {
            "type": "STRING",
            "enum": ["incidencia_envio", "devolucion", "consulta_producto", "otro"]
        },
        "prioridad": {
            "type": "STRING",
            "enum": ["alta", "media", "baja"]
        },
        "respuesta_sugerida": {
            "type": "STRING",
            "description": "Borrador de respuesta cordial en español para el cliente"
        }
    },
    "required": ["categoria", "prioridad", "respuesta_sugerida"]
}

config = genai.types.GenerateContentConfig(
    system_instruction="Eres un agente de atención al cliente de una empresa de comercio internacional. "
                       "Clasifica la consulta del cliente y redacta un borrador de respuesta cordial, siempre en español.",
    temperature=0.2,
    response_mime_type="application/json",
    response_schema=esquema_json
)

# Errores transitorios (sí se reintentan)
ERRORES_TRANSITORIOS = (429, 500, 503)


def analizar_consulta(mensaje, max_retries=5, base_delay=1.0):
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=mensaje,
                config=config
            )
            # Comprobar que la respuesta no se ha cortado a la mitad
            if response.candidates[0].finish_reason != "STOP":
                raise ValueError(f"Respuesta incompleta ({response.candidates[0].finish_reason})")
            return json.loads(response.text)

        except APIError as e:
            # Errores permanentes (400, 401, 403, 404) o último intento: no se reintenta
            if e.code not in ERRORES_TRANSITORIOS or attempt == max_retries - 1:
                raise e

            # Tiempo base exponencial: 1s, 2s, 4s, 8s...
            backoff_delay = base_delay * (2 ** attempt)
            # Jitter: variación aleatoria para que no se reintente todo a la vez
            jitter = random.uniform(0, backoff_delay)
            sleep_time = backoff_delay + jitter
            print(f"[Error {e.code}] Reintento {attempt + 1}/{max_retries}. Esperando {sleep_time:.2f}s...")
            time.sleep(sleep_time)


mensaje = input("Consulta del cliente: ")
try:
    resultado = analizar_consulta(mensaje)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
except Exception as e:
    print("No se ha podido analizar la consulta:", e)

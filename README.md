# UD2. Traductor offline y servicio de soporte con Gemini

Dos herramientas para el panel de administración del cliente:

1. **Traductor offline** (`index.html`): traduce inglés ↔ español en el propio navegador con Transformers.js. El modelo se ejecuta en el ordenador del usuario, así que no hay coste por traducción.
2. **Servicio de soporte** (`soporte.py`): clasifica las consultas de los clientes y prepara un borrador de respuesta con la API de Gemini, desde Python, que es quien guarda la clave.

## Archivos

| Archivo | Descripción |
|---|---|
| `index.html` | Traductor (HTML, CSS y JS en el mismo archivo) |
| `soporte.py` | Backend con Gemini |
| `.env.example` | Ejemplo de la variable de entorno |
| `.gitignore` | Para no subir el `.env` |
| `requirements.txt` | Librerías de Python |
| `README.md` | Este archivo |

## Frontend: traductor offline

- Transformers.js se importa desde el CDN de jsDelivr en un `<script type="module">`, sin instalar nada.
- Se usa `pipeline('translation', modelo)` con un modelo por sentido:
  - `Xenova/opus-mt-en-es` (inglés → español)
  - `Xenova/opus-mt-es-en` (español → inglés)
- Los modelos ya cargados se guardan en `traductores` para no descargarlos otra vez al cambiar de dirección.
- **Aceleración por hardware:** si existe `navigator.gpu` se usa `webgpu`; si no, `wasm`. La carga está dentro de un `try/catch` y, si WebGPU falla, se vuelve a cargar con `wasm` (plan B, más lento pero funciona en cualquier navegador). La página muestra el dispositivo en uso.
- El estado muestra el porcentaje de descarga (`progress_callback`), "Modelo listo para usar.", "Traduciendo..." y "¡Hecho!". El botón se desactiva mientras carga o traduce.

> Hay que abrirlo con un servidor local (`python -m http.server 8000`): con doble clic el navegador no carga el módulo, y WebGPU solo funciona con HTTPS o en `localhost`.

## Backend: servicio de soporte técnico

- La llamada a Gemini se hace desde el backend, nunca desde el navegador, para que la API key no se vea en la pestaña Network.
- La clave está en `.env` (`GEMINI_API_KEY`). `load_dotenv()` la carga y `genai.Client()` la coge sola. Si falta, el programa avisa.
- Librería oficial `google-genai` con el modelo `gemini-3.1-flash-lite` (rápido y barato, suficiente para clasificar).
- `system_instruction` con el papel del agente y `temperature=0.2` para respuestas estables.
- **Salida estructurada:** `response_mime_type="application/json"` y `response_schema` con un esquema de tres campos obligatorios; `categoria` y `prioridad` llevan `enum` para que Gemini no invente valores.
- Antes de `json.loads` se comprueba que `finish_reason` sea `STOP`; si no, la respuesta podría estar cortada y se lanza un error.

Ejemplo con "my package never arrived":

```json
{
  "categoria": "incidencia_envio",
  "prioridad": "alta",
  "respuesta_sugerida": "Estimado cliente, lamentamos que su pedido no haya llegado..."
}
```

## Gestión de errores

- Los errores 400, 401, 403 y 404 son permanentes (petición o clave incorrecta) y **no** se reintentan.
- Los errores 429, 500 y 503 son transitorios y se reintentan hasta 5 veces.
- Espera con backoff exponencial `base_delay * 2 ** attempt` (1, 2, 4, 8 s) más un **jitter** aleatorio entre 0 y ese tiempo, para que muchos clientes no reintenten a la vez.
- En el último intento el error se lanza y lo recoge el `try/except` final, que lo muestra sin cerrar el programa de golpe.

## Seguridad

La API key solo está en el `.env` local. El `.gitignore` incluye `.env` para que nunca se suba, y en el repositorio va `.env.example` para saber qué variable crear. Si la clave se subiera por error a GitHub no bastaría con borrar el commit: habría que revocarla en Google AI Studio y crear otra.

## Cómo ejecutarlo

```bash
pip install -r requirements.txt
cp .env.example .env        # y poner la clave dentro
python soporte.py

python -m http.server 8000  # y abrir http://localhost:8000
```

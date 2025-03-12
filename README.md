# JarvisIA (0.2)
Literalmente Jarvis.
Inspirado en el icónico J.A.R.V.I.S. de Tony Stark. Utiliza OpenAI GPT-4, ElevenLabs, y varias herramientas del sistema para responder preguntas, ejecutar comandos y realizar tareas automatizadas.

✨ Características
✅ Reconocimiento de voz (SpeechRecognition) para recibir comandos hablados.
✅ Síntesis de voz realista con ElevenLabs AI.
✅ Interacción con OpenAI GPT-4 para responder preguntas y generar código.
✅ Ejecución segura de comandos Python en un entorno controlado.
✅ Acceso a funciones del sistema como archivos, procesos y red.

🛠️ Instalación
1️⃣ Clona este repositorio:

bash
Copiar
Editar
git clone https://github.com/tu-usuario/jarvis-assistant.git
cd jarvis-assistant
2️⃣ Instala las dependencias:

bash
Copiar
Editar
pip install -r requirements.txt
3️⃣ Configura tus claves API en variables de entorno:

bash
Copiar
Editar
export OPENAI_API_KEY="tu-clave-openai"
export ELEVENLABS_API_KEY="tu-clave-elevenlabs"
4️⃣ Ejecuta el asistente:

bash
Copiar
Editar
python jarvis.py
🎤 Uso
Habla con JARVIS presionando Enter.
Interrumpe la voz con ESC.
Pide acciones del sistema, como:
"Crea un archivo llamado notas.txt".
"Muestra los procesos en ejecución".
"Dime cuánta memoria RAM estoy usando".
🚀 Funcionalidades Avanzadas
Ejecución de código en un entorno seguro con acceso restringido a módulos del sistema.
División de texto en fragmentos para mejorar la síntesis de voz.
Búsqueda en la web y generación de respuestas inteligentes.
⚡ Mejoras Futuras
🔹 Integración con Google Search API para búsquedas más avanzadas.
🔹 Integracion con Blender Api para generacion de modelos 3D

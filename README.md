# Jarvis IA (0.2)

💡 **Literalmente Jarvis.**  
Inspirado en el icónico J.A.R.V.I.S. de Tony Stark. Utiliza OpenAI GPT-4, ElevenLabs y varias herramientas del sistema para responder preguntas, ejecutar comandos y realizar tareas automatizadas.

---

## ✨ Características  
✅ **Reconocimiento de voz** (SpeechRecognition) para recibir comandos hablados.  
✅ **Síntesis de voz realista** con ElevenLabs AI.  
✅ **Interacción con OpenAI GPT-4** para responder preguntas y generar código.  
✅ **Ejecución segura de comandos Python** en un entorno controlado.  
✅ **Acceso a funciones del sistema** como archivos, procesos y red.  

---

## 🛠️ Instalación Windows 

### 1️⃣ Clona este repositorio:  
```bash
git clone https://github.com/poiferto12/JarvisIA.git
cd jarvis-assistant
```
### 2️⃣ Instala las dependencias:
```bash
pip install -r requirements.txt
```
### 3️⃣ Configura tus claves API en variables de entorno:
```bash
export OPENAI_API_KEY="tu-clave-openai"
export ELEVENLABS_API_KEY="tu-clave-elevenlabs"
```
### 4️⃣ Ejecuta el asistente:
```bash
python chatbot.py
```
---
## 🎤 Uso
Habla con JARVIS presionando Enter e interrumpe la voz con la tecla ESC.
### Ejemplos de comandos:

- "Crea un archivo llamado notas.txt"
- "Muestra los procesos en ejecución"
- "Dime cuánta memoria RAM estoy usando"

---

## 🛠️ Planes a futuro:
- Mejora del reconocimiento y la síntesis de voz
- Integracion de Google Search API para busquedas mas avanzadas
- Integracion con Blender API para generacion de modelos 3D

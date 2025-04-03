# Jarvis IA (0.4)

💡 **Literalmente Jarvis.**  
Inspirado en el icónico J.A.R.V.I.S. de Tony Stark. Utiliza OpenAI GPT-4, ElevenLabs y varias herramientas del sistema para responder preguntas, ejecutar comandos y realizar tareas automatizadas.

## ✨ Características  
✅ **Reconocimiento de voz** (SpeechRecognition) para recibir comandos hablados.  
✅ **Síntesis de voz realista** con ElevenLabs AI.  
✅ **Interacción con OpenAI GPT-4** para responder preguntas y generar código.  
✅ **Ejecución segura de comandos Python** en un entorno controlado.  
✅ **Acceso a funciones del sistema** como archivos, procesos y red.  

## Nuevo respecto a la versión anterior
✅ **Añadido un menu simple** para configurar el chatbot y mayor calidad de vida.  
✅ **Ahora es posible usar solo texto**, pudiendo prescindir de la clave de Elevenlabs.  
✅ **Si por algun motivo no se pudiese aplicar la sintesis de voz, se pasaría a modo texto automaticamente**  
✅**Jarvis ahora funciona en Linux y Windows** y tambien deberia de funcionar en MAC, pero no soy rico, asi que no puedo testearlo.

## 🛠️ Instalación Windows

### 0️⃣ Prerrequisitos:

```plaintext
- Python 3.8 o superior (asegúrate de marcar "Add Python to PATH" durante la instalación)
- Git para Windows
- Microsoft Visual C++ Redistributable (necesario para algunas dependencias)
```

### 1️⃣ Clona este repositorio:

```bat
git clone https://github.com/poiferto12/JarvisIA.git
cd JarvisIA
```

### 2️⃣ Instala las dependencias:

```bat
pip install -r requirements.txt

# Si PyAudio falla al instalar con requirements.txt, prueba instalarlo manualmente:
# pip install pipwin
# pipwin install pyaudio
```

### 3️⃣ Configura tus claves API en variables de entorno:

```bat
# En Command Prompt (CMD)
set OPENAI_API_KEY=tu-clave-openai
set ELEVENLABS_API_KEY=tu-clave-elevenlabs

# O en PowerShell
$env:OPENAI_API_KEY = "tu-clave-openai"
$env:ELEVENLABS_API_KEY = "tu-clave-elevenlabs"

# Para configurar permanentemente (Panel de Control > Sistema > Configuración avanzada del sistema > Variables de entorno)
```

### 4️⃣ Ejecuta el asistente:

```bat
python chatbot.py
```

## 🐧 Instalación en Linux

### 1️⃣ Clona este repositorio:

```shellscript
git clone https://github.com/poiferto12/JarvisIA.git
cd JarvisIA
```

### 2️⃣ Instala las dependencias:

#### Dependencias del sistema:

```shellscript
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3-pyaudio portaudio19-dev

# Fedora
sudo dnf install portaudio portaudio-devel

# Arch Linux
sudo pacman -S portaudio
```

#### Dependencias de Python:

```shellscript
pip install -r requirements.txt
```

### 3️⃣ Configura tus claves API:

```shellscript
# Temporal (para la sesión actual)
export OPENAI_API_KEY="tu-clave-openai"
export ELEVENLABS_API_KEY="tu-clave-elevenlabs"

# Permanente (añadir a tu .bashrc o .zshrc)
echo 'export OPENAI_API_KEY="tu-clave-openai"' >> ~/.bashrc
echo 'export ELEVENLABS_API_KEY="tu-clave-elevenlabs"' >> ~/.bashrc
source ~/.bashrc
```

### 4️⃣ Ejecuta el asistente:

```shellscript
python chatbot.py
```
## 🎤 Uso
Habla con JARVIS presionando Enter e interrumpe la voz con la tecla ESC.
### Ejemplos de comandos:

- "Crea un archivo llamado notas.txt"
- "Muestra los procesos en ejecución"
- "Dime cuánta memoria RAM estoy usando"


## 🛠️ Planes a futuro:
- Mejora del reconocimiento y la síntesis de voz
- Mejora de la generacion de código
- Integracion de Google Search API para busquedas mas avanzadas
- Integracion con Blender API para generacion de modelos 3D
- Mejora de la memoria y el retenimiento de informacion entre solicitudes

## Notas 
- El codigo python que genera para ejecutar ciertas acciones en el SO es incorrecto la mitad de las veces. La mayoría de errores suelen estar en la sintaxis del código.
- El codigo que se intenta ejecutar se hace en un entorno seguro con ciertos comandos permitidos, de igual forma, es importante tener cuidado con no borrar el ordenador entero.

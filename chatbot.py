import os
import subprocess
import psutil
import glob
from openai import OpenAI
import speech_recognition as sr
import asyncio
import time
import threading
import re
import sys
import shutil
import queue
import json
import platform
from pathlib import Path

# Detectar el sistema operativo
SISTEMA_OPERATIVO = platform.system()  # 'Windows', 'Linux', 'Darwin' (macOS)

# Verificar si elevenlabs está disponible
try:
    from elevenlabs import ElevenLabs, Voice, play
    ELEVENLABS_DISPONIBLE = True
except ImportError:
    ELEVENLABS_DISPONIBLE = False

# Verificar si keyboard está disponible
try:
    import keyboard
    KEYBOARD_DISPONIBLE = True
except ImportError:
    KEYBOARD_DISPONIBLE = False

# Configuración de la clave API de OpenAI desde la variable de entorno
client1 = OpenAI()

# Modelo y parámetros
MAX_HISTORIAL = 10

# Configuración por defecto
CONFIG_DEFAULT = {
    "modo_entrada": "texto",  # "texto" o "voz"
    "modo_salida": "texto",   # "texto" o "voz"
    "sensibilidad_voz": 300,  # Umbral de energía (300-700)
    "pausa_voz": 1.0,         # Pausa en segundos
    "duracion_ajuste": 0.5,   # Duración del ajuste de ruido
    "voice_id": "gD1IexrzCvsXPHUuT0s3",  # ID de voz de ElevenLabs
    "modelo_voz": "eleven_multilingual_v2",  # Modelo de voz
    "max_tokens": 500,        # Tokens máximos para GPT
    "temperatura": 0.7        # Temperatura para GPT
}

# Ruta del archivo de configuración
CONFIG_PATH = Path.home() / "jarvis_config.json"

class JarvisAssistant:
    def __init__(self, config=None):
        # Cargar configuración
        self.config = config if config else self.cargar_config()
        
        # Inicializar variables
        self.conversation_history = []
        self.recognizer = sr.Recognizer()
        self.is_speaking = False
        self.stop_speaking = False
        self.listening = False
        self.audio_queue = queue.Queue()
        
        # Configurar reconocedor de voz
        self.recognizer.pause_threshold = self.config["pausa_voz"]
        self.recognizer.energy_threshold = self.config["sensibilidad_voz"]
        
        # Inicializar ElevenLabs si está disponible y se usa voz
        if ELEVENLABS_DISPONIBLE and self.config["modo_salida"] == "voz":
            try:
                ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
                self.client_voz = ElevenLabs(api_key=ELEVENLABS_API_KEY)
                self.voice = Voice(voice_id=self.config["voice_id"])
                print("Síntesis de voz inicializada correctamente.")
            except Exception as e:
                print(f"Error al inicializar la síntesis de voz: {e}")
                self.config["modo_salida"] = "texto"
                print("Cambiando a modo de salida de texto.")
        
        # Crear un entorno seguro con acceso a módulos y funciones básicas
        self.safe_environment = self._create_safe_environment()

    def cargar_config(self):
        """Carga la configuración desde un archivo o usa los valores por defecto"""
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                    # Asegurarse de que todos los campos existan
                    for key, value in CONFIG_DEFAULT.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                print(f"Error al cargar la configuración: {e}")
        
        return CONFIG_DEFAULT.copy()

    def guardar_config(self):
        """Guarda la configuración actual en un archivo"""
        try:
            with open(CONFIG_PATH, 'w') as f:
                json.dump(self.config, f, indent=4)
            print(f"Configuración guardada en {CONFIG_PATH}")
            return True
        except Exception as e:
            print(f"Error al guardar la configuración: {e}")
            return False

    def _create_safe_environment(self):
        """Crea un entorno de ejecución con acceso a módulos y funciones seguras"""
        # Módulos completos o parciales que queremos permitir
        safe_env = {
            # Funciones integradas de Python
            "print": print,
            "input": input,
            "open": open,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "len": len,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "sorted": sorted,
            "sum": sum,
            "min": min,
            "max": max,
            "abs": abs,
            "round": round,
            "any": any,
            "all": all,
            "dir": dir,
            "getattr": getattr,
            "hasattr": hasattr,
            "isinstance": isinstance,
            "issubclass": issubclass,
            "type": type,
            "id": id,
            "help": help,
            # Constantes y funciones multiplataforma
            "SISTEMA_OPERATIVO": SISTEMA_OPERATIVO,
            "abrir_archivo": self.abrir_archivo,
            "obtener_escritorio": self.obtener_escritorio,
            "obtener_documentos": self.obtener_documentos,
            "ejecutar_comando": self.ejecutar_comando,
        }
        
        # Añadir módulos de forma segura
        # OS - Funciones básicas
        safe_os = type('SafeOS', (), {})()
        safe_os.listdir = os.listdir
        safe_os.getcwd = os.getcwd
        safe_os.mkdir = os.mkdir
        safe_os.makedirs = os.makedirs
        safe_os.remove = os.remove
        safe_os.rmdir = os.rmdir
        safe_os.rename = os.rename
        safe_os.chdir = os.chdir
        safe_os.walk = os.walk
        safe_os.environ = os.environ
        
        # OS.PATH - Funciones de manejo de rutas
        safe_os_path = type('SafeOSPath', (), {})()
        safe_os_path.join = os.path.join
        safe_os_path.exists = os.path.exists
        safe_os_path.isfile = os.path.isfile
        safe_os_path.isdir = os.path.isdir
        safe_os_path.abspath = os.path.abspath
        safe_os_path.basename = os.path.basename
        safe_os_path.dirname = os.path.dirname
        safe_os_path.expanduser = os.path.expanduser
        safe_os_path.splitext = os.path.splitext
        safe_os.path = safe_os_path
        
        # Subprocess - Funciones para ejecutar comandos
        safe_subprocess = type('SafeSubprocess', (), {})()
        safe_subprocess.run = subprocess.run
        safe_subprocess.Popen = subprocess.Popen
        safe_subprocess.PIPE = subprocess.PIPE
        safe_subprocess.STDOUT = subprocess.STDOUT
        safe_subprocess.call = subprocess.call
        safe_subprocess.check_output = subprocess.check_output
        
        # Shutil - Operaciones de archivos avanzadas
        safe_shutil = type('SafeShutil', (), {})()
        safe_shutil.copy = shutil.copy
        safe_shutil.copy2 = shutil.copy2
        safe_shutil.copytree = shutil.copytree
        safe_shutil.move = shutil.move
        safe_shutil.rmtree = shutil.rmtree
        
        # Psutil - Monitoreo del sistema
        safe_psutil = type('SafePsutil', (), {})()
        safe_psutil.process_iter = psutil.process_iter
        safe_psutil.cpu_percent = psutil.cpu_percent
        safe_psutil.virtual_memory = psutil.virtual_memory
        safe_psutil.disk_usage = psutil.disk_usage
        if hasattr(psutil, 'net_io_counters'):
            safe_psutil.net_io_counters = psutil.net_io_counters
        if hasattr(psutil, 'sensors_temperatures'):
            safe_psutil.sensors_temperatures = psutil.sensors_temperatures
        
        # Time - Funciones de tiempo
        safe_time = type('SafeTime', (), {})()
        safe_time.sleep = time.sleep
        safe_time.time = time.time
        safe_time.ctime = time.ctime
        safe_time.strftime = time.strftime
        safe_time.localtime = time.localtime
        
        # Platform - Información del sistema
        safe_platform = type('SafePlatform', (), {})()
        safe_platform.system = platform.system
        safe_platform.platform = platform.platform
        safe_platform.version = platform.version
        safe_platform.machine = platform.machine
        safe_platform.processor = platform.processor
        safe_platform.architecture = platform.architecture
        
        # Añadir todos los módulos seguros al entorno
        safe_env["os"] = safe_os
        safe_env["subprocess"] = safe_subprocess
        safe_env["glob"] = glob
        safe_env["re"] = re
        safe_env["time"] = safe_time
        safe_env["shutil"] = safe_shutil
        safe_env["psutil"] = safe_psutil
        safe_env["platform"] = safe_platform
        safe_env["Path"] = Path
        
        return safe_env

    def abrir_archivo(self, ruta):
        """Abre un archivo con la aplicación predeterminada de manera multiplataforma"""
        try:
            ruta_abs = os.path.abspath(os.path.expanduser(ruta))
            if not os.path.exists(ruta_abs):
                return f"Error: El archivo {ruta_abs} no existe"
                
            if SISTEMA_OPERATIVO == "Windows":
                os.startfile(ruta_abs)
            elif SISTEMA_OPERATIVO == "Darwin":  # macOS
                subprocess.Popen(["open", ruta_abs])
            else:  # Linux y otros
                subprocess.Popen(["xdg-open", ruta_abs])
                
            return f"Abriendo: {ruta_abs}"
        except Exception as e:
            return f"Error al abrir el archivo: {str(e)}"

    def obtener_escritorio(self):
        """Devuelve la ruta al escritorio de manera multiplataforma"""
        return os.path.join(os.path.expanduser("~"), "Desktop")

    def obtener_documentos(self):
        """Devuelve la ruta a documentos de manera multiplataforma"""
        if SISTEMA_OPERATIVO == "Windows":
            return os.path.join(os.path.expanduser("~"), "Documents")
        elif SISTEMA_OPERATIVO == "Darwin":  # macOS
            return os.path.join(os.path.expanduser("~"), "Documents")
        else:  # Linux
            # Intentar encontrar la carpeta de documentos según el estándar XDG
            xdg_config = os.path.expanduser("~/.config/user-dirs.dirs")
            if os.path.exists(xdg_config):
                with open(xdg_config, 'r') as f:
                    for line in f:
                        if line.startswith('XDG_DOCUMENTS_DIR'):
                            path = line.split('=')[1].strip().strip('"').replace('$HOME', os.path.expanduser('~'))
                            return path
            # Si no se encuentra, usar el valor predeterminado
            return os.path.join(os.path.expanduser("~"), "Documents")

    def ejecutar_comando(self, comando, shell=True, timeout=10):
        """Ejecuta un comando del sistema de forma segura y multiplataforma"""
        # Lista de comandos prohibidos
        dangerous_commands = ['rm -rf', 'format', 'mkfs', 'dd', ':(){:|:&};:', 'wget', 'curl', 'del /f', 'deltree']
        
        # Verificar si el comando contiene alguna palabra peligrosa
        if any(cmd in comando.lower() for cmd in dangerous_commands):
            return "Comando rechazado por motivos de seguridad"
        
        try:
            # Adaptar el comando según el sistema operativo
            if SISTEMA_OPERATIVO == "Windows":
                # Convertir comandos comunes de Unix a Windows
                if comando.startswith("ls"):
                    comando = comando.replace("ls", "dir", 1)
                elif comando.startswith("cat"):
                    comando = comando.replace("cat", "type", 1)
                elif comando.startswith("clear"):
                    comando = "cls"
            
            result = subprocess.run(
                comando, 
                shell=shell, 
                capture_output=True, 
                text=True, 
                timeout=timeout
            )
            return {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return "El comando excedió el tiempo límite"
        except Exception as e:
            return f"Error al ejecutar el comando: {str(e)}"

    def listen_callback(self, recognizer, audio):
        """Callback para procesar el audio capturado"""
        try:
            if not self.listening:
                return
                
            text = recognizer.recognize_google(audio, language="es-ES")
            if text:
                print(f"Reconocido: {text}")
                self.audio_queue.put(text)
        except sr.UnknownValueError:
            print("No se pudo entender el audio")
        except sr.RequestError as e:
            print(f"Error en el servicio de reconocimiento de voz: {e}")

    def stop_listening_callback(self):
        """Detiene la escucha cuando se presiona Enter"""
        self.listening = False
        print("\nDetención de escucha solicitada...")

    async def listen_voice(self) -> str:
        """
        Escucha la entrada de voz del usuario con mejoras.
        Comienza a escuchar cuando se presiona Enter y termina cuando se vuelve a presionar Enter.
        """
        print("Presiona Enter para comenzar a hablar...")
        input()
        
        # Inicializar variables
        self.listening = True
        self.audio_queue = queue.Queue()
        collected_text = []
        
        # Configurar el callback para detener la escucha
        if KEYBOARD_DISPONIBLE:
            keyboard.add_hotkey('enter', self.stop_listening_callback)
            print("Escuchando... (Presiona Enter para detener)")
        else:
            print("Escuchando... (Espera o presiona Ctrl+C para detener)")
        
        # Usar el reconocedor en modo no bloqueante
        with sr.Microphone() as source:
            # Ajustar para el ruido ambiental
            print("Ajustando para el ruido ambiental...")
            self.recognizer.adjust_for_ambient_noise(source, duration=self.config["duracion_ajuste"])
            print(f"Umbral de energía ajustado a: {self.recognizer.energy_threshold}")
            
            # Iniciar escucha en segundo plano
            stop_listening = self.recognizer.listen_in_background(source, self.listen_callback)
            
            # Esperar hasta que se presione Enter o haya un timeout
            timeout = time.time() + 60  # 60 segundos máximo de escucha
            try:
                while self.listening and time.time() < timeout:
                    try:
                        # Verificar si hay texto reconocido en la cola
                        text = self.audio_queue.get(timeout=0.5)
                        collected_text.append(text)
                        # Reiniciar el timeout cuando se detecta habla
                        timeout = time.time() + 60
                    except queue.Empty:
                        # No hay texto nuevo, continuar esperando
                        pass
                    
                    # Si no ha habido actividad por 5 segundos y hay texto, detener
                    if collected_text and time.time() - timeout > -55:  # 60-55=5 segundos de inactividad
                        print("Inactividad detectada, deteniendo escucha...")
                        self.listening = False
            except KeyboardInterrupt:
                print("\nDetención manual solicitada...")
                self.listening = False
            
            # Detener la escucha en segundo plano
            stop_listening(wait_for_stop=False)
        
        # Eliminar el hotkey si está disponible
        if KEYBOARD_DISPONIBLE:
            keyboard.remove_hotkey('enter')
        
        # Unir todo el texto reconocido
        full_text = " ".join(collected_text)
        
        if full_text:
            print(f"Usuario: {full_text}")
            return full_text
        else:
            print("No se detectó ninguna entrada de voz.")
            return ""

    async def listen_text(self) -> str:
        """Obtiene entrada de texto del usuario"""
        text = input("Tú: ")
        return text

    async def listen(self) -> str:
        """Obtiene entrada del usuario según el modo configurado"""
        if self.config["modo_entrada"] == "voz":
            return await self.listen_voice()
        else:
            return await self.listen_text()

    def split_text_into_chunks(self, text, max_chars=75):
        """Divide el texto en fragmentos más pequeños para una respuesta más rápida"""
        # Dividir por oraciones
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= max_chars:
                current_chunk += " " + sentence if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

    def speak_chunk(self, text):
        """Genera y reproduce un fragmento de audio"""
        if not ELEVENLABS_DISPONIBLE or self.config["modo_salida"] != "voz":
            return
            
        try:
            if self.stop_speaking:
                return
                
            audio = self.client_voz.generate(
                text=text,
                voice=self.voice,
                model=self.config["modelo_voz"]
            )
            play(audio)
        except Exception as e:
            print(f"Error al generar voz: {str(e)}")
            # Cambiar a modo texto si hay error
            print("Cambiando a modo de salida de texto.")
            self.config["modo_salida"] = "texto"

    async def speak(self, text: str):
        """Habla o muestra el texto según el modo configurado"""
        # Siempre mostrar el texto en la consola
        print(f"Jarvis: {text}")
        
        # Si el modo es texto, terminar aquí
        if self.config["modo_salida"] != "voz" or not ELEVENLABS_DISPONIBLE:
            return
            
        # Establecer flags
        self.is_speaking = True
        self.stop_speaking = False
        
        # Dividir el texto en fragmentos
        chunks = self.split_text_into_chunks(text)
        
        # Iniciar un hilo para el primer fragmento inmediatamente
        if chunks:
            first_chunk = chunks[0]
            first_thread = threading.Thread(target=self.speak_chunk, args=(first_chunk,))
            first_thread.start()
            
            # Esperar a que termine el primer fragmento
            first_thread.join()
            
            # Procesar el resto de fragmentos si no se ha interrumpido
            for chunk in chunks[1:]:
                if self.stop_speaking:
                    break
                    
                chunk_thread = threading.Thread(target=self.speak_chunk, args=(chunk,))
                chunk_thread.start()
                chunk_thread.join()
        
        self.is_speaking = False

    def interrupt_speech(self):
        """Interrumpe la reproducción de voz actual"""
        if self.is_speaking:
            print("Interrumpiendo la voz...")
            self.stop_speaking = True

    async def process_command(self, command: str):
        self.conversation_history.append({"role": "user", "content": command})

        if len(self.conversation_history) > MAX_HISTORIAL:
            self.conversation_history = self.conversation_history[-MAX_HISTORIAL:]

        # Obtener respuesta de la IA
        response = await self.get_gpt_response()
        
        # Verificar si la respuesta contiene código para ejecutar
        if "CODIGO:" in response:
            print("\n--- Detectado código para ejecutar ---")
            code_parts = response.split("CODIGO:", 1)
            
            # Si hay texto antes del código, lo decimos
            if code_parts[0].strip():
                await self.speak(code_parts[0].strip())
            
            # Extraer el código
            code = code_parts[1].strip()
            print("\nCódigo generado por la IA:")
            print("-" * 40)
            print(code)
            print("-" * 40)
            
            # Ejecutar el código
            try:
                result = self.execute_code(code)
                
                # Si hay un resultado, lo decimos
                if result:
                    await self.speak(f"Resultado: {result}")
                else:
                    await self.speak("Código ejecutado con éxito.")
            except Exception as e:
                print(f"Error al ejecutar código: {str(e)}")
                await self.speak(f"Hubo un error al ejecutar el código: {str(e)}")
        else:
            # Si no hay código, simplemente respondemos
            self.conversation_history.append({"role": "assistant", "content": response})
            await self.speak(response)

    def execute_code(self, code):
        """Ejecuta código Python en un entorno seguro y devuelve el resultado"""
        # Capturar la salida estándar
        import io
        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output
        
        # Variable para almacenar el resultado
        result = None
        
        # Ejecutar el código
        try:
            # Modificar el código para capturar el resultado de la última expresión
            lines = code.strip().split('\n')
            if lines and not lines[-1].strip().startswith(('if', 'for', 'while', 'def', 'class', 'try', 'with')):
                # Si la última línea parece una expresión, capturamos su valor
                last_line = lines[-1]
                if not last_line.strip().endswith(':') and '=' not in last_line:
                    lines[-1] = f"__result = {last_line}"
            
            # Unir las líneas de nuevo
            modified_code = '\n'.join(lines)
            
            # Ejecutar el código modificado
            local_vars = {}
            exec(modified_code, self.safe_environment, local_vars)
            
            # Obtener el resultado si existe
            if '__result' in local_vars:
                result = local_vars['__result']
        finally:
            # Restaurar la salida estándar
            sys.stdout = old_stdout
        
        # Obtener la salida capturada
        output = redirected_output.getvalue()
        
        # Si hay salida, la imprimimos
        if output:
            print("Salida del código:")
            print(output)
            # Si no hay resultado pero hay salida, usamos la salida como resultado
            if result is None and output.strip():
                result = output.strip()
        
        # Devolver el resultado
        return result

    async def get_gpt_response(self) -> str:
        try:
            messages = [
                {"role": "system", "content": """Eres JARVIS, la IA creada por Tony Stark. Puedes generar código Python para ejecutar comandos del usuario.
                
                IMPORTANTE: Cuando el usuario te pida realizar una acción en el sistema, DEBES responder con 'CODIGO:' seguido del código Python en una nueva línea.
                IMPORTANTE: Cuando generes código Python, NO incluyas delimitadores de formato como ```python o ``` alrededor del código. 
                Proporciona SOLO el código Python puro que se ejecutará directamente.
                
                (INCORRECTO:
                CODIGO:
                ```python
                print("Hola mundo"))

                El usuario está ejecutando este programa en un sistema """ + SISTEMA_OPERATIVO + """.
                
                Tienes acceso a las siguientes funciones multiplataforma:
                - abrir_archivo(ruta): Abre un archivo con la aplicación predeterminada
                - obtener_escritorio(): Devuelve la ruta al escritorio
                - obtener_documentos(): Devuelve la ruta a documentos
                - ejecutar_comando(comando): Ejecuta un comando del sistema de forma segura
                
                Tienes acceso a los siguientes módulos y funciones:
                
                1. Módulos:
                   - os: listdir, getcwd, mkdir, makedirs, remove, rmdir, rename, path, chdir, walk
                   - os.path: join, exists, isfile, isdir, abspath, basename, dirname, expanduser, splitext
                   - subprocess: run, Popen, PIPE, STDOUT, call, check_output
                   - glob: todas las funciones
                   - re: todas las funciones
                   - time: sleep, time, ctime, strftime, localtime
                   - shutil: copy, copy2, copytree, move, rmtree
                   - psutil: process_iter, cpu_percent, virtual_memory, disk_usage, net_io_counters, sensors_temperatures
                   - platform: system, platform, version, machine, processor, architecture
                   - Path: de pathlib, para manejo de rutas multiplataforma
                
                2. Funciones integradas de Python:
                   - print, input, open, str, int, float, bool, list, dict, set, tuple
                   - len, range, enumerate, zip, map, filter, sorted, sum, min, max, abs, round
                   - any, all, dir, getattr, hasattr, isinstance, issubclass, type, id, help
                
                Ejemplos de código multiplataforma que puedes generar:
                
                1. Para crear un archivo de texto:
                CODIGO:
                ruta = os.path.join(obtener_escritorio(), "archivo.txt")
                with open(ruta, "w", encoding="utf-8") as f:
                    f.write("Contenido del archivo")
                print(f"Archivo creado en: {ruta}")
                
                2. Para buscar y abrir un archivo:
                CODIGO:
                patron = "documento"
                ubicaciones = [
                    obtener_escritorio(),
                    obtener_documentos()
                ]
                archivos_encontrados = []
                for ubicacion in ubicaciones:
                    patron_busqueda = os.path.join(ubicacion, f"*{patron}*")
                    archivos_encontrados.extend(glob.glob(patron_busqueda))
                
                for archivo in archivos_encontrados:
                    print(archivo)
                
                if archivos_encontrados:
                    # Abrir el primer archivo encontrado
                    resultado = abrir_archivo(archivos_encontrados[0])
                    print(resultado)
                else:
                    print("No se encontraron archivos")
                
                3. Para obtener información del sistema:
                CODIGO:
                cpu = psutil.cpu_percent(interval=1)
                memoria = psutil.virtual_memory()
                disco = psutil.disk_usage('/')
                
                print(f"Sistema operativo: {platform.system()} {platform.version()}")
                print(f"Arquitectura: {platform.machine()}")
                print(f"Uso de CPU: {cpu}%")
                print(f"Memoria total: {memoria.total / (1024**3):.2f} GB")
                print(f"Memoria disponible: {memoria.available / (1024**3):.2f} GB")
                print(f"Uso de disco: {disco.percent}%")
                
                4. Para ejecutar un comando del sistema:
                CODIGO:
                # El comando se adaptará automáticamente según el sistema operativo
                if SISTEMA_OPERATIVO == "Windows":
                    comando = "dir"
                else:
                    comando = "ls -la"
                
                resultado = ejecutar_comando(comando)
                print(resultado['stdout'])
                
                5. Para listar procesos en ejecución:
                CODIGO:
                procesos = [p.name() for p in psutil.process_iter()]
                for proceso in sorted(procesos):
                    print(proceso)
                
                RECUERDA: SIEMPRE usa 'CODIGO:' cuando necesites ejecutar una acción en el sistema.
                """}
            ]
            
            messages.extend(self.conversation_history)
            
            # Añadir manejo de errores más detallado
            try:
                response = client1.chat.completions.create(
                    model="gpt-4",
                    messages=messages,
                    max_tokens=self.config["max_tokens"],
                    temperature=self.config["temperatura"]
                )
            
                response_text = response.choices[0].message.content
                return response_text
            except Exception as e:
                print(f"Error específico en la solicitud a OpenAI: {str(e)}")
                # Registrar más detalles para depuración
                import traceback
                traceback.print_exc()
                return "Hubo un error al obtener la respuesta. Por favor, intenta de nuevo."
        except Exception as e:
            print(f"Error general en get_gpt_response: {str(e)}")
            import traceback
            traceback.print_exc()
            return "Ocurrió un error inesperado. Por favor, intenta de nuevo."

def configurar_hotkeys(jarvis):
    """Configura las teclas de acceso rápido si el módulo keyboard está disponible"""
    if KEYBOARD_DISPONIBLE:
        keyboard.add_hotkey('esc', jarvis.interrupt_speech)
        print("Tecla ESC configurada para interrumpir la voz.")
    else:
        print("Módulo keyboard no disponible. Las teclas de acceso rápido no funcionarán.")

def mostrar_menu_configuracion(config_actual):
    """Muestra un menú para configurar las opciones de JARVIS"""
    while True:
        print("\n" + "=" * 50)
        print(" CONFIGURACIÓN DE JARVIS ")
        print("=" * 50)
        print(f"1. Modo de entrada: {config_actual['modo_entrada']}")
        print(f"2. Modo de salida: {config_actual['modo_salida']}")
        print(f"3. Sensibilidad de voz: {config_actual['sensibilidad_voz']}")
        print(f"4. Pausa de voz: {config_actual['pausa_voz']} segundos")
        print(f"5. Duración del ajuste de ruido: {config_actual['duracion_ajuste']} segundos")
        print(f"6. Tokens máximos: {config_actual['max_tokens']}")
        print(f"7. Temperatura: {config_actual['temperatura']}")
        print("8. Guardar configuración")
        print("9. Iniciar JARVIS")
        print("0. Salir")
        print("=" * 50)
        
        opcion = input("Selecciona una opción: ")
        
        if opcion == "1":
            modo = input("Modo de entrada (texto/voz): ").lower()
            if modo in ["texto", "voz"]:
                config_actual["modo_entrada"] = modo
            else:
                print("Opción no válida. Debe ser 'texto' o 'voz'.")
        
        elif opcion == "2":
            modo = input("Modo de salida (texto/voz): ").lower()
            if modo in ["texto", "voz"]:
                if modo == "voz" and not ELEVENLABS_DISPONIBLE:
                    print("Advertencia: ElevenLabs no está disponible. Se usará el modo de texto.")
                    config_actual["modo_salida"] = "texto"
                else:
                    config_actual["modo_salida"] = modo
            else:
                print("Opción no válida. Debe ser 'texto' o 'voz'.")
        
        elif opcion == "3":
            try:
                valor = int(input("Sensibilidad de voz (300-700, menor es más sensible): "))
                if 100 <= valor <= 1000:
                    config_actual["sensibilidad_voz"] = valor
                else:
                    print("El valor debe estar entre 100 y 1000.")
            except ValueError:
                print("Debes ingresar un número.")
        
        elif opcion == "4":
            try:
                valor = float(input("Pausa de voz en segundos (0.5-2.0): "))
                if 0.1 <= valor <= 3.0:
                    config_actual["pausa_voz"] = valor
                else:
                    print("El valor debe estar entre 0.1 y 3.0.")
            except ValueError:
                print("Debes ingresar un número.")
        
        elif opcion == "5":
            try:
                valor = float(input("Duración del ajuste de ruido en segundos (0.1-2.0): "))
                if 0.1 <= valor <= 2.0:
                    config_actual["duracion_ajuste"] = valor
                else:
                    print("El valor debe estar entre 0.1 y 2.0.")
            except ValueError:
                print("Debes ingresar un número.")
        
        elif opcion == "6":
            try:
                valor = int(input("Tokens máximos (100-1000): "))
                if 100 <= valor <= 1000:
                    config_actual["max_tokens"] = valor
                else:
                    print("El valor debe estar entre 100 y 1000.")
            except ValueError:
                print("Debes ingresar un número.")
        
        elif opcion == "7":
            try:
                valor = float(input("Temperatura (0.0-1.0): "))
                if 0.0 <= valor <= 1.0:
                    config_actual["temperatura"] = valor
                else:
                    print("El valor debe estar entre 0.0 y 1.0.")
            except ValueError:
                print("Debes ingresar un número.")
        
        elif opcion == "8":
            # Guardar configuración
            try:
                with open(CONFIG_PATH, 'w') as f:
                    json.dump(config_actual, f, indent=4)
                print(f"Configuración guardada en {CONFIG_PATH}")
            except Exception as e:
                print(f"Error al guardar la configuración: {e}")
        
        elif opcion == "9":
            # Iniciar JARVIS
            return config_actual
        
        elif opcion == "0":
            print("Saliendo...")
            sys.exit(0)
        
        else:
            print("Opción no válida.")

async def probar_reconocimiento_voz():
    """Función para probar el reconocimiento de voz"""
    print("\n" + "=" * 50)
    print(" PRUEBA DE RECONOCIMIENTO DE VOZ ")
    print("=" * 50)
    print("Esta prueba te permitirá ajustar los parámetros de reconocimiento de voz.")
    
    # Crear un reconocedor
    recognizer = sr.Recognizer()
    
    # Valores iniciales
    energy_threshold = 300
    pause_threshold = 1.0
    
    while True:
        print(f"\nUmbral de energía actual: {energy_threshold}")
        print(f"Umbral de pausa actual: {pause_threshold}")
        print("\n1. Probar con configuración actual")
        print("2. Ajustar umbral de energía")
        print("3. Ajustar umbral de pausa")
        print("4. Volver al menú principal")
        
        opcion = input("\nSelecciona una opción: ")
        
        if opcion == "1":
            # Configurar el reconocedor
            recognizer.energy_threshold = energy_threshold
            recognizer.pause_threshold = pause_threshold
            
            print("\nPresiona Enter y comienza a hablar...")
            input()
            
            try:
                with sr.Microphone() as source:
                    print("Ajustando para el ruido ambiental...")
                    recognizer.adjust_for_ambient_noise(source, duration=1.0)
                    print(f"Umbral de energía ajustado a: {recognizer.energy_threshold}")
                    
                    print("Escuchando...")
                    audio = recognizer.listen(source)
                    
                    print("Reconociendo...")
                    text = recognizer.recognize_google(audio, language="es-ES")
                    print(f"Texto reconocido: {text}")
            except sr.UnknownValueError:
                print("No se pudo entender el audio")
            except sr.RequestError as e:
                print(f"Error en el servicio de reconocimiento de voz: {e}")
            except Exception as e:
                print(f"Error: {e}")
        
        elif opcion == "2":
            try:
                valor = int(input("Nuevo umbral de energía (100-1000, menor es más sensible): "))
                if 100 <= valor <= 1000:
                    energy_threshold = valor
                else:
                    print("El valor debe estar entre 100 y 1000.")
            except ValueError:
                print("Debes ingresar un número.")
        
        elif opcion == "3":
            try:
                valor = float(input("Nuevo umbral de pausa en segundos (0.1-3.0): "))
                if 0.1 <= valor <= 3.0:
                    pause_threshold = valor
                else:
                    print("El valor debe estar entre 0.1 y 3.0.")
            except ValueError:
                print("Debes ingresar un número.")
        
        elif opcion == "4":
            return {"sensibilidad_voz": energy_threshold, "pausa_voz": pause_threshold}
        
        else:
            print("Opción no válida.")

async def main():
    print("\n" + "=" * 50)
    print(" JARVIS - ASISTENTE DE IA ")
    print("=" * 50)
    print("1. Iniciar JARVIS con configuración por defecto")
    print("2. Configurar JARVIS")
    print("3. Probar reconocimiento de voz")
    print("4. Salir")
    print("=" * 50)
    
    opcion = input("Selecciona una opción: ")
    
    config = CONFIG_DEFAULT.copy()
    
    if opcion == "1":
        # Cargar configuración guardada si existe
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, 'r') as f:
                    config_guardada = json.load(f)
                    # Asegurarse de que todos los campos existan
                    for key, value in CONFIG_DEFAULT.items():
                        if key not in config_guardada:
                            config_guardada[key] = value
                    config = config_guardada
                    print("Configuración cargada correctamente.")
            except Exception as e:
                print(f"Error al cargar la configuración: {e}")
                print("Usando configuración por defecto.")
    
    elif opcion == "2":
        # Mostrar menú de configuración
        config = mostrar_menu_configuracion(config)
    
    elif opcion == "3":
        # Probar reconocimiento de voz
        ajustes_voz = await probar_reconocimiento_voz()
        if ajustes_voz:
            config["sensibilidad_voz"] = ajustes_voz["sensibilidad_voz"]
            config["pausa_voz"] = ajustes_voz["pausa_voz"]
        
        # Volver al menú principal
        return await main()
    
    elif opcion == "4":
        print("Saliendo...")
        return
    
    else:
        print("Opción no válida.")
        return await main()
    
    # Iniciar JARVIS con la configuración seleccionada
    jarvis = JarvisAssistant(config)
    
    # Configurar teclas de acceso rápido
    configurar_hotkeys(jarvis)
    
    # Mostrar información sobre el modo actual
    print("\n" + "=" * 50)
    print(f" JARVIS - Modo de entrada: {config['modo_entrada'].upper()}, Modo de salida: {config['modo_salida'].upper()} ")
    print("=" * 50)
    
    if config["modo_entrada"] == "texto":
        print("Escribe tus comandos directamente. Escribe 'salir' o 'adiós' para terminar.")
    else:
        print("Presiona Enter para hablar. Presiona Enter nuevamente para detener la grabación.")
        if KEYBOARD_DISPONIBLE:
            print("Presiona ESC para interrumpir la voz de JARVIS.")
    
    print("=" * 50)
    
    await jarvis.speak("Hola, soy JARVIS. ¿En qué puedo ayudarte?")

    while True:
        command = await jarvis.listen()
        if not command:
            continue
        if command.lower() in ["adiós", "adios", "salir", "exit", "quit"]:
            await jarvis.speak("Hasta luego, señor. Estaré aquí si me necesita.")
            break
        await jarvis.process_command(command)

if __name__ == "__main__":
    asyncio.run(main())


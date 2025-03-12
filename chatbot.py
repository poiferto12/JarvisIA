import os
import subprocess
import psutil
import glob
from openai import OpenAI
import speech_recognition as sr
from elevenlabs import ElevenLabs, Voice, play
import asyncio
import time
import threading
import keyboard
import re
import inspect
import sys
import shutil

# Configuración de la clave API de OpenAI desde la variable de entorno
client1 = OpenAI()

# Configuración de ElevenLabs API
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
client = ElevenLabs(
    api_key=ELEVENLABS_API_KEY,
)

# Modelo y parámetros
MAX_HISTORIAL = 10

class JarvisAssistant:
    def __init__(self):
        self.conversation_history = []
        self.recognizer = sr.Recognizer()
        self.voice = Voice(voice_id="gD1IexrzCvsXPHUuT0s3")
        self.is_speaking = False
        self.stop_speaking = False
        
        # Crear un entorno seguro con acceso a módulos y funciones básicas
        self.safe_environment = self._create_safe_environment()

    def _create_safe_environment(self):
        """Crea un entorno de ejecución con acceso a módulos y funciones seguras"""
        # Módulos completos o parciales que queremos permitir
        safe_env = {
            # Módulos estándar
            "os": self._create_safe_module(os, [
                "listdir", "getcwd", "mkdir", "makedirs", "remove", "rmdir", 
                "rename", "path", "environ", "getenv", "chdir", "walk"
            ]),
            "subprocess": self._create_safe_module(subprocess, [
                "run", "Popen", "PIPE", "STDOUT", "call", "check_output"
            ]),
            "glob": glob,
            "re": re,
            "time": self._create_safe_module(time, [
                "sleep", "time", "ctime", "strftime", "localtime"
            ]),
            "shutil": self._create_safe_module(shutil, [
                "copy", "copy2", "copytree", "move", "rmtree"
            ]),
            "psutil": self._create_safe_module(psutil, [
                "process_iter", "cpu_percent", "virtual_memory", "disk_usage", 
                "net_io_counters", "sensors_temperatures"
            ]),
            
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
        }
        
        return safe_env

    def _create_safe_module(self, module, allowed_attributes):
        """Crea una versión segura de un módulo con acceso limitado a atributos específicos"""
        safe_module = type('SafeModule', (), {})()
        
        for attr_name in allowed_attributes:
            if hasattr(module, attr_name):
                # Si el atributo es un submódulo (como os.path), crear un submódulo seguro
                attr = getattr(module, attr_name)
                if inspect.ismodule(attr):
                    # Obtener todos los atributos del submódulo
                    sub_attrs = [name for name in dir(attr) 
                                if not name.startswith('_') and 
                                not name in ['system', 'exec', 'eval', 'execfile', 'compile']]
                    setattr(safe_module, attr_name, self._create_safe_module(attr, sub_attrs))
                else:
                    setattr(safe_module, attr_name, attr)
        
        return safe_module

    async def listen(self) -> str:
        # Versión simplificada: presiona Enter para hablar
        input("Presiona Enter para comenzar a hablar...")
        with sr.Microphone() as source:
            print("Escuchando...")
            audio = self.recognizer.listen(source)
            try:
                text = self.recognizer.recognize_google(audio, language="es-ES")
                print(f"Usuario: {text}")
                return text
            except sr.UnknownValueError:
                print("No se pudo entender el audio")
                return ""
            except sr.RequestError as e:
                print(f"Error en el servicio de reconocimiento de voz; {e}")
                return ""

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
        try:
            if self.stop_speaking:
                return
                
            audio = client.generate(
                text=text,
                voice=self.voice,
                model="eleven_multilingual_v2"
            )
            play(audio)
        except Exception as e:
            print(f"Error al generar voz: {str(e)}")

    async def speak(self, text: str):
        """Habla el texto dividido en fragmentos para una respuesta más rápida"""
        print(f"Jarvis: {text}")
        
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
                
                Tienes acceso a los siguientes módulos y funciones:
                
                1. Módulos:
                   - os: listdir, getcwd, mkdir, makedirs, remove, rmdir, rename, path, environ, getenv, chdir, walk
                   - subprocess: run, Popen, PIPE, STDOUT, call, check_output
                   - glob: todas las funciones
                   - re: todas las funciones
                   - time: sleep, time, ctime, strftime, localtime
                   - shutil: copy, copy2, copytree, move, rmtree
                   - psutil: process_iter, cpu_percent, virtual_memory, disk_usage, net_io_counters, sensors_temperatures
                
                2. Funciones integradas de Python:
                   - print, input, open, str, int, float, bool, list, dict, set, tuple
                   - len, range, enumerate, zip, map, filter, sorted, sum, min, max, abs, round
                   - any, all, dir, getattr, hasattr, isinstance, issubclass, type, id, help
                
                Ejemplos de código que puedes generar:
                
                1. Para crear un archivo de texto:
                CODIGO:
                ruta = os.path.join(os.path.expanduser("~"), "Desktop", "archivo.txt")
                with open(ruta, "w", encoding="utf-8") as f:
                    f.write("Contenido del archivo")
                print(f"Archivo creado en: {ruta}")
                
                2. Para buscar y abrir un archivo:
                CODIGO:
                patron = "documento"
                ubicaciones = [
                    os.path.join(os.path.expanduser("~"), "Desktop"),
                    os.path.join(os.path.expanduser("~"), "Documents")
                ]
                archivos_encontrados = []
                for ubicacion in ubicaciones:
                    patron_busqueda = os.path.join(ubicacion, f"*{patron}*")
                    archivos_encontrados.extend(glob.glob(patron_busqueda))
                
                for archivo in archivos_encontrados:
                    print(archivo)
                
                if archivos_encontrados:
                    # Abrir el primer archivo encontrado
                    subprocess.Popen(["start", "", archivos_encontrados[0]], shell=True)
                    print(f"Abriendo: {archivos_encontrados[0]}")
                else:
                    print("No se encontraron archivos")
                
                3. Para obtener información del sistema:
                CODIGO:
                cpu = psutil.cpu_percent(interval=1)
                memoria = psutil.virtual_memory()
                disco = psutil.disk_usage('/')
                
                print(f"Uso de CPU: {cpu}%")
                print(f"Memoria total: {memoria.total / (1024**3):.2f} GB")
                print(f"Memoria disponible: {memoria.available / (1024**3):.2f} GB")
                print(f"Uso de disco: {disco.percent}%")
                
                4. Para ejecutar un comando del sistema:
                CODIGO:
                resultado = subprocess.run("dir", shell=True, capture_output=True, text=True)
                print(resultado.stdout)
                
                5. Para listar procesos en ejecución:
                CODIGO:
                procesos = [p.name() for p in psutil.process_iter()]
                for proceso in sorted(procesos):
                    print(proceso)
                
                RECUERDA: SIEMPRE usa 'CODIGO:' cuando necesites ejecutar una acción en el sistema.
                """}
            ]
            
            messages.extend(self.conversation_history)
            
            response = client1.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            response_text = response.choices[0].message.content
            return response_text
        except Exception as e:
            print(f"Error en la solicitud a OpenAI: {str(e)}")
            return "Hubo un error al obtener la respuesta."

async def main():
    jarvis = JarvisAssistant()
    
    # Configurar la tecla para interrumpir la voz (Escape)
    keyboard.add_hotkey('esc', jarvis.interrupt_speech)
    
    await jarvis.speak("Hola, soy JARVIS. Presiona Enter cuando quieras hablar conmigo. Presiona ESC para interrumpir mi voz.")

    while True:
        command = await jarvis.listen()
        if not command:
            continue
        if "adiós" in command.lower():
            await jarvis.speak("Hasta luego, señor. Estaré aquí si me necesita.")
            break
        await jarvis.process_command(command)

if __name__ == "__main__":
    asyncio.run(main())


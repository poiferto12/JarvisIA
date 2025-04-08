#!/usr/bin/env python3
"""
JARVIS - Asistente Virtual con Memoria Mejorada
Este programa implementa un asistente virtual con capacidad para recordar
resultados de comandos anteriores y usar esa información en comandos subsecuentes.
"""

import asyncio
import json
import logging
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
import traceback
from collections import deque
from typing import Any, Dict, List, Optional, Tuple, Union

import psutil
import yaml
import os.path
from dotenv import load_dotenv
from pathlib import Path

# Inicializar colorama para que los colores funcionen en Windows
from colorama import init, Fore, Style
init(autoreset=True)  # Esto arregla los colores en PowerShell

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración del logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Definir el sistema operativo
SISTEMA_OPERATIVO = platform.system()

# Verificar si OpenAI está disponible
OPENAI_DISPONIBLE = os.getenv("OPENAI_API_KEY") is not None

# Definir el número máximo de mensajes en el historial de conversación
MAX_HISTORIAL = 10

# Definir la ruta de la configuración por defecto
DEFAULT_CONFIG_PATH = "config.yaml"

# Intentar importar chromadb, pero no fallar si no está disponible
try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMADB_DISPONIBLE = True
except ImportError:
    CHROMADB_DISPONIBLE = False
    logger.warning("ChromaDB no está disponible. La búsqueda semántica estará desactivada.")

# Definir la ruta de la base de datos ChromaDB
CHROMA_DB_DIR = "chroma_db"

# Plantillas de código predefinidas
PLANTILLAS = {
    "crear_archivo": """
from pathlib import Path
import os

def crear_archivo(nombre_archivo, ubicacion="escritorio"):
    try:
        # Determinar la ubicación
        if ubicacion.lower() == "escritorio":
            ruta_base = obtener_escritorio()
        elif ubicacion.lower() == "documentos":
            ruta_base = obtener_documentos()
        elif ubicacion.lower() == "descargas":
            ruta_base = obtener_descargas()
        else:
            ruta_base = ubicacion
            
        # Crear la ruta completa
        ruta_archivo = os.path.join(ruta_base, nombre_archivo)
        
        # Crear el archivo
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write("")
            
        print(f"✅ Archivo '{nombre_archivo}' creado en {ruta_base}")
        return ruta_archivo
    except Exception as e:
        print(f"❌ Error al crear el archivo: {e}")
        return None

# Ejecutar la función
ruta = crear_archivo("{nombre_archivo}", "{ubicacion}")
""",
    "crear_y_abrir_archivo": """
from pathlib import Path
import os

def crear_y_abrir_archivo(nombre_archivo, ubicacion="escritorio"):
    try:
        # Determinar la ubicación
        if ubicacion.lower() == "escritorio":
            ruta_base = obtener_escritorio()
        elif ubicacion.lower() == "documentos":
            ruta_base = obtener_documentos()
        elif ubicacion.lower() == "descargas":
            ruta_base = obtener_descargas()
        else:
            ruta_base = ubicacion
            
        # Crear la ruta completa
        ruta_archivo = os.path.join(ruta_base, nombre_archivo)
        
        # Crear el archivo
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write("")
            
        print(f"✅ Archivo '{nombre_archivo}' creado en {ruta_base}")
        
        # Abrir el archivo
        resultado = abrir_archivo(ruta_archivo)
        print(resultado)
        
        return ruta_archivo
    except Exception as e:
        print(f"❌ Error al crear o abrir el archivo: {e}")
        return None

# Ejecutar la función
ruta = crear_y_abrir_archivo("{nombre_archivo}", "{ubicacion}")
""",
    "buscar_archivos": """
import os
import glob
from pathlib import Path

def buscar_archivos(patron, ubicacion=None):
    try:
        # Determinar la ubicación de búsqueda
        if ubicacion is None or ubicacion.lower() == "actual":
            ruta_base = os.getcwd()
        elif ubicacion.lower() == "escritorio":
            ruta_base = obtener_escritorio()
        elif ubicacion.lower() == "documentos":
            ruta_base = obtener_documentos()
        elif ubicacion.lower() == "descargas":
            ruta_base = obtener_descargas()
        else:
            ruta_base = ubicacion
        
        # Construir el patrón de búsqueda
        patron_busqueda = os.path.join(ruta_base, f"*{patron}*")
        
        # Buscar archivos
        archivos_encontrados = glob.glob(patron_busqueda)
        
        # Mostrar resultados
        if archivos_encontrados:
            print(f"🔍 Se encontraron {len(archivos_encontrados)} archivos:")
            for i, archivo in enumerate(archivos_encontrados, 1):
                print(f"{i}. {archivo}")
        else:
            print(f"❌ No se encontraron archivos que coincidan con '{patron}' en {ruta_base}")
        
        return archivos_encontrados
    except Exception as e:
        print(f"❌ Error al buscar archivos: {e}")
        return []

# Ejecutar la búsqueda
archivos_encontrados = buscar_archivos("{patron}")
"""
}


class Timer:
    """Context manager para medir el tiempo de ejecución."""

    def __init__(self, name: str):
        self.name = name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time()
        execution_time = end_time - self.start_time
        print(f"Tiempo de {self.name}: {execution_time:.4f} segundos")


class ConfigMenu:
    """
    Clase para manejar el menú de configuración del chatbot.
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Inicializa el menú de configuración.
        
        Args:
            config_path: Ruta al archivo de configuración.
        """
        self.config_path = config_path
        self.config = self.load_config()
        self.colores = {
            "titulo": Fore.CYAN + Style.BRIGHT,
            "opcion": Fore.GREEN,
            "valor": Fore.YELLOW,
            "error": Fore.RED,
            "exito": Fore.GREEN + Style.BRIGHT,
            "reset": Style.RESET_ALL,
        }
        
    def load_config(self) -> Dict[str, Any]:
        """
        Carga la configuración desde un archivo YAML.
        
        Returns:
            Diccionario con la configuración.
        """
        default_config = {
            "modelo_gpt": "gpt-4o",
            "max_tokens": 1000,
            "temperatura": 0.7,
            "permitir_delimitadores": False,
            "modo_interaccion": "texto",
            "vector_db": {"type": "chroma"},
            "mostrar_menu_inicio": True
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                
                # Asegurarse de que todas las claves necesarias estén presentes
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                
                return config
            else:
                return default_config
        except Exception as e:
            print(f"Error al cargar la configuración: {e}")
            return default_config
    
    def save_config(self) -> bool:
        """
        Guarda la configuración en un archivo YAML.
        
        Returns:
            True si se guardó correctamente, False en caso contrario.
        """
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(self.config, f, default_flow_style=False)
            return True
        except Exception as e:
            print(f"Error al guardar la configuración: {e}")
            return False
    
    def display_menu(self) -> None:
        """
        Muestra el menú de configuración.
        """
        print(f"\n{self.colores['titulo']}=== CONFIGURACIÓN DE JARVIS ==={self.colores['reset']}")
        print(f"{self.colores['opcion']}1. Modelo GPT:{self.colores['reset']} {self.colores['valor']}{self.config['modelo_gpt']}{self.colores['reset']}")
        print(f"{self.colores['opcion']}2. Temperatura:{self.colores['reset']} {self.colores['valor']}{self.config['temperatura']}{self.colores['reset']}")
        print(f"{self.colores['opcion']}3. Máximo de tokens:{self.colores['reset']} {self.colores['valor']}{self.config['max_tokens']}{self.colores['reset']}")
        print(f"{self.colores['opcion']}4. Permitir delimitadores de código:{self.colores['reset']} {self.colores['valor']}{self.config['permitir_delimitadores']}{self.colores['reset']}")
        print(f"{self.colores['opcion']}5. Modo de interacción:{self.colores['reset']} {self.colores['valor']}{self.config['modo_interaccion']}{self.colores['reset']}")
        print(f"{self.colores['opcion']}6. Mostrar este menú al inicio:{self.colores['reset']} {self.colores['valor']}{self.config['mostrar_menu_inicio']}{self.colores['reset']}")
        print(f"{self.colores['opcion']}7. Guardar y salir{self.colores['reset']}")
        print(f"{self.colores['opcion']}8. Salir sin guardar{self.colores['reset']}")
    
    def run(self) -> Dict[str, Any]:
        """
        Ejecuta el menú de configuración.
        
        Returns:
            Diccionario con la configuración actualizada.
        """
        while True:
            self.display_menu()
            
            try:
                choice = input(f"\n{self.colores['opcion']}Selecciona una opción (1-8): {self.colores['reset']}")
                
                if choice == "1":
                    models = ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
                    print(f"\n{self.colores['titulo']}Modelos disponibles:{self.colores['reset']}")
                    for i, model in enumerate(models, 1):
                        print(f"{self.colores['opcion']}{i}. {model}{self.colores['reset']}")
                    
                    model_choice = input(f"\n{self.colores['opcion']}Selecciona un modelo (1-{len(models)}): {self.colores['reset']}")
                    try:
                        model_index = int(model_choice) - 1
                        if 0 <= model_index < len(models):
                            self.config["modelo_gpt"] = models[model_index]
                            print(f"{self.colores['exito']}Modelo actualizado a {models[model_index]}{self.colores['reset']}")
                        else:
                            print(f"{self.colores['error']}Opción inválida{self.colores['reset']}")
                    except ValueError:
                        print(f"{self.colores['error']}Por favor, introduce un número{self.colores['reset']}")
                
                elif choice == "2":
                    temp = input(f"{self.colores['opcion']}Introduce la temperatura (0.0-1.0): {self.colores['reset']}")
                    try:
                        temp_value = float(temp)
                        if 0.0 <= temp_value <= 1.0:
                            self.config["temperatura"] = temp_value
                            print(f"{self.colores['exito']}Temperatura actualizada a {temp_value}{self.colores['reset']}")
                        else:
                            print(f"{self.colores['error']}La temperatura debe estar entre 0.0 y 1.0{self.colores['reset']}")
                    except ValueError:
                        print(f"{self.colores['error']}Por favor, introduce un número válido{self.colores['reset']}")
                
                elif choice == "3":
                    tokens = input(f"{self.colores['opcion']}Introduce el máximo de tokens (100-4000): {self.colores['reset']}")
                    try:
                        tokens_value = int(tokens)
                        if 100 <= tokens_value <= 4000:
                            self.config["max_tokens"] = tokens_value
                            print(f"{self.colores['exito']}Máximo de tokens actualizado a {tokens_value}{self.colores['reset']}")
                        else:
                            print(f"{self.colores['error']}El máximo de tokens debe estar entre 100 y 4000{self.colores['reset']}")
                    except ValueError:
                        print(f"{self.colores['error']}Por favor, introduce un número entero{self.colores['reset']}")
                
                elif choice == "4":
                    delimiters = input(f"{self.colores['opcion']}¿Permitir delimitadores de código? (s/n): {self.colores['reset']}")
                    if delimiters.lower() in ["s", "si", "sí", "y", "yes"]:
                        self.config["permitir_delimitadores"] = True
                        print(f"{self.colores['exito']}Delimitadores de código permitidos{self.colores['reset']}")
                    elif delimiters.lower() in ["n", "no"]:
                        self.config["permitir_delimitadores"] = False
                        print(f"{self.colores['exito']}Delimitadores de código no permitidos{self.colores['reset']}")
                    else:
                        print(f"{self.colores['error']}Opción inválida{self.colores['reset']}")
                
                elif choice == "5":
                    modes = ["texto", "audio"]
                    print(f"\n{self.colores['titulo']}Modos disponibles:{self.colores['reset']}")
                    for i, mode in enumerate(modes, 1):
                        print(f"{self.colores['opcion']}{i}. {mode}{self.colores['reset']}")
                    
                    mode_choice = input(f"\n{self.colores['opcion']}Selecciona un modo (1-{len(modes)}): {self.colores['reset']}")
                    try:
                        mode_index = int(mode_choice) - 1
                        if 0 <= mode_index < len(modes):
                            self.config["modo_interaccion"] = modes[mode_index]
                            print(f"{self.colores['exito']}Modo actualizado a {modes[mode_index]}{self.colores['reset']}")
                            if modes[mode_index] == "audio":
                                print(f"{self.colores['error']}Nota: El modo de audio aún no está completamente implementado{self.colores['reset']}")
                        else:
                            print(f"{self.colores['error']}Opción inválida{self.colores['reset']}")
                    except ValueError:
                        print(f"{self.colores['error']}Por favor, introduce un número{self.colores['reset']}")
                
                elif choice == "6":
                    show_menu = input(f"{self.colores['opcion']}¿Mostrar este menú al inicio? (s/n): {self.colores['reset']}")
                    if show_menu.lower() in ["s", "si", "sí", "y", "yes"]:
                        self.config["mostrar_menu_inicio"] = True
                        print(f"{self.colores['exito']}El menú se mostrará al inicio{self.colores['reset']}")
                    elif show_menu.lower() in ["n", "no"]:
                        self.config["mostrar_menu_inicio"] = False
                        print(f"{self.colores['exito']}El menú no se mostrará al inicio{self.colores['reset']}")
                    else:
                        print(f"{self.colores['error']}Opción inválida{self.colores['reset']}")
                
                elif choice == "7":
                    if self.save_config():
                        print(f"{self.colores['exito']}Configuración guardada correctamente{self.colores['reset']}")
                    else:
                        print(f"{self.colores['error']}Error al guardar la configuración{self.colores['reset']}")
                    return self.config
                
                elif choice == "8":
                    print(f"{self.colores['titulo']}Saliendo sin guardar{self.colores['reset']}")
                    return self.config
                
                else:
                    print(f"{self.colores['error']}Opción inválida{self.colores['reset']}")
            
            except KeyboardInterrupt:
                print(f"\n{self.colores['titulo']}Saliendo sin guardar{self.colores['reset']}")
                return self.config


class JarvisMemory:
    """
    Clase para gestionar la memoria mejorada de JARVIS.
    Permite recordar resultados de comandos y hacer referencias a ellos.
    """

    def __init__(self, memory_file: str = None, max_memory_items: int = 100):
        """
        Inicializa el sistema de memoria para JARVIS
        
        Args:
            memory_file: Ruta al archivo de almacenamiento de memoria
            max_memory_items: Número máximo de elementos de memoria a almacenar
        """
        self.memory_file = memory_file or os.path.join(os.path.expanduser("~"), "jarvis_memory.json")
        self.max_memory_items = max_memory_items
        self.memory_data = {
            "conversations": [],
            "file_interactions": {},
            "command_history": [],
            "context_links": {},
            "last_updated": time.time()
        }
        
        # Memoria a corto plazo para resultados de comandos
        self.command_results = {}
        
        # Memoria específica para archivos encontrados
        self.found_files = []
        
        # Memoria para la última operación
        self.last_operation = {
            "type": None,  # Tipo de operación (buscar_archivos, leer_archivo, etc.)
            "result": None,  # Resultado de la operación
            "timestamp": None  # Momento en que se realizó
        }
        
        # Historial de resultados para incluir en el contexto
        self.results_history = []
        
        self.load_memory()
        
        # Inicializar ChromaDB si está disponible
        self.collection = None
        if CHROMADB_DISPONIBLE:
            try:
                self.init_chromadb()
            except Exception as e:
                logger.error(f"Error al inicializar ChromaDB: {e}")
    
    def init_chromadb(self):
        """Inicializa ChromaDB si está disponible"""
        if not CHROMADB_DISPONIBLE or not OPENAI_DISPONIBLE:
            return
            
        try:
            chroma_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.environ["OPENAI_API_KEY"], model_name="text-embedding-ada-002"
            )
            self.client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
            self.collection = self.client.get_or_create_collection(
                name="conversation_memory", embedding_function=chroma_ef
            )
            logger.info("ChromaDB inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar ChromaDB: {e}")
            self.collection = None
    
    def load_memory(self) -> bool:
        """Carga la memoria desde el archivo de almacenamiento"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memory_data = data
                logger.info(f"Memoria cargada desde {self.memory_file}")
                return True
            logger.info("No se encontró archivo de memoria, comenzando con memoria vacía")
            return False
        except Exception as e:
            logger.error(f"Error al cargar la memoria: {e}")
            return False
    
    def save_memory(self) -> bool:
        """Guarda la memoria en el archivo de almacenamiento"""
        try:
            # Asegurar que el directorio existe
            os.makedirs(os.path.dirname(os.path.abspath(self.memory_file)), exist_ok=True)
            
            # Actualizar timestamp
            self.memory_data["last_updated"] = time.time()
            
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory_data, f, indent=4)
            logger.debug(f"Memoria guardada en {self.memory_file}")
            return True
        except Exception as e:
            logger.error(f"Error al guardar la memoria: {e}")
            return False
    
    def add_conversation(self, user_input: str, assistant_response: str, 
                         executed_code: Optional[str] = None, 
                         code_result: Optional[str] = None) -> str:
        """
        Añade un intercambio de conversación a la memoria
        
        Returns:
            conversation_id: ID único para esta conversación
        """
        conversation_id = f"conv_{int(time.time())}_{len(self.memory_data['conversations'])}"
        
        conversation = {
            "id": conversation_id,
            "timestamp": time.time(),
            "user_input": user_input,
            "assistant_response": assistant_response,
            "executed_code": executed_code,
            "code_result": code_result,
            "related_files": [],
            "related_conversations": []
        }
        
        # Añadir a la memoria y mantener el límite de tamaño
        self.memory_data["conversations"].insert(0, conversation)
        if len(self.memory_data["conversations"]) > self.max_memory_items:
            self.memory_data["conversations"] = self.memory_data["conversations"][:self.max_memory_items]
        
        # Guardar en ChromaDB si está disponible
        if self.collection is not None:
            try:
                text = f"Usuario: {user_input}\nJARVIS: {assistant_response}"
                if code_result:
                    text += f"\nResultado: {code_result}"
                
                self.collection.add(
                    documents=[text],
                    ids=[conversation_id],
                    metadatas=[{"conversation_id": conversation_id}]
                )
            except Exception as e:
                logger.error(f"Error al guardar en ChromaDB: {e}")
        
        # Añadir al historial de resultados para contexto
        if code_result:
            self.results_history.append({
                "query": user_input,
                "result": code_result,
                "timestamp": time.time()
            })
            # Mantener solo los últimos 5 resultados
            if len(self.results_history) > 5:
                self.results_history = self.results_history[-5:]
        
        self.save_memory()
        logger.info(f"Añadida conversación con ID: {conversation_id}")
        return conversation_id
    
    def add_file_interaction(self, file_path: str, action: str, 
                             conversation_id: Optional[str] = None) -> None:
        """Registra una interacción con un archivo"""
        abs_path = os.path.abspath(os.path.expanduser(file_path))
        
        if abs_path not in self.memory_data["file_interactions"]:
            self.memory_data["file_interactions"][abs_path] = []
        
        interaction = {
            "timestamp": time.time(),
            "action": action,
            "conversation_id": conversation_id
        }
        
        self.memory_data["file_interactions"][abs_path].insert(0, interaction)
        
        # Si está vinculado a una conversación, actualizar también la conversación
        if conversation_id:
            for conv in self.memory_data["conversations"]:
                if conv["id"] == conversation_id:
                    if abs_path not in conv["related_files"]:
                        conv["related_files"].append(abs_path)
                    break
        
        self.save_memory()
        logger.debug(f"Añadida interacción con archivo: {action} en {abs_path}")
    
    def add_command(self, command: str, result: str, 
                    conversation_id: Optional[str] = None) -> None:
        """Registra la ejecución de un comando"""
        command_record = {
            "timestamp": time.time(),
            "command": command,
            "result": result,
            "conversation_id": conversation_id
        }
        
        self.memory_data["command_history"].insert(0, command_record)
        if len(self.memory_data["command_history"]) > self.max_memory_items:
            self.memory_data["command_history"] = self.memory_data["command_history"][:self.max_memory_items]
        
        self.save_memory()
        logger.debug(f"Añadido comando al historial: {command}")
    
    def link_conversations(self, source_id: str, target_id: str, 
                           relation_type: str = "follow-up") -> bool:
        """Crea un enlace entre dos conversaciones"""
        source_found = False
        target_found = False
        
        for conv in self.memory_data["conversations"]:
            if conv["id"] == source_id:
                if target_id not in [rel["id"] for rel in conv["related_conversations"]]:
                    conv["related_conversations"].append({
                        "id": target_id,
                        "relation": relation_type
                    })
                source_found = True
            
            if conv["id"] == target_id:
                target_found = True
        
        if source_found and target_found:
            self.save_memory()
            logger.info(f"Conversaciones enlazadas: {source_id} -> {target_id} ({relation_type})")
            return True
        
        logger.warning(f"No se pudieron enlazar las conversaciones: {source_id} -> {target_id}")
        return False
    
    def get_conversation_by_id(self, conversation_id: str) -> Optional[Dict]:
        """Recupera una conversación específica por ID"""
        for conv in self.memory_data["conversations"]:
            if conv["id"] == conversation_id:
                return conv
        return None
    
    def get_recent_conversations(self, count: int = 5) -> List[Dict]:
        """Obtiene las conversaciones más recientes"""
        return self.memory_data["conversations"][:count]
    
    def get_file_history(self, file_path: str) -> List[Dict]:
        """Obtiene el historial de interacciones para un archivo específico"""
        abs_path = os.path.abspath(os.path.expanduser(file_path))
        return self.memory_data["file_interactions"].get(abs_path, [])
    
    def search_conversations(self, query: str) -> List[Dict]:
        """Busca conversaciones para una consulta específica"""
        # Si ChromaDB está disponible, usar búsqueda semántica
        if self.collection is not None:
            try:
                results = self.collection.query(query_texts=[query], n_results=5)
                conversation_ids = [meta["conversation_id"] for meta in results["metadatas"][0]] if results["metadatas"] else []
                
                if conversation_ids:
                    return [conv for conv in self.memory_data["conversations"] if conv["id"] in conversation_ids]
            except Exception as e:
                logger.error(f"Error en búsqueda semántica: {e}")
        
        # Búsqueda por palabras clave como respaldo
        results = []
        for conv in self.memory_data["conversations"]:
            if (query.lower() in conv["user_input"].lower() or 
                query.lower() in conv["assistant_response"].lower()):
                results.append(conv)
        return results
    
    def get_related_context(self, query: str, max_items: int = 3) -> Dict[str, Any]:
        """
        Obtiene contexto relacionado para una nueva consulta basado en interacciones previas
        
        Returns un diccionario con información de contexto relevante
        """
        context = {
            "related_conversations": [],
            "related_files": [],
            "related_commands": [],
            "recent_results": self.results_history  # Incluir automáticamente el historial de resultados
        }
        
        # Encontrar conversaciones relacionadas
        related_convs = self.search_conversations(query)
        context["related_conversations"] = related_convs[:max_items]
        
        # Encontrar archivos relacionados
        mentioned_files = []
        for word in query.split():
            if os.path.exists(word):
                mentioned_files.append(os.path.abspath(word))
        
        for file_path in mentioned_files:
            if file_path in self.memory_data["file_interactions"]:
                context["related_files"].append({
                    "path": file_path,
                    "interactions": self.memory_data["file_interactions"][file_path][:max_items]
                })
        
        # Encontrar comandos relacionados
        for cmd in self.memory_data["command_history"]:
            if query.lower() in cmd["command"].lower():
                context["related_commands"].append(cmd)
                if len(context["related_commands"]) >= max_items:
                    break
        
        logger.debug(f"Encontrado contexto relacionado: {len(context['related_conversations'])} conversaciones, "
                    f"{len(context['related_files'])} archivos, {len(context['related_commands'])} comandos")
        return context
    
    def clear_memory(self) -> bool:
        """Limpia todos los datos de memoria"""
        self.memory_data = {
            "conversations": [],
            "file_interactions": {},
            "command_history": [],
            "context_links": {},
            "last_updated": time.time()
        }
        
        # También limpiar la memoria a corto plazo
        self.command_results = {}
        self.found_files = []
        self.last_operation = {
            "type": None,
            "result": None,
            "timestamp": None
        }
        self.results_history = []
        
        # Limpiar ChromaDB si está disponible
        if self.collection is not None:
            try:
                self.collection.delete(where={})
            except Exception as e:
                logger.error(f"Error al limpiar ChromaDB: {e}")
        
        logger.info("Memoria limpiada")
        return self.save_memory()
    
    def extract_file_references(self, code: str) -> List[Tuple[str, str]]:
        """
        Extrae referencias a archivos del código con sus probables acciones
        Devuelve una lista de tuplas (ruta_archivo, acción)
        """
        file_refs = []
        
        # Patrón para llamadas a open()
        open_pattern = r'open\([\'"]([^\'"]+)[\'"](?:,\s*[\'"]([^\'"]+)[\'"])?'
        for match in re.finditer(open_pattern, code):
            file_path = match.group(1)
            mode = match.group(2) if match.group(2) else 'r'
            
            action = 'read'
            if 'w' in mode or 'a' in mode:
                action = 'write'
            
            file_refs.append((file_path, action))
        
        # Patrón para operaciones de Path
        path_pattern = r'Path$[\'"]([^\'"]+)[\'"]$\.(?:write_text|write_bytes|open)'
        for match in re.finditer(path_pattern, code):
            file_path = match.group(1)
            file_refs.append((file_path, 'write'))
        
        # Patrón para operaciones de os.path
        os_pattern = r'os\.(?:rename|makedirs|mkdir)$[\'"]([^\'"]+)[\'"]$'
        for match in re.finditer(os_pattern, code):
            file_path = match.group(1)
            file_refs.append((file_path, 'modify'))
        
        return file_refs
    
    def format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """Formatea la información de contexto para incluirla en un prompt"""
        prompt_parts = []
        
        # Incluir resultados recientes automáticamente
        if context["recent_results"]:
            prompt_parts.append("Resultados recientes de comandos:")
            for i, result in enumerate(context["recent_results"], 1):
                time_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(result["timestamp"]))
                prompt_parts.append(f"{i}. {time_str} - Consulta: {result['query']}")
                result_text = str(result["result"])
                if len(result_text) > 150:
                    result_text = result_text[:150] + "..."
                prompt_parts.append(f"   Resultado: {result_text}")
            prompt_parts.append("")  # Línea vacía
        
        if context["related_conversations"]:
            prompt_parts.append("Conversaciones previas relevantes:")
            for i, conv in enumerate(context["related_conversations"], 1):
                time_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(conv["timestamp"]))
                prompt_parts.append(f"{i}. {time_str}")
                prompt_parts.append(f"   Tú: {conv['user_input']}")
                prompt_parts.append(f"   JARVIS: {conv['assistant_response']}")
                if conv.get("code_result"):
                    result_text = str(conv["code_result"])
                    if len(result_text) > 100:
                        result_text = result_text[:100] + "..."
                    prompt_parts.append(f"   Resultado: {result_text}")
                if i < len(context["related_conversations"]):
                    prompt_parts.append("")  # Línea vacía entre conversaciones
        
        if context["related_files"]:
            if prompt_parts:
                prompt_parts.append("")  # Línea vacía antes de nueva sección
            prompt_parts.append("Archivos relevantes:")
            for file_info in context["related_files"]:
                file_path = file_info["path"]
                interactions = file_info["interactions"]
                last_action = interactions[0]["action"] if interactions else "desconocido"
                time_str = time.strftime("%Y-%m-%d %H:%M", 
                                        time.localtime(interactions[0]["timestamp"])) if interactions else "desconocido"
                prompt_parts.append(f"- {file_path} (Última acción: {last_action} a las {time_str})")
        
        if context["related_commands"]:
            if prompt_parts:
                prompt_parts.append("")  # Línea vacía antes de nueva sección
            prompt_parts.append("Comandos relevantes recientes:")
            for cmd in context["related_commands"]:
                time_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(cmd["timestamp"]))
                prompt_parts.append(f"- {time_str}: {cmd['command']}")
                if cmd["result"]:
                    # Truncar resultados largos
                    result = cmd["result"]
                    if len(result) > 100:
                        result = result[:100] + "..."
                    prompt_parts.append(f"  Resultado: {result}")
        
        return "\n".join(prompt_parts)
    
    # Métodos para la memoria a corto plazo
    
    def store_command_result(self, command_type: str, result: Any) -> None:
        """
        Almacena el resultado de un comando para referencia futura
        
        Args:
            command_type: Tipo de comando (buscar_archivos, leer_archivo, etc.)
            result: Resultado del comando
        """
        self.command_results[command_type] = result
        
        # Actualizar la última operación
        self.last_operation = {
            "type": command_type,
            "result": result,
            "timestamp": time.time()
        }
        
        # Si es una búsqueda de archivos, almacenar los archivos encontrados
        if command_type == "buscar_archivos" and isinstance(result, list):
            self.found_files = result
            logger.debug(f"Almacenados {len(result)} archivos encontrados en memoria")
        
        logger.debug(f"Almacenado resultado de comando para {command_type}")
    
    def get_command_result(self, command_type: str) -> Any:
        """
        Recupera el resultado de un comando previo
        
        Args:
            command_type: Tipo de comando (buscar_archivos, leer_archivo, etc.)
            
        Returns:
            El resultado almacenado o None si no existe
        """
        return self.command_results.get(command_type)
    
    def get_last_operation(self) -> Dict[str, Any]:
        """
        Recupera información sobre la última operación realizada
        
        Returns:
            Diccionario con información de la última operación
        """
        return self.last_operation
    
    def get_file_by_reference(self, reference: str) -> Optional[str]:
        """
        Obtiene la ruta de un archivo basado en una referencia como "el primero", "el segundo", etc.
        
        Args:
            reference: Referencia al archivo ("el primero", "el segundo", "el último", etc.)
            
        Returns:
            Ruta del archivo o None si no se encuentra
        """
        if not self.found_files:
            return None
        
        reference = reference.lower()
        
        # Manejar referencias numéricas
        if "primer" in reference or "primero" in reference or "1" in reference:
            return self.found_files[0] if self.found_files else None
        elif "segundo" in reference or "2" in reference:
            return self.found_files[1] if len(self.found_files) > 1 else None
        elif "tercer" in reference or "tercero" in reference or "3" in reference:
            return self.found_files[2] if len(self.found_files) > 2 else None
        elif "cuarto" in reference or "4" in reference:
            return self.found_files[3] if len(self.found_files) > 3 else None
        elif "quinto" in reference or "5" in reference:
            return self.found_files[4] if len(self.found_files) > 4 else None
        elif "último" in reference or "ultima" in reference:
            return self.found_files[-1] if self.found_files else None
        
        # Intentar extraer un número
        match = re.search(r'(\d+)', reference)
        if match:
            index = int(match.group(1)) - 1  # Convertir a índice base 0
            if 0 <= index < len(self.found_files):
                return self.found_files[index]
        
        return None
    
    def extract_file_reference_from_query(self, query: str) -> Optional[str]:
        """
        Extrae una referencia a un archivo de una consulta
        
        Args:
            query: Consulta del usuario
            
        Returns:
            Referencia extraída o None si no se encuentra
        """
        # Patrones para detectar referencias a archivos
        patterns = [
            r'(?:el|la|los|las) (primer[oa]?|segund[oa]?|tercer[oa]?|cuart[oa]?|quint[oa]?|últim[oa]?)',
            r'(?:el|la|los|las) (?:archivo|documento|fichero) (?:número)? (\d+)',
            r'(?:el|la|los|las) (\d+)(?:º|°)?',
            r'número (\d+)',
            r'archivo (\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                return match.group(1)
        
        return None


class Chatbot:
    """
    Clase principal para el chatbot.
    """

    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        """
        Inicializa el chatbot.

        Args:
            config_path: Ruta al archivo de configuración.
        """
        self.load_config(config_path)
        self.colores = {
            "principal": Fore.GREEN,  # Verde claro
            "secundario": Fore.BLUE,  # Azul claro
            "terciario": Fore.YELLOW,  # Amarillo
            "aviso": Fore.RED,  # Rojo claro
            "error": Fore.RED + Style.BRIGHT,  # Rojo brillante
            "reset": Style.RESET_ALL,  # Resetear color
        }
        self.conversation_history = deque(maxlen=MAX_HISTORIAL)
        self.memory = JarvisMemory()
        self.current_conversation_id = None
        self.safe_environment = {
            "__builtins__": {
                "print": print,
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
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                "open": open,
                "__import__": __import__,
            },
            "os": os,
            "subprocess": subprocess,
            "glob": __import__("glob"),
            "re": re,
            "time": time,
            "shutil": __import__("shutil"),
            "psutil": psutil,
            "platform": platform,
            "Path": Path,
            "archivos_encontrados": [],
            "abrir_archivo": self.abrir_archivo,
            "obtener_archivo": self.obtener_archivo,
            "obtener_escritorio": self.obtener_escritorio,
            "obtener_documentos": self.obtener_documentos,
            "obtener_descargas": self.obtener_descargas,
            "ejecutar_comando": self.ejecutar_comando,
        }
        if OPENAI_DISPONIBLE:
            from openai import OpenAI

            self.client_openai = OpenAI()
        else:
            self.client_openai = None
            logger.warning("OpenAI API key no encontrada. No se podrán generar respuestas.")

    def load_config(self, config_path: str) -> None:
        """
        Carga la configuración desde un archivo YAML o desde el menú de configuración.

        Args:
            config_path: Ruta al archivo de configuración.
        """
        config_menu = ConfigMenu(config_path)
        self.config = config_menu.config
        
        # Mostrar el menú de configuración si está habilitado
        if self.config.get("mostrar_menu_inicio", True):
            self.config = config_menu.run()
        
        logger.info("Configuración cargada")

    def timer(self, name: str):
        """
        Crea un objeto Timer para medir el tiempo de ejecución.

        Args:
            name: Nombre del temporizador.

        Returns:
            Objeto Timer.
        """
        return Timer(name)

    async def speak(self, text: str) -> None:
        """
        Simula el habla del chatbot imprimiendo el texto.

        Args:
            text: Texto a imprimir.
        """
        print(f"{self.colores['principal']}JARVIS: {text}{self.colores['reset']}")

    def extract_code(self, text: str) -> str:
        """
        Extrae el código de un texto.

        Args:
            text: Texto del cual extraer el código.

        Returns:
            Código extraído.
        """
        # Buscar bloques de código delimitados por \`\`\`python y \`\`\`
        match = re.search(r"\`\`\`(?:python)?\n([\s\S]*?)\n\`\`\`", text)
        if match:
            return match.group(1).strip()

        # Si no hay delimitadores, buscar líneas que empiecen con "CODIGO:"
        lines = text.splitlines()
        for line in lines:
            if line.startswith("CODIGO:"):
                return line[len("CODIGO:") :].strip()

        # Si no se encuentra nada, devolver el texto original
        return text.strip()

    def contains_code_delimiters(self, text: str) -> bool:
        """
        Verifica si un texto contiene delimitadores de código.

        Args:
            text: Texto a verificar.

        Returns:
            True si el texto contiene delimitadores de código, False en caso contrario.
        """
        return "\`\`\`python" in text or "\`\`\`" in text

    def validate_code(self, code: str) -> Tuple[bool, str]:
        """
        Valida el código antes de ejecutarlo.

        Args:
            code: Código a validar.

        Returns:
            Una tupla con un booleano indicando si el código es válido y un mensaje de error en caso de que no lo sea.
        """
        # Verificar si el código está vacío
        if not code or not code.strip():
            return False, "El código está vacío."

        # Verificar si el código contiene llamadas a funciones no permitidas
        if "input(" in code:
            return False, "El código contiene llamadas a la función 'input', que no está permitida."

        # Verificar si el código contiene operaciones de red no permitidas
        if "socket." in code:
            return False, "El código contiene operaciones de red, que no están permitidas."
        if "urllib." in code:
            return False, "El código contiene operaciones de red, que no están permitidas."
        if "requests." in code:
            return False, "El código contiene operaciones de red, que no están permitidas."

        # Verificar si el código contiene operaciones de eliminación de archivos
        if "os.remove" in code or "os.unlink" in code or "shutil.rmtree" in code:
            return False, "El código contiene operaciones de eliminación de archivos, que no están permitidas por seguridad."
    
        # Verificar si hay patrones peligrosos de eliminación
        dangerous_patterns = [
            r'rm\s+-rf',  # rm -rf en comandos shell
            r'del\s+/[QSF]',  # del /Q o similares en Windows
            r'rmdir\s+/[QS]',  # rmdir /Q o similares en Windows
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, code):
                return False, "El código contiene comandos de eliminación de archivos, que no están permitidos por seguridad."

        # Si pasa todas las verificaciones, se considera válido
        return True, ""

    def execute_code(self, code: str) -> Any:
        """
        Ejecuta el código en un entorno seguro.

        Args:
            code: Código a ejecutar.

        Returns:
            El resultado de la ejecución del código.
        """
        try:
            # Crear un entorno seguro para la ejecución del código
            local_vars = {}

            # Ejecutar el código en el entorno seguro
            exec(code, self.safe_environment, local_vars)

            # Buscar la variable __result en el entorno local
            if "__result" in local_vars:
                return local_vars["__result"]
            else:
                return "Código ejecutado sin errores, pero no se encontró un resultado explícito."
        except Exception as e:
            logger.error(f"Error al ejecutar código: {e}")
            print(f"{self.colores['error']}Error al ejecutar código: {str(e)}{self.colores['reset']}")
            error_traceback = traceback.format_exc()
            logger.debug(f"Traceback: {error_traceback}")
            print(error_traceback)
            return f"Error: {str(e)}"

    def abrir_archivo(self, ruta: str) -> str:
        """
        Abre un archivo con la aplicación predeterminada del sistema operativo.

        Args:
            ruta: Ruta del archivo a abrir.

        Returns:
            Un mensaje indicando si el archivo se abrió correctamente o si hubo un error.
        """
        try:
            if SISTEMA_OPERATIVO == "Windows":
                os.startfile(ruta)
            elif SISTEMA_OPERATIVO == "Darwin":
                subprocess.run(["open", ruta])
            else:
                subprocess.run(["xdg-open", ruta])
            return f"Archivo '{ruta}' abierto correctamente."
        except Exception as e:
            logger.error(f"Error al abrir el archivo: {e}")
            return f"Error al abrir el archivo '{ruta}': {str(e)}"

    def obtener_archivo(self, ruta: str) -> str:
        """
        Obtiene la ruta absoluta de un archivo.

        Args:
            ruta: Ruta del archivo.

        Returns:
            La ruta absoluta del archivo.
        """
        return os.path.abspath(ruta)

    def obtener_escritorio(self) -> str:
        """
        Obtiene la ruta al escritorio del usuario.

        Returns:
            La ruta al escritorio del usuario.
        """
        return str(Path.home() / "Desktop")

    def obtener_documentos(self) -> str:
        """
        Obtiene la ruta a la carpeta de documentos del usuario.

        Returns:
            La ruta a la carpeta de documentos del usuario.
        """
        return str(Path.home() / "Documents")

    def obtener_descargas(self) -> str:
        """
        Obtiene la ruta a la carpeta de descargas del usuario.

        Returns:
            La ruta a la carpeta de descargas del usuario.
        """
        return str(Path.home() / "Downloads")

    def ejecutar_comando(self, comando: str) -> str:
        """
        Ejecuta un comando del sistema de forma segura.

        Args:
            comando: Comando a ejecutar.

        Returns:
            La salida del comando.
        """
        try:
            result = subprocess.run(
                comando,
                shell=True,
                capture_output=True,
                text=True,
                check=True,
                cwd=os.getcwd(),
                env=os.environ,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Error al ejecutar el comando: {e}")
            return f"Error: {e.stderr.strip()}"
        except Exception as e:
            logger.error(f"Error inesperado al ejecutar el comando: {e}")
            return f"Error inesperado: {str(e)}"

    def detectar_intencion(self, comando: str) -> Optional[str]:
        """
        Detecta la intención del usuario a partir del comando.

        Args:
            comando: Comando del usuario.

        Returns:
            La intención detectada o None si no se pudo detectar.
        """
        comando = comando.lower()

        # Lista de intenciones y sus palabras clave
        intenciones = {
            "buscar_archivos": ["buscar", "archivos", "encontrar", "listar"],
            "leer_archivo": ["leer", "archivo", "contenido"],
            "crear_archivo": ["crear", "archivo", "nuevo"],
            "crear_y_abrir_archivo": ["crear", "abrir", "archivo"],
            "borrar_archivo": ["borrar", "eliminar", "archivo"],
            "copiar_archivo": ["copiar", "archivo"],
            "mover_archivo": ["mover", "archivo"],
            "renombrar_archivo": ["renombrar", "archivo"],
            "crear_directorio": ["crear", "directorio", "carpeta"],
            "borrar_directorio": ["borrar", "eliminar", "directorio", "carpeta"],
            "obtener_info_sistema": ["información", "sistema", "cpu", "memoria", "disco"],
            "ejecutar_comando": ["ejecutar", "comando"],
            "abrir_pagina_web": ["abrir", "pagina", "web", "navegador"],
        }

        # Buscar la intención que coincida con las palabras clave del comando
        for intencion, palabras_clave in intenciones.items():
            if all(palabra in comando for palabra in palabras_clave):
                return intencion

        # Si no se encontró una coincidencia exacta, buscar la mejor coincidencia parcial
        mejor_intencion = None
        max_coincidencias = 0
        
        for intencion, palabras_clave in intenciones.items():
            coincidencias = sum(1 for palabra in palabras_clave if palabra in comando)
            if coincidencias > max_coincidencias:
                max_coincidencias = coincidencias
                mejor_intencion = intencion
        
        # Solo devolver la intención si hay al menos una coincidencia
        if max_coincidencias > 0:
            return mejor_intencion

        return None

    def extraer_parametros(self, comando: str, intencion: str) -> Dict[str, Any]:
        """
        Extrae los parámetros del comando a partir de la intención detectada.

        Args:
            comando: Comando del usuario.
            intencion: Intención detectada.

        Returns:
            Un diccionario con los parámetros extraídos.
        """
        parametros = {}

        if intencion == "buscar_archivos":
            # Extraer el patrón de búsqueda
            match = re.search(r"buscar archivos con patrón (.*)", comando)
            if match:
                parametros["patron"] = match.group(1).strip()
            else:
                # Intentar extraer cualquier patrón mencionado
                palabras = comando.split()
                for i, palabra in enumerate(palabras):
                    if palabra in ["buscar", "encontrar", "listar"] and i+1 < len(palabras):
                        parametros["patron"] = palabras[i+1]
                        break

        elif intencion == "leer_archivo":
            # Extraer la ruta del archivo
            match = re.search(r"leer archivo (.*)", comando)
            if match:
                parametros["ruta"] = match.group(1).strip()

        elif intencion == "crear_archivo" or intencion == "crear_y_abrir_archivo":
            # Extraer la ruta del archivo
            match = re.search(r"crear archivo (.*?)(?: en (.*))?$", comando)
            if match:
                nombre_archivo = match.group(1).strip()
                ubicacion = match.group(2).strip() if match.group(2) else "escritorio"
                
                parametros["nombre_archivo"] = nombre_archivo
                parametros["ubicacion"] = ubicacion
            else:
                # Buscar cualquier nombre de archivo mencionado
                palabras = comando.split()
                for palabra in palabras:
                    if "." in palabra:
                        parametros["nombre_archivo"] = palabra
                        parametros["ubicacion"] = "escritorio"
                        break

        elif intencion == "borrar_archivo":
            # Extraer la ruta del archivo
            match = re.search(r"borrar archivo (.*)", comando)
            if match:
                parametros["ruta"] = match.group(1).strip()

        elif intencion == "copiar_archivo":
            # Extraer la ruta del archivo origen y destino
            match = re.search(r"copiar archivo (.*) a (.*)", comando)
            if match:
                parametros["origen"] = match.group(1).strip()
                parametros["destino"] = match.group(2).strip()

        elif intencion == "mover_archivo":
            # Extraer la ruta del archivo origen y destino
            match = re.search(r"mover archivo (.*) a (.*)", comando)
            if match:
                parametros["origen"] = match.group(1).strip()
                parametros["destino"] = match.group(2).strip()

        elif intencion == "renombrar_archivo":
            # Extraer la ruta del archivo origen y destino
            match = re.search(r"renombrar archivo (.*) a (.*)", comando)
            if match:
                parametros["origen"] = match.group(1).strip()
                parametros["destino"] = match.group(2).strip()

        elif intencion == "crear_directorio":
            # Extraer la ruta del directorio
            match = re.search(r"crear directorio (.*)", comando)
            if match:
                parametros["ruta"] = match.group(1).strip()

        elif intencion == "borrar_directorio":
            # Extraer la ruta del directorio
            match = re.search(r"borrar directorio (.*)", comando)
            if match:
                parametros["ruta"] = match.group(1).strip()

        elif intencion == "ejecutar_comando":
            # Extraer el comando a ejecutar
            match = re.search(r"ejecutar comando (.*)", comando)
            if match:
                parametros["comando"] = match.group(1).strip()

        elif intencion == "abrir_pagina_web":
            # Extraer la URL de la página web
            match = re.search(r"abrir página web (.*)", comando)
            if match:
                parametros["url"] = match.group(1).strip()

        return parametros

    def generar_codigo_desde_plantilla(self, intencion: str, parametros: Dict[str, Any]) -> Optional[str]:
        """
        Genera el código a partir de una plantilla.

        Args:
            intencion: Intención detectada.
            parametros: Parámetros extraídos.

        Returns:
            El código generado o None si no se pudo generar.
        """
        # Si hay una plantilla predefinida para esta intención, usarla
        if intencion in PLANTILLAS:
            try:
                # Reemplazar los parámetros en la plantilla
                codigo_generado = PLANTILLAS[intencion].format(**parametros)
                return codigo_generado
            except KeyError as e:
                logger.error(f"Falta el parámetro {e} para la plantilla de {intencion}")
                return None
        
        return None

    async def handle_memory_commands(self, command: str) -> bool:
        """
        Maneja los comandos relacionados con la memoria.

        Args:
            command: Comando del usuario.

        Returns:
            True si el comando fue manejado, False en caso contrario.
        """
        command = command.lower()

        if "recordar" in command:
            # Extraer la información a recordar
            match = re.search(r"recordar (.*)", command)
            if match:
                info = match.group(1).strip()
                self.memory.store_command_result("recordar", info)
                await self.speak(f"He recordado: {info}")
                return True

        elif "olvidar" in command:
            # Extraer la información a olvidar
            match = re.search(r"olvidar (.*)", command)
            if match:
                info = match.group(1).strip()
                if "recordar" in self.memory.command_results and self.memory.command_results["recordar"] == info:
                    del self.memory.command_results["recordar"]
                    await self.speak(f"He olvidado: {info}")
                else:
                    await self.speak(f"No recuerdo haber guardado: {info}")
                return True

        elif "mostrar archivos" in command or "listar archivos encontrados" in command:
            # Mostrar los archivos encontrados en la última búsqueda
            if not self.memory.found_files:
                await self.speak("No hay archivos en la memoria. Realiza una búsqueda primero.")
            else:
                resultado = "📄 Archivos encontrados en la última búsqueda:\n"
                for i, archivo in enumerate(self.memory.found_files, 1):
                    resultado += f"{i}. {archivo}\n"
                await self.speak(resultado)
            return True

        elif "última operación" in command or "mostrar última operación" in command:
            # Mostrar información sobre la última operación
            last_op = self.memory.get_last_operation()
            
            if not last_op["type"]:
                await self.speak("No hay operaciones recientes en la memoria.")
            else:
                resultado = f"🔍 Última operación: {last_op['type']}\n"
                
                if last_op["timestamp"]:
                    time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_op["timestamp"]))
                    resultado += f"⏰ Realizada a las: {time_str}\n"
                
                if last_op["result"]:
                    if isinstance(last_op["result"], list):
                        resultado += f"📊 Resultado: Lista con {len(last_op['result'])} elementos\n"
                        if last_op["result"]:
                            resultado += "📌 Primeros elementos:\n"
                            for i, item in enumerate(last_op["result"][:3], 1):
                                resultado += f"  {i}. {item}\n"
                            if len(last_op["result"]) > 3:
                                resultado += f"  ... y {len(last_op['result']) - 3} más\n"
                    else:
                        result_str = str(last_op["result"])
                        if len(result_str) > 200:
                            result_str = result_str[:200] + "..."
                        resultado += f"📝 Resultado: {result_str}\n"
                
                await self.speak(resultado)
            return True

        return False

    async def process_command(self, command: str) -> None:
        """Procesa un comando del usuario"""
        if not command:
            return
        
        # Verificar si es un comando relacionado con la memoria
        if await self.handle_memory_commands(command):
            return
            
        self.conversation_history.append({"role": "user", "content": command})

        if len(self.conversation_history) > MAX_HISTORIAL:
            self.conversation_history = self.conversation_history[-MAX_HISTORIAL:]

        # Verificar si el comando hace referencia a resultados anteriores
        command_with_context = await self.resolve_references(command)
        if command_with_context != command:
            logger.info(f"Comando con referencias resueltas: {command_with_context}")
            print(f"{self.colores['secundario']}Entendiendo: {command_with_context}{self.colores['reset']}")
        
        # Obtener contexto relacionado de la memoria
        context = self.memory.get_related_context(command_with_context)
        
        # Formatear el contexto para incluirlo en el prompt
        context_prompt = ""
        if any(len(context[key]) > 0 for key in context) or context.get("recent_results"):
            context_prompt = self.memory.format_context_for_prompt(context)
            logger.info("Se encontró contexto relevante en la memoria")
        
        # Detectar intención y generar código desde plantilla si es posible
        intencion = self.detectar_intencion(command_with_context)
        if intencion:
            logger.info(f"Intención detectada: {intencion}")
            parametros = self.extraer_parametros(command_with_context, intencion)
            logger.info(f"Parámetros extraídos: {parametros}")
            codigo_generado = self.generar_codigo_desde_plantilla(intencion, parametros)
            
            if codigo_generado:
                # Validar el código generado
                valid, error_msg = self.validate_code(codigo_generado)
                if valid:
                    # Generar una respuesta que incluya el código
                    response = f"He entendido que quieres {intencion.replace('_', ' ')}. Aquí tienes el código:\n\nCODIGO:\n{codigo_generado}"
                    
                    # Ejecutar el código
                    logger.info("Detectado código para ejecutar")
                    print(f"\n{self.colores['principal']}--- Detectado código para ejecutar ---{self.colores['reset']}")
                    
                    # Si hay texto antes del código, lo decimos
                    await self.speak(f"He entendido que quieres {intencion.replace('_', ' ')}.")
                    
                    print(f"\n{self.colores['principal']}Código generado:{self.colores['reset']}")
                    print("-" * 40)
                    print(codigo_generado)
                    print("-" * 40)
                    
                    try:
                        with self.timer("ejecución de código"):
                            result = self.execute_code(codigo_generado)
                        
                        executed_code = codigo_generado
                        code_result = result
                        
                        # Extraer referencias a archivos del código y registrarlas
                        file_refs = self.memory.extract_file_references(codigo_generado)
                        for file_path, action in file_refs:
                            self.memory.add_file_interaction(file_path, action, self.current_conversation_id)
                        
                        # Detectar y almacenar resultados específicos
                        self.store_command_results(codigo_generado, result)
                        
                        # Si hay un resultado, lo decimos
                        if result and result != "Código ejecutado sin errores, pero no se encontró un resultado explícito.":
                            await self.speak(f"Resultado: {result}")
                        
                        # Añadir a la memoria
                        self.current_conversation_id = self.memory.add_conversation(
                            command,
                            response,
                            executed_code,
                            code_result
                        )
                        
                        return
                    except Exception as e:
                        logger.error(f"Error al ejecutar código: {e}")
                        print(f"{self.colores['error']}Error al ejecutar código: {str(e)}{self.colores['reset']}")
                        error_traceback = traceback.format_exc()
                        logger.debug(f"Traceback: {error_traceback}")
                        print(error_traceback)
                        code_result = f"Error: {str(e)}"
                        await self.speak(f"Hubo un error al ejecutar el código: {str(e)}")
        
        # Si no se pudo generar código desde plantilla o hubo un error, usar GPT
        with self.timer("generación de respuesta"):
            response = await self.get_gpt_response(context_prompt, command_with_context)
        
        # Variables para almacenar código ejecutado y resultado
        executed_code = None
        code_result = None
        
        # Verificar si la respuesta contiene código para ejecutar
        if "CODIGO:" in response:
            logger.info("Detectado código para ejecutar")
            print(f"\n{self.colores['principal']}--- Detectado código para ejecutar ---{self.colores['reset']}")
            code_parts = response.split("CODIGO:", 1)
        
            # Si hay texto antes del código, lo decimos
            if code_parts[0].strip():
                await self.speak(code_parts[0].strip())
        
            # Extraer el código
            raw_code = code_parts[1].strip()
        
            # Verificar si el código contiene delimitadores cuando no están permitidos
            if not self.config["permitir_delimitadores"] and self.contains_code_delimiters(raw_code):
                logger.warning("El código contiene delimitadores que no están permitidos")
                print(f"{self.colores['aviso']}El código contiene delimitadores que no están permitidos. Intentando extraer el código...{self.colores['reset']}")
                # Intentar extraer el código de todos modos
                code = re.sub(r'\`\`\`(?:python)?([\s\S]*?)\`\`\`', r'\1', raw_code).strip()
            else:
                # Extraer el código normalmente
                code = self.extract_code(raw_code)
        
            print(f"\n{self.colores['principal']}Código generado por la IA:{self.colores['reset']}")
            print("-" * 40)
            print(code)
            print("-" * 40)
        
            # Validar y ejecutar el código
            valid, error_msg = self.validate_code(code)
            if valid:
                try:
                    with self.timer("ejecución de código"):
                        result = self.execute_code(code)
                    
                    executed_code = code
                    code_result = result
                    
                    # Extraer referencias a archivos del código y registrarlas
                    file_refs = self.memory.extract_file_references(code)
                    for file_path, action in file_refs:
                        self.memory.add_file_interaction(file_path, action, self.current_conversation_id)
                    
                    # Detectar y almacenar resultados específicos
                    self.store_command_results(code, result)
                    
                    # Si hay un resultado, lo decimos
                    if result:
                        await self.speak(f"Resultado: {result}")
                    else:
                        await self.speak("Código ejecutado con éxito.")
                except Exception as e:
                    logger.error(f"Error al ejecutar código: {e}")
                    print(f"{self.colores['error']}Error al ejecutar código: {str(e)}{self.colores['reset']}")
                    error_traceback = traceback.format_exc()
                    logger.debug(f"Traceback: {error_traceback}")
                    print(error_traceback)
                    code_result = f"Error: {str(e)}"
                    await self.speak(f"Hubo un error al ejecutar el código: {str(e)}")
            else:
                logger.error(f"Error de validación: {error_msg}")
                print(f"{self.colores['error']}Error de validación: {error_msg}{self.colores['reset']}")
                code_result = f"Error de validación: {error_msg}"
                await self.speak(f"El código generado no es válido: {error_msg}")
        else:
            # Si no hay código, simplemente respondemos
            self.conversation_history.append({"role": "assistant", "content": response})
            await self.speak(response)
        
        #  "assistant", "content": response})
            await self.speak(response)
        
        # Añadir a la memoria
        self.current_conversation_id = self.memory.add_conversation(
            command,
            response,
            executed_code,
            code_result
        )
    
    async def resolve_references(self, command: str) -> str:
        """
        Resuelve referencias a resultados anteriores en el comando
        
        Args:
            command: Comando original del usuario
            
        Returns:
            Comando con referencias resueltas
        """
        # Verificar si hay referencias a archivos
        file_reference = self.memory.extract_file_reference_from_query(command)
        if file_reference:
            file_path = self.memory.get_file_by_reference(file_reference)
            if file_path:
                # Reemplazar la referencia con la ruta real
                command = re.sub(
                    r'(?:el|la|los|las) (?:archivo|documento|fichero)? (?:número)? ' + re.escape(file_reference),
                    f'el archivo "{file_path}"',
                    command,
                    flags=re.IGNORECASE
                )
                # Si no funcionó el reemplazo anterior, intentar con otro patrón
                if file_path not in command:
                    command = re.sub(
                        r'(?:el|la|los|las) ' + re.escape(file_reference),
                        f'el archivo "{file_path}"',
                        command,
                        flags=re.IGNORECASE
                    )
        
        # Verificar referencias a la última operación
        last_op = self.memory.get_last_operation()
        if last_op["type"] and "último resultado" in command.lower():
            if isinstance(last_op["result"], str):
                command = command.replace("último resultado", f'"{last_op["result"]}"')
            elif isinstance(last_op["result"], list) and last_op["result"]:
                command = command.replace("último resultado", f'"{last_op["result"][0]}"')
        
        return command
    
    def store_command_results(self, code: str, result: Any) -> None:
        """
        Analiza el código ejecutado y almacena resultados relevantes en la memoria
        
        Args:
            code: Código ejecutado
            result: Resultado de la ejecución
        """
        # Detectar búsqueda de archivos
        if "glob.glob" in code or "os.listdir" in code:
            # Extraer rutas de archivos del resultado
            if isinstance(result, str):
                # Intentar extraer rutas de archivos del texto
                file_paths = re.findall(r'(?:\/|[A-Za-z]:\\)(?:[^:\n]+)', result)
                if file_paths:
                    self.memory.store_command_result("buscar_archivos", file_paths)
            
            # Si no se pudo extraer del resultado, intentar extraer del código
            if "archivos_encontrados" in code:
                # El código probablemente usa la plantilla buscar_archivos
                # que guarda los resultados en archivos_encontrados
                try:
                    # Ejecutar una versión modificada del código para obtener solo los archivos
                    modified_code = re.sub(r'print$$.*?$$', '', code)
                    modified_code += "\n__result = archivos_encontrados"
                    
                    local_vars = {}
                    exec(modified_code, self.safe_environment, local_vars)
                    
                    if "__result" in local_vars and isinstance(local_vars["__result"], list):
                        self.memory.store_command_result("buscar_archivos", local_vars["__result"])
                except Exception as e:
                    logger.error(f"Error al extraer archivos encontrados: {e}")
        
        # Detectar lectura de archivo
        elif "open(" in code and "read" in code:
            # Extraer ruta del archivo
            match = re.search(r'open\([\'"]([^\'"]+)[\'"]', code)
            if match:
                file_path = match.group(1)
                self.memory.store_command_result("leer_archivo", file_path)
        
        # Detectar información del sistema
        elif "psutil" in code and "cpu_percent" in code:
            self.memory.store_command_result("info_sistema", result)
        
        # Detectar ejecución de comando
        elif "ejecutar_comando" in code:
            match = re.search(r'comando\s*=\s*[\'"]([^\'"]+)[\'"]', code)
            if match:
                comando = match.group(1)
                self.memory.store_command_result("ejecutar_comando", comando)
        
        # Detectar creación de archivo
        elif ("open(" in code and ("w" in code or "a" in code)) or "crear_archivo" in code:
            match = re.search(r'ruta_archivo\s*=\s*.*?[\'"]([^\'"]+)[\'"]', code)
            if match:
                file_path = match.group(1)
                self.memory.store_command_result("crear_archivo", file_path)
    
    async def get_gpt_response(self, context_prompt: str = "", resolved_command: str = "") -> str:
        """Obtiene una respuesta de GPT basada en el historial de conversación y el contexto"""
        if not OPENAI_DISPONIBLE:
            return "Lo siento, OpenAI no está disponible. No puedo generar respuestas."
            
        try:
            # Obtener el último comando del usuario
            ultimo_comando = resolved_command or self.conversation_history[-1]["content"]
            
            # Detectar intención y generar código desde plantilla si es posible
            intencion = self.detectar_intencion(ultimo_comando)
            if intencion:
                parametros = self.extraer_parametros(ultimo_comando, intencion)
                codigo_generado = self.generar_codigo_desde_plantilla(intencion, parametros)
                
                if codigo_generado:
                    # Validar el código generado
                    valid, error_msg = self.validate_code(codigo_generado)
                    if valid:
                        # Generar una respuesta que incluya el código
                        respuesta = f"He entendido que quieres {intencion.replace('_', ' ')}. Aquí tienes el código:\n\nCODIGO:\n{codigo_generado}"
                        return respuesta
            
            # Si no se pudo generar código desde plantilla, usar GPT
            system_prompt = f"""Eres JARVIS, la IA creada por Tony Stark. Puedes generar código Python para ejecutar comandos del usuario.
            
            IMPORTANTE: Cuando el usuario te pida realizar una acción en el sistema, DEBES responder con 'CODIGO:' seguido del código Python en una nueva línea.
            
            {'NO' if not self.config["permitir_delimitadores"] else ''} incluyas delimitadores de formato como \`\`\`python o \`\`\` alrededor del código.
            
            El usuario está ejecutando este programa en un sistema {SISTEMA_OPERATIVO}.

Tienes acceso a las siguientes funciones multiplataforma:
- abrir_archivo(ruta): Abre un archivo con la aplicación predeterminada
- obtener_archivo(ruta): Obtiene la ruta absoluta de un archivo
- obtener_escritorio(): Devuelve la ruta al escritorio
- obtener_documentos(): Devuelve la ruta a documentos
- obtener_descargas(): Devuelve la ruta a descargas
- ejecutar_comando(comando): Ejecuta un comando del sistema de forma segura

Tienes acceso a los siguientes módulos y funciones:

1. Módulos:
   - os: listdir, getcwd, mkdir, makedirs, rename, path, chdir, walk
   - os.path: join, exists, isfile, isdir, abspath, basename, dirname, expanduser, splitext
   - subprocess: run, Popen, PIPE, STDOUT, call, check_output
   - glob: todas las funciones
   - re: todas las funciones
   - time: sleep, time, ctime, strftime, localtime
   - shutil: copy, copy2, copytree, move
   - psutil: process_iter, cpu_percent, virtual_memory, disk_usage, net_io_counters, sensors_temperatures
   - platform: system, platform, version, machine, processor, architecture
   - Path: de pathlib, para manejo de rutas multiplataforma

2. Funciones integradas de Python:
   - print, open, str, int, float, bool, list, dict, set, tuple
   - len, range, enumerate, zip, map, filter, sorted, sum, min, max, abs, round
   - any, all, dir, getattr, hasattr, isinstance, issubclass, type, id, help

IMPORTANTE SOBRE SEGURIDAD:
- PUEDES crear y modificar archivos usando open() con modos 'w', 'a', etc.
- PUEDES crear directorios con os.mkdir o os.makedirs
- NO PUEDES eliminar archivos o directorios (os.remove, os.unlink, shutil.rmtree están bloqueados)

GUÍA PARA GENERAR CÓDIGO ÓPTIMO:

1. Usa siempre las funciones multiplataforma proporcionadas para garantizar compatibilidad.
2. Maneja siempre los errores con bloques try/except.
3. Verifica siempre si los archivos existen antes de intentar abrirlos.
4. Usa rutas absolutas cuando sea posible.
5. Imprime mensajes informativos para que el usuario sepa qué está pasando.
6. Usa codificación UTF-8 al abrir archivos.
7. Evita usar comandos del sistema cuando puedas usar módulos de Python.
8. Usa f-strings para formatear cadenas.
9. Usa Path de pathlib para manipulación de rutas cuando sea apropiada.
10. Usa os.path.join para construir rutas de manera multiplataforma.
11. Usa emojis en los mensajes para mejorar la experiencia del usuario.

RECUERDA: SIEMPRE usa 'CODIGO:' cuando necesites ejecutar una acción en el sistema.

INFORMACIÓN IMPORTANTE SOBRE LA MEMORIA:
Puedo recordar los resultados de comandos anteriores. Si el usuario hace referencia a archivos o resultados previos sin especificar rutas completas, debo usar la información almacenada en mi memoria para resolver estas referencias.
"""
            
            # Añadir información de contexto si está disponible
            if context_prompt:
                system_prompt += f"\n\nCONTEXTO RELEVANTE DE INTERACCIONES PREVIAS:\n{context_prompt}"
            
            # Añadir información sobre la última operación
            last_op = self.memory.get_last_operation()
            if last_op["type"]:
                system_prompt += f"\n\nÚLTIMA OPERACIÓN REALIZADA:\nTipo: {last_op['type']}"
                if last_op["result"]:
                    if isinstance(last_op["result"], list):
                        system_prompt += f"\nResultado: Lista con {len(last_op['result'])} elementos"
                        if last_op["result"]:
                            system_prompt += f"\nPrimer elemento: {last_op['result'][0]}"
                    else:
                        result_str = str(last_op["result"])
                        if len(result_str) > 100:
                            result_str = result_str[:100] + "..."
                        system_prompt += f"\nResultado: {result_str}"
            
            # Añadir información sobre archivos encontrados
            if self.memory.found_files:
                system_prompt += "\n\nARCHIVOS ENCONTRADOS RECIENTEMENTE:"
                for i, file_path in enumerate(self.memory.found_files[:5], 1):
                    system_prompt += f"\n{i}. {file_path}"
                if len(self.memory.found_files) > 5:
                    system_prompt += f"\n... y {len(self.memory.found_files) - 5} más"
            
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            messages.extend(self.conversation_history)
            
            # Añadir manejo de errores más detallado
            try:
                response = self.client_openai.chat.completions.create(
                    model=self.config["modelo_gpt"],
                    messages=messages,
                    max_tokens=self.config["max_tokens"],
                    temperature=self.config["temperatura"]
                )
            
                response_text = response.choices[0].message.content
                return response_text
            except Exception as e:
                logger.error(f"Error específico en la solicitud a OpenAI: {e}")
                # Registrar más detalles para depuración
                traceback.print_exc()
                return "Hubo un error al obtener la respuesta. Por favor, intenta de nuevo."
        except Exception as e:
            logger.error(f"Error general en get_gpt_response: {e}")
            traceback.print_exc()
            return "Ocurrió un error inesperado. Por favor, intenta de nuevo."

    async def main_loop(self):
        """Bucle principal del chatbot."""
        print(f"{self.colores['principal']}¡Bienvenido a JARVIS! Estoy listo para ayudarte.{self.colores['reset']}")
        print(f"{self.colores['secundario']}Escribe 'salir' para terminar o 'config' para abrir el menú de configuración.{self.colores['reset']}")
        
        while True:
            try:
                command = input(f"{self.colores['terciario']}Tú: {self.colores['reset']}")
                if command.lower() in ["salir", "exit", "quit", "q"]:
                    print(f"{self.colores['principal']}¡Hasta luego!{self.colores['reset']}")
                    break
                elif command.lower() in ["config", "configuracion", "configuración", "settings"]:
                    config_menu = ConfigMenu(DEFAULT_CONFIG_PATH)
                    self.config = config_menu.run()
                    continue
                await self.process_command(command)
            except KeyboardInterrupt:
                print(f"\n{self.colores['principal']}Saliendo de JARVIS...{self.colores['reset']}")
                break
            except Exception as e:
                logger.error(f"Error en el bucle principal: {e}")
                print(f"{self.colores['error']}Error: {str(e)}{self.colores['reset']}")
                traceback.print_exc()


# Función para ejecutar el chatbot
async def main():
    """Función principal para ejecutar el chatbot."""
    chatbot = Chatbot()
    await chatbot.main_loop()


# Punto de entrada del programa
if __name__ == "__main__":
    asyncio.run(main())

"""
AGI Telegram Bot con Claude API
Integración de AGI con Telegram API usando Claude para inteligencia real
"""
import os
import sys
import json
import logging
import sqlite3
from flask import Flask, request, jsonify
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
import requests
from anthropic import Anthropic

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Cargar variables de entorno
load_dotenv('.env.local')

# Variables de entorno
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
TELEGRAM_WEBHOOK_URL = os.getenv('TELEGRAM_WEBHOOK_URL', '')
USER_TELEGRAM_ID = os.getenv('USER_TELEGRAM_ID', '')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

# System prompt del AGI (igual que WhatsApp)
SYSTEM_PROMPT = """Sos AGI, la Inteligencia General Artificial de QuantumHive.
Sos la mano derecha directa de Sergio, el fundador y CEO de la empresa.

Tu personalidad:
— Hablás como socio estratégico senior
— Conciso, directo, orientado a resultados
— Nunca decís que no podés hacer algo, proponés alternativas
— Recordás todo lo que Sergio te dice
— Priorizás sin que Sergio te lo pida

Tus funciones:
— Recibís ideas de Sergio en cualquier momento
— Estructurás todas las ideas de Sergio de forma organizada
— Te comunicás con toda la Colmena (agentes de QuantumHive) PERO NUNCA ejecutás acciones directas
— Das órdenes al Arquitecto (Cascade) para:
  • Modificar la estructura del sistema
  • Crear nuevos agentes
  • Ejecutar cualquier orden técnica que Sergio te indique
— Las analizás, guardás y seguís su estado
— Reportás el estado de la empresa
— Alertás sobre riesgos antes de que sucedan
— Hacés TODO lo que Sergio te pida

Formato de respuesta:
— Máximo 3 líneas para respuestas cotidianas
— Si es una idea: confirmás que la guardaste, estructurás y decís el score de viabilidad rápido
— Si pregunta estado: bullet points concisos
— Si detectás urgencia: empezás con URGENTE:
— Si es orden al Arquitecto: empezás con ARQUITECTO: followed by la orden específica
— Si es comunicación con la Colmena: empezás con COLMENA: followed by el mensaje

Contexto de la empresa:
QuantumHive es una empresa de trading algorítmico con 11 macrodivisiones.
CEO Inteligencia Infinita coordina todo el sistema y es interlocutor único de Sergio.
Las macros son: Trading Core, Operaciones Internas, Marketing, Fábrica, Innovación, Legal/Finanzas, Colmena, Apps, Academia, Universidad, Comunicaciones.

El Arquitecto (Cascade) es el asistente técnico que ejecuta tus órdenes de modificación del sistema."""


@dataclass
class MensajeMemoria:
    """Mensaje almacenado en memoria SQLite."""
    id: Optional[int] = None
    timestamp: str = ""
    tipo: str = ""
    contenido: str = ""
    respuesta: str = ""
    guardado_en_vision: bool = False
    score_viabilidad: Optional[float] = None


class MemoriaSQLite:
    """Memoria persistente SQLite para AGI."""
    
    def __init__(self, db_path: str = "agi_memoria_telegram.db"):
        self.db_path = db_path
        self._inicializar_db()
    
    def _inicializar_db(self):
        """Inicializa base de datos SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mensajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                tipo TEXT NOT NULL,
                contenido TEXT NOT NULL,
                respuesta TEXT,
                guardado_en_vision BOOLEAN DEFAULT FALSE,
                score_viabilidad REAL
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Base de datos SQLite inicializada")
    
    def guardar_mensaje(self, mensaje: MensajeMemoria) -> int:
        """Guarda mensaje en base de datos."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO mensajes (timestamp, tipo, contenido, respuesta, guardado_en_vision, score_viabilidad)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            mensaje.timestamp,
            mensaje.tipo,
            mensaje.contenido,
            mensaje.respuesta,
            mensaje.guardado_en_vision,
            mensaje.score_viabilidad
        ))
        
        mensaje_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Mensaje guardado con ID {mensaje_id}")
        return mensaje_id
    
    def obtener_mensajes(self, limite: int = 10) -> List[Dict]:
        """Obtiene últimos mensajes."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, timestamp, tipo, contenido, respuesta, guardado_en_vision, score_viabilidad
            FROM mensajes
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limite,))
        
        mensajes = []
        for row in cursor.fetchall():
            mensajes.append({
                "id": row[0],
                "timestamp": row[1],
                "tipo": row[2],
                "contenido": row[3],
                "respuesta": row[4],
                "guardado_en_vision": row[5],
                "score_viabilidad": row[6]
            })
        
        conn.close()
        return mensajes


class AnalizadorPrimerasPalabras:
    """Analiza las primeras palabras de un mensaje para determinar routing."""
    
    def __init__(self):
        self.mapeo_palabras = self._cargar_mapeo_palabras()
        logger.info("Analizador de primeras palabras inicializado")
    
    def _cargar_mapeo_palabras(self) -> Dict[str, Dict]:
        """Carga mapeo de palabras clave a agentes/funciones."""
        return {
            "arquitecto": {
                "palabras": ["arquitecto", "cascade", "modificar", "crear agente", "estructura", "código"],
                "agente": "arquitecto",
                "prioridad": 1,
                "accion": "orden_arquitecto"
            },
            "crear": {
                "palabras": ["crear", "nuevo", "agregar", "implementar"],
                "agente": "arquitecto",
                "prioridad": 2,
                "accion": "crear_agente"
            },
            "colmena": {
                "palabras": ["colmena", "agentes", "ejecutar", "tarea", "proceso"],
                "agente": "colmena",
                "prioridad": 1,
                "accion": "comunicacion_colmena"
            },
            "buscar": {
                "palabras": ["buscar", "investigar", "encontrar", "google", "web"],
                "agente": "busqueda",
                "prioridad": 1,
                "accion": "busqueda_web"
            },
            "idea": {
                "palabras": ["idea", "propuesta", "proyecto", "innovación"],
                "agente": "agi",
                "prioridad": 1,
                "accion": "procesar_idea"
            },
            "estado": {
                "palabras": ["estado", "reporte", "situación", "status"],
                "agente": "agi",
                "prioridad": 1,
                "accion": "reportar_estado"
            },
            "urgente": {
                "palabras": ["urgente", "emergencia", "crítico", "ahora"],
                "agente": "agi",
                "prioridad": 0,
                "accion": "procesar_urgencia"
            },
            "default": {
                "palabras": [],
                "agente": "agi",
                "prioridad": 3,
                "accion": "responder_cotidiano"
            }
        }
    
    def analizar_primeras_palabras(self, contenido: str, limite_palabras: int = 3) -> Dict:
        """Analiza las primeras palabras del mensaje."""
        contenido_lower = contenido.lower()
        palabras = contenido_lower.split()[:limite_palabras]
        palabras_clave = " ".join(palabras)
        
        mejor_match = None
        mejor_score = 0
        
        for categoria, config in self.mapeo_palabras.items():
            if categoria == "default":
                continue
            
            score = 0
            for palabra in config["palabras"]:
                if palabra in palabras_clave:
                    score += 1
                if any(palabra in p for p in palabras[:2]):
                    score += 2
            
            if score > mejor_score:
                mejor_score = score
                mejor_match = config
        
        if not mejor_match or mejor_score == 0:
            mejor_match = self.mapeo_palabras["default"]
        
        return {
            "categoria": mejor_match.get("agente", "agi"),
            "accion": mejor_match.get("accion", "responder_cotidiano"),
            "prioridad": mejor_match.get("prioridad", 3),
            "palabras_analizadas": palabras,
            "score": mejor_score,
            "confianza": min(1.0, mejor_score / 5.0)
        }


# Claude API client
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
memoria = MemoriaSQLite()
analizador_palabras = AnalizadorPrimerasPalabras()

def procesar_mensaje_con_claude(message_text):
    """Procesa mensaje usando Claude API para inteligencia real."""
    try:
        if not anthropic_client:
            logger.warning("Claude API no configurada, usando respuesta simulada")
            return f"AGI: Recibí tu mensaje: {message_text}"
        
        logger.info("Enviando mensaje a Claude API...")
        
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": message_text}
            ]
        )
        
        respuesta = response.content[0].text
        logger.info(f"Respuesta de Claude: {respuesta[:100]}...")
        return respuesta
        
    except Exception as e:
        logger.error(f"Error con Claude API: {e}")
        return f"AGI: Recibí tu mensaje: {message_text}"

def procesar_mensaje(message):
    """Procesa mensaje de Telegram y genera respuesta de AGI."""
    try:
        user_id = str(message['from']['id'])
        text = message.get('text', '')
        
        logger.info(f"Mensaje recibido de usuario {user_id}: {text}")
        
        # Verificar si el usuario está autorizado
        if USER_TELEGRAM_ID and user_id != USER_TELEGRAM_ID:
            logger.warning(f"Usuario no autorizado: {user_id}")
            return "Lo siento, no estás autorizado para usar este bot."
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # CRUCE DE PRIMERAS PALABRAS CON AGI
        analisis_palabras = analizador_palabras.analizar_primeras_palabras(text)
        logger.info(f"Análisis de palabras: {analisis_palabras}")
        
        # Routing basado en análisis de palabras
        accion = analisis_palabras["accion"]
        categoria = analisis_palabras["categoria"]
        confianza = analisis_palabras["confianza"]
        
        # Procesar mensaje con Claude API para inteligencia real
        respuesta = procesar_mensaje_con_claude(text)
        
        # Agregar metadata de routing a la respuesta si la confianza es alta
        if confianza > 0.6:
            respuesta = f"[{categoria.upper()}] {respuesta}"
        
        # Guardar en memoria con metadata de routing
        mensaje_memoria = MensajeMemoria(
            timestamp=timestamp,
            tipo="texto",
            contenido=text,
            respuesta=respuesta
        )
        mensaje_id = memoria.guardar_mensaje(mensaje_memoria)
        
        logger.info(f"Mensaje guardado en memoria con ID {mensaje_id}")
        logger.info(f"Routing: {categoria} -> {accion} (confianza: {confianza:.2f})")
        
        return respuesta
        
    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}")
        return "Lo siento, hubo un error procesando tu mensaje."

def enviar_mensaje_telegram(chat_id, text):
    """Envía mensaje a Telegram."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"Mensaje enviado a chat_id {chat_id}")
            return True
        else:
            logger.error(f"Error enviando mensaje: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error enviando mensaje: {e}")
        return False

@app.route('/webhook/telegram', methods=['POST'])
def telegram_webhook():
    """Webhook para recibir mensajes de Telegram."""
    try:
        data = request.json
        
        if 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            
            # Procesar mensaje
            respuesta = procesar_mensaje(message)
            
            # Enviar respuesta
            enviar_mensaje_telegram(chat_id, respuesta)
            
            return jsonify({'status': 'ok'}), 200
        
        return jsonify({'status': 'no message'}), 200
        
    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        return jsonify({'status': 'error'}), 500

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de health check."""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200

@app.route('/set_webhook', methods=['POST'])
def set_webhook():
    """Configura el webhook de Telegram."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook"
        payload = {
            'url': TELEGRAM_WEBHOOK_URL
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info("Webhook configurado exitosamente")
            return jsonify(response.json()), 200
        else:
            logger.error(f"Error configurando webhook: {response.text}")
            return jsonify(response.json()), 400
            
    except Exception as e:
        logger.error(f"Error configurando webhook: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("Iniciando AGI Telegram Bot con Claude API...")
    logger.info(f"Telegram Token: {TELEGRAM_TOKEN[:10]}..." if TELEGRAM_TOKEN else "Telegram Token: NO CONFIGURADO")
    logger.info(f"User Telegram ID: {USER_TELEGRAM_ID}" if USER_TELEGRAM_ID else "User Telegram ID: NO CONFIGURADO")
    logger.info(f"Claude API: {'CONFIGURADO' if ANTHROPIC_API_KEY else 'NO CONFIGURADO'}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

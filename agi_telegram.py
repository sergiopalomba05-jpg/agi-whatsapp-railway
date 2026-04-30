"""
AGI Telegram Bot con Claude API
Integración de AGI con Telegram API usando Claude para inteligencia real
"""
import os
import logging
from flask import Flask, request, jsonify
from datetime import datetime
import requests
from anthropic import Anthropic

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Variables de entorno
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
TELEGRAM_WEBHOOK_URL = os.getenv('TELEGRAM_WEBHOOK_URL', '')
USER_TELEGRAM_ID = os.getenv('USER_TELEGRAM_ID', '')  # ID de Telegram del usuario autorizado
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')  # Claude API key

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

# Claude API client
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

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
        
        # Procesar mensaje con Claude API para inteligencia real
        respuesta = procesar_mensaje_con_claude(text)
        
        logger.info(f"Respuesta generada: {respuesta}")
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

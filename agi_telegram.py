"""
AGI Telegram Bot
Integración de AGI con Telegram API
"""
import os
import logging
from flask import Flask, request, jsonify
from datetime import datetime
import requests

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
        
        # Aquí iría la lógica de AGI para procesar el mensaje
        # Por ahora, respondemos con un mensaje simple
        respuesta = f"AGI: Recibí tu mensaje: {text}"
        
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
    logger.info("Iniciando AGI Telegram Bot...")
    logger.info(f"Telegram Token: {TELEGRAM_TOKEN[:10]}..." if TELEGRAM_TOKEN else "Telegram Token: NO CONFIGURADO")
    logger.info(f"User Telegram ID: {USER_TELEGRAM_ID}" if USER_TELEGRAM_ID else "User Telegram ID: NO CONFIGURADO")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

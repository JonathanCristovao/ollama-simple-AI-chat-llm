import os
import json
import logging
import requests
from flask import Flask, request, jsonify, render_template, Response, stream_with_context
from flask_cors import CORS

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv não está instalado, usar apenas variáveis de ambiente do sistema
    pass

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configurações
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://ollama:11434')
PORT = int(os.getenv('PORT', 5000))
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

@app.route('/')
def index():
    """Página principal do chat"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Endpoint de saúde da aplicação"""
    try:
        # Verificar se o Ollama está acessível
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        ollama_status = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception as e:
        ollama_status = f"error: {str(e)}"
    
    return jsonify({
        "status": "healthy",
        "ollama_url": OLLAMA_URL,
        "ollama_status": ollama_status
    })

@app.route('/api/models')
def get_models():
    """Listar modelos disponíveis no Ollama"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": "Failed to fetch models"}), response.status_code
    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint para chat com streaming"""
    try:
        data = request.json
        if not data or 'message' not in data:
            return jsonify({"error": "Message is required"}), 400
        
        # Preparar dados para o Ollama
        ollama_data = {
            "model": data.get('model', 'qwen2.5:0.5b'),
            "prompt": data['message'],
            "stream": True
        }
        
        # Fazer requisição para o Ollama
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=ollama_data,
            stream=True,
            timeout=120
        )
        
        if response.status_code != 200:
            return jsonify({"error": f"Ollama error: {response.status_code}"}), response.status_code
        
        def generate():
            try:
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line.decode('utf-8'))
                        yield f"data: {json.dumps(chunk)}\n\n"
                        
                        if chunk.get('done', False):
                            break
            except Exception as e:
                logger.error(f"Error in streaming: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*'
            }
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate', methods=['POST'])
def generate():
    """Endpoint compatível com API do Ollama"""
    try:
        data = request.json
        
        # Repassar requisição para o Ollama
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=data,
            stream=data.get('stream', False),
            timeout=120
        )
        
        if data.get('stream', False):
            def generate_stream():
                for line in response.iter_lines():
                    if line:
                        yield line + b'\n'
            
            return Response(
                stream_with_context(generate_stream()),
                mimetype='application/x-ndjson',
                headers={
                    'Access-Control-Allow-Origin': '*'
                }
            )
        else:
            return jsonify(response.json()), response.status_code
            
    except Exception as e:
        logger.error(f"Error in generate endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tags')
def get_tags():
    """Proxy para endpoint de tags do Ollama"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error(f"Error fetching tags: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/pull', methods=['POST'])
def pull_model():
    """Endpoint para baixar modelos"""
    try:
        data = request.json
        response = requests.post(
            f"{OLLAMA_URL}/api/pull",
            json=data,
            stream=True,
            timeout=600  # 10 minutos para download
        )
        
        def generate_pull():
            for line in response.iter_lines():
                if line:
                    yield line + b'\n'
        
        return Response(
            stream_with_context(generate_pull()),
            mimetype='application/x-ndjson'
        )
        
    except Exception as e:
        logger.error(f"Error pulling model: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logger.info(f"Starting Flask app on port {PORT}")
    logger.info(f"Ollama URL: {OLLAMA_URL}")
    
    app.run(
        host='0.0.0.0',
        port=PORT,
        debug=DEBUG,
        threaded=True
    )

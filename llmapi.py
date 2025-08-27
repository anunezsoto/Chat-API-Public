import re
import requests
import sqlite3
import json
import logging
import os
import time
from flask import Flask, request, jsonify
from flask_cors import CORS

# Basic logging setup with stream handler only
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Get script directory
script_dir = os.path.dirname(os.path.abspath(__file__))

# Default config
default_config = {
    "log_path": "flask.log",
    "ollama_server": "http://localhost:11434",
    "use_context": True,
    "flask_host": "0.0.0.0",
    "flask_port": 6000,
    "flask_debug": False,
    "db_path": "user_contexts.db"
}

# Load config
config_path = os.path.join(script_dir, 'config.json')
config = {}
try:
    with open(config_path, 'r') as f:
        config = json.load(f)
    logger.info('Config loaded successfully')
except FileNotFoundError:
    logger.info(f'Config file not found at {config_path}; creating with defaults')
    with open(config_path, 'w') as f:
        json.dump(default_config, f, indent=4)
    config = default_config
except json.JSONDecodeError as e:
    logger.warning(f'Invalid JSON in config file: {e}, using defaults')
    config = default_config
except Exception as e:
    logger.warning(f'Failed to load config: {e}, using defaults')
    config = default_config

# Set log path and add file handler
log_path = config.get('log_path', 'flask.log')
if not os.path.isabs(log_path):
    log_path = os.path.join(script_dir, log_path)
try:
    fh = logging.FileHandler(log_path)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
    logger.addHandler(fh)
    logger.info(f'File logging enabled at {log_path}')
except Exception as e:
    logger.warning(f'Failed to add file handler: {e}')

# Other configs
OLLAMA_SERVER = config.get('ollama_server', os.getenv("OLLAMA_SERVER", "http://localhost:11434"))
USE_CONTEXT = config.get('use_context', True)
flask_host = config.get('flask_host', "0.0.0.0")
flask_port = config.get('flask_port', 6000)
flask_debug = config.get('flask_debug', False)

# Database path
db_default = 'user_contexts.db'
db_config_path = config.get('db_path', db_default)
if os.path.isabs(db_config_path):
    db_path = db_config_path
else:
    db_path = os.path.join(script_dir, db_config_path)

app = Flask(__name__)
CORS(app)

# Initialize SQLite database for contexts and loaded model
def init_db():
    try:
        # Check if database file is accessible
        if not os.path.exists(db_path):
            logger.info(f"Database file {db_path} does not exist; creating...")
        elif not os.access(db_path, os.R_OK | os.W_OK):
            logger.error(f"Database file {db_path} exists but is not readable/writable")
            raise PermissionError(f"Database file {db_path} is not accessible")

        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS contexts (user_id TEXT PRIMARY KEY, context TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS loaded_model (id INTEGER PRIMARY KEY CHECK (id = 1), name TEXT)")
        conn.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        conn.close()

def save_context(user_id, context):
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO contexts (user_id, context) VALUES (?, ?)",
                  (user_id, json.dumps(context)))
        conn.commit()
        logger.debug(f"Saved context for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to save context for user {user_id}: {e}")
    finally:
        conn.close()

def load_context(user_id):
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT context FROM contexts WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        return json.loads(result[0]) if result else []
    except Exception as e:
        logger.error(f"Failed to load context for user {user_id}: {e}")
        return []
    finally:
        conn.close()

def save_loaded_model(model):
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO loaded_model (id, name) VALUES (1, ?)", (model,))
        conn.commit()
        logger.debug(f"Saved loaded model: {model}")
    except Exception as e:
        logger.error(f"Failed to save loaded model: {e}")
    finally:
        conn.close()

def get_loaded_model():
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM loaded_model WHERE id = 1")
        result = c.fetchone()
        model = result[0] if result else None
        if model and not is_model_loaded(model):
            save_loaded_model(None)
            model = None
        logger.debug(f"Retrieved loaded model: {model}")
        return model
    except Exception as e:
        logger.error(f"Failed to get loaded model: {e}")
        return None
    finally:
        conn.close()

# Check if a model is loaded using /api/ps
def is_model_loaded(model):
    try:
        response = requests.get(f"{OLLAMA_SERVER}/api/ps", timeout=10)
        logger.debug(f"Ollama /api/ps response: {response.status_code} - {response.text}")
        if response.status_code != 200:
            logger.error(f"Failed to check running models: {response.status_code} - {response.text}")
            return False
        running_models = [m['name'] for m in response.json().get('models', [])]
        return model in running_models
    except requests.Timeout:
        logger.error(f"Timeout checking running models for {model}")
        return False
    except requests.RequestException as e:
        logger.error(f"Network error checking running models for {model}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error checking running models for {model}: {str(e)}")
        return False

# Poll Ollama for models
def poll_ollama_models():
    try:
        response = requests.get(f"{OLLAMA_SERVER}/api/tags", timeout=10)
        logger.debug(f"Ollama /api/tags response: {response.status_code} - {response.text}")
        if response.status_code == 200:
            result = response.json()
            models = [model['name'] for model in result.get('models', [])]
            logger.info(f"Polled {len(models)} models: {models}")
            return models
        else:
            logger.error(f"Failed to poll models: {response.status_code} - {response.text}")
            return []
    except requests.Timeout:
        logger.error("Timeout polling Ollama models")
        return []
    except requests.RequestException as e:
        logger.error(f"Network error polling Ollama models: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Error polling Ollama models: {str(e)}")
        return []

def clean_response(response_text):
    """Removes <think> tags and cleans up response."""
    try:
        response_text = re.sub(r"<think>.*?</think>", "", response_text, flags=re.DOTALL)
        response_text = re.sub(r"<think>|</think>", "", response_text)
        return response_text.strip()
    except Exception as e:
        logger.error(f"Error cleaning response: {e}")
        return response_text

# Initialize database at startup
try:
    init_db()
except Exception as e:
    logger.error(f"Failed to initialize app: {e}")
    raise

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        logger.debug(f"Received chat request: {data}")
        user_id = data.get("user_id", "default")
        user_input = data.get("message", "").strip()
        use_context = data.get("use_context", USE_CONTEXT)
        model = data.get("model")

        if not user_input:
            logger.warning("No message provided in request")
            return jsonify({"error": "Message is required"}), 400
        if not user_id or not isinstance(user_id, str) or len(user_id) > 100:
            logger.warning(f"Invalid user_id: {user_id}")
            return jsonify({"error": "Invalid or missing user_id"}), 400

        # If no model specified, try to use the currently loaded model or a default
        if not model:
            model = get_loaded_model()
            if not model:
                # Fallback to first available model from /api/tags
                available_models = poll_ollama_models()
                if available_models:
                    model = available_models[0]
                    logger.info(f"No model loaded; using first available model: {model}")
                else:
                    logger.warning("No model specified and no models available")
                    return jsonify({"error": "Model is required and no models are available"}), 400
            else:
                logger.info(f"No model specified; using loaded model: {model}")

        # Verify model exists via /api/tags
        models = poll_ollama_models()
        if model not in models:
            logger.warning(f"Model {model} not found in available models")
            return jsonify({"error": f"Model {model} not found"}), 400

        previous_messages = load_context(user_id) if use_context else []
        logger.debug(f"Context for user {user_id}: {previous_messages}")

        messages = previous_messages + [{"role": "user", "content": user_input}]

        response = requests.post(
            f"{OLLAMA_SERVER}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "keep_alive": -1
            },
            timeout=60
        )

        logger.debug(f"Ollama /api/chat response: {response.status_code} - {response.text}")
        if response.status_code != 200:
            logger.error(f"Ollama chat request failed: {response.status_code} - {response.text}")
            return jsonify({
                "error": "Failed to get response from Ollama",
                "status": response.status_code,
                "response": response.text
            }), 500

        try:
            result = response.json()
        except ValueError as e:
            logger.error(f"Failed to parse Ollama response as JSON: {e}")
            return jsonify({"error": "Invalid response from Ollama server"}), 500

        ai_response = result.get("message", {}).get("content", "")

        if not ai_response:
            logger.warning("No content in Ollama response")
            return jsonify({"error": "No response content from AI"}), 500

        cleaned_response = clean_response(ai_response)
        logger.debug(f"Cleaned response: {cleaned_response}")

        new_messages = previous_messages + [{"role": "user", "content": user_input}, {"role": "assistant", "content": ai_response}]

        if use_context:
            save_context(user_id, new_messages)

        save_loaded_model(model)
        return jsonify({
            "choices": [{"message": {"content": cleaned_response}}],
            "context": new_messages if use_context else []
        })

    except requests.Timeout:
        logger.error("Request to Ollama timed out")
        return jsonify({"error": "Request timed out. Please try again later."}), 500
    except requests.RequestException as e:
        logger.error(f"Network error: {str(e)}")
        return jsonify({"error": f"Network error: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error in chat: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/models', methods=['GET'])
def list_models():
    try:
        # Always poll for fresh list; ignore refresh param for simplicity
        models = poll_ollama_models()
        logger.debug(f"Returning models: {models}")
        return jsonify({"models": models})
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/loaded-model', methods=['GET'])
def loaded_model():
    try:
        model = get_loaded_model()
        logger.debug(f"Returning loaded model: {model}")
        return jsonify({"loaded_model": model})
    except Exception as e:
        logger.error(f"Error getting loaded model: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/load-model', methods=['POST'])
def load_model():
    try:
        data = request.json
        model = data.get("model")
        if not model:
            logger.warning("No model provided in load request")
            return jsonify({"error": "Model name is required"}), 400

        # Verify model exists via /api/tags; pull if not
        models = poll_ollama_models()
        if model not in models:
            logger.info(f"Model {model} not found locally; pulling...")
            pull_response = requests.post(
                f"{OLLAMA_SERVER}/api/pull",
                json={"name": model, "stream": False},
                timeout=600
            )
            if pull_response.status_code != 200:
                logger.error(f"Failed to pull model {model}: {pull_response.status_code} - {pull_response.text}")
                return jsonify({"error": f"Failed to pull model: {pull_response.text}"}), 500
            # Repoll after pull
            models = poll_ollama_models()
            if model not in models:
                return jsonify({"error": f"Model {model} not available after pull"}), 500

        # Load model into memory with a dummy generate call
        logger.info(f"Loading model {model} into memory")
        load_response = requests.post(
            f"{OLLAMA_SERVER}/api/generate",
            json={
                "model": model,
                "prompt": "",
                "stream": False,
                "keep_alive": -1
            },
            timeout=60
        )
        if load_response.status_code != 200:
            logger.error(f"Failed to load model {model}: {load_response.status_code} - {load_response.text}")
            return jsonify({"error": f"Failed to load model: {load_response.text}"}), 500

        # Verify model is loaded
        time.sleep(1)  # Give time for loading
        if not is_model_loaded(model):
            logger.error(f"Model {model} not listed in /api/ps after loading")
            return jsonify({"error": f"Model {model} failed to load into memory"}), 500

        save_loaded_model(model)
        return jsonify({"success": True, "message": f"Model {model} loaded successfully"})

    except requests.Timeout:
        logger.error(f"Timeout loading model {model}")
        return jsonify({"error": "Request to Ollama timed out"}), 500
    except requests.RequestException as e:
        logger.error(f"Network error loading model {model}: {str(e)}")
        return jsonify({"error": f"Network error: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error loading model {model}: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/stop-model', methods=['POST'])
def stop_model():
    try:
        data = request.json
        model = data.get("model")
        if not model:
            logger.warning("No model provided in stop request")
            return jsonify({"error": "Model name is required"}), 400

        # Verify model exists via /api/tags
        models = poll_ollama_models()
        if model not in models:
            logger.warning(f"Model {model} not found in available models")
            return jsonify({"error": f"Model {model} not found"}), 400

        # Check if model is loaded
        if not is_model_loaded(model):
            logger.info(f"Model {model} is not loaded")
            if model == get_loaded_model():
                save_loaded_model(None)
            return jsonify({"success": True, "message": f"Model {model} is not loaded"})

        # Unload model with a dummy generate call and keep_alive=0
        logger.info(f"Unloading model {model}")
        stop_response = requests.post(
            f"{OLLAMA_SERVER}/api/generate",
            json={
                "model": model,
                "prompt": "",
                "stream": False,
                "keep_alive": 0
            },
            timeout=60
        )
        logger.debug(f"Ollama /api/generate stop response: {stop_response.status_code} - {stop_response.text}")
        if stop_response.status_code != 200:
            logger.error(f"Failed to stop model {model}: {stop_response.status_code} - {stop_response.text}")
            return jsonify({"error": f"Failed to stop model: {stop_response.text}"}), 500

        # Verify model is unloaded
        time.sleep(2)  # Give time for unloading
        if not is_model_loaded(model):
            if model == get_loaded_model():
                save_loaded_model(None)
            return jsonify({"success": True, "message": f"Model {model} stopped/unloaded successfully"})

        logger.error(f"Model {model} still loaded after unload attempt")
        return jsonify({"error": f"Failed to unload model {model}"}), 500

    except requests.Timeout:
        logger.error(f"Timeout stopping model {model}")
        return jsonify({"error": "Request to Ollama timed out"}), 500
    except requests.RequestException as e:
        logger.error(f"Network error stopping model {model}: {str(e)}")
        return jsonify({"error": f"Network error: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Error stopping model: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/stop-loaded-model', methods=['POST'])
def stop_loaded_model():
    try:
        model = get_loaded_model()
        if not model:
            logger.info("No model currently loaded")
            return jsonify({"success": True, "message": "No model currently loaded"})

        # Check if model is loaded
        if not is_model_loaded(model):
            logger.info(f"Model {model} is not loaded")
            save_loaded_model(None)
            return jsonify({"success": True, "message": f"Model {model} is not loaded"})

        # Unload model with a dummy generate call and keep_alive=0
        logger.info(f"Unloading currently loaded model {model}")
        stop_response = requests.post(
            f"{OLLAMA_SERVER}/api/generate",
            json={
                "model": model,
                "prompt": "",
                "stream": False,
                "keep_alive": 0
            },
            timeout=60
        )
        logger.debug(f"Ollama /api/generate stop response: {stop_response.status_code} - {stop_response.text}")
        if stop_response.status_code != 200:
            logger.error(f"Failed to stop model {model}: {stop_response.status_code} - {stop_response.text}")
            return jsonify({"error": f"Failed to stop model: {stop_response.text}"}), 500

        # Verify model is unloaded
        time.sleep(2)  # Give time for unloading
        if not is_model_loaded(model):
            save_loaded_model(None)
            return jsonify({"success": True, "message": f"Model {model} stopped/unloaded successfully"})

        logger.error(f"Model {model} still loaded after unload attempt")
        return jsonify({"error": f"Failed to unload model {model}"}), 500

    except requests.Timeout:
        logger.error("Timeout stopping loaded model")
        return jsonify({"error": "Request to Ollama timed out"}), 500
    except requests.RequestException as e:
        logger.error(f"Network error stopping loaded model: {str(e)}")
        return jsonify({"error": f"Network error: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Error stopping loaded model: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host=flask_host, port=flask_port, debug=flask_debug)

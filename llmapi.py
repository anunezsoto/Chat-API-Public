import re
import requests
import sqlite3
import json
import logging
import os
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('/home/andres/llmapi/flask.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Ollama server settings (from environment variables)
OLLAMA_SERVER = os.getenv("OLLAMA_SERVER", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:1.5b")

# Context setting
USE_CONTEXT = True

# Initialize SQLite database for persistent context storage
def init_db():
    try:
        conn = sqlite3.connect("/home/andres/llmapi/user_contexts.db")
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS contexts (user_id TEXT PRIMARY KEY, context TEXT)")
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    finally:
        conn.close()

def save_context(user_id, context):
    try:
        conn = sqlite3.connect("/home/andres/llmapi/user_contexts.db")
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO contexts (user_id, context) VALUES (?, ?)",
                  (user_id, json.dumps(context)))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to save context for user {user_id}: {e}")
    finally:
        conn.close()

def load_context(user_id):
    try:
        conn = sqlite3.connect("/home/andres/llmapi/user_contexts.db")
        c = conn.cursor()
        c.execute("SELECT context FROM contexts WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        return json.loads(result[0]) if result else []
    except Exception as e:
        logger.error(f"Failed to load context for user {user_id}: {e}")
        return []
    finally:
        conn.close()

init_db()

def clean_response(response_text):
    """Removes <think> tags and cleans up response."""
    try:
        response_text = re.sub(r"<think>.*?</think>", "", response_text, flags=re.DOTALL)
        response_text = re.sub(r"<think>|</think>", "", response_text)
        return response_text.strip()
    except Exception as e:
        logger.error(f"Error cleaning response: {e}")
        return response_text

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        logger.debug(f"Received request: {data}")
        user_id = data.get("user_id", "default")
        user_input = data.get("message", "").strip()
        use_context = data.get("use_context", USE_CONTEXT)

        if not user_input:
            logger.warning("No message provided in request")
            return jsonify({"error": "Message is required"}), 400
        if not user_id or not isinstance(user_id, str) or len(user_id) > 100:
            logger.warning(f"Invalid user_id: {user_id}")
            return jsonify({"error": "Invalid or missing user_id"}), 400

        context = load_context(user_id) if use_context else []
        logger.debug(f"Context for user {user_id}: {context}")

        response = requests.post(
            f"{OLLAMA_SERVER}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": user_input}],
                "stream": False,
                "context": context
            },
            timeout=60
        )

        logger.debug(f"Ollama response: {response.status_code} - {response.text}")
        if response.status_code != 200:
            logger.error(f"Ollama request failed: {response.status_code} - {response.text}")
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
        new_context = result.get("context", [])

        if not ai_response:
            logger.warning("No content in Ollama response")
            return jsonify({"error": "No response content from AI"}), 500

        cleaned_response = clean_response(ai_response)
        logger.debug(f"Cleaned response: {cleaned_response}")

        if use_context:
            save_context(user_id, new_context)

        return jsonify({
            "choices": [{"message": {"content": cleaned_response}}],
            "context": new_context if use_context else []
        })

    except requests.Timeout:
        logger.error("Request to Ollama timed out")
        return jsonify({"error": "Request timed out. Please try again later."}), 500
    except requests.RequestException as e:
        logger.error(f"Network error: {str(e)}")
        return jsonify({"error": f"Network error: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=6000, debug=False)

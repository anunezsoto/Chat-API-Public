import re
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Context setting (Enable or disable context memory) <-- History
USE_CONTEXT = True

# Ollama server settings
OLLAMA_SERVER = "http://localhost:11434"
OLLAMA_MODEL = "deepseek-r1:1.5b"

# In-memory store for user conversation contexts
user_contexts = {}

def clean_response(response_text):
    """Removes <think> tags and cleans up response."""
    response_text = re.sub(r"<think>.*?</think>", "", response_text, flags=re.DOTALL)
    response_text = re.sub(r"<think>|</think>", "", response_text)
    return response_text.strip()

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_id = data.get("user_id", "default")  # Use a unique ID per user
        user_input = data.get("message", "").strip()
        use_context = data.get("use_context", USE_CONTEXT)  # Default to global setting

        if not user_input:
            return jsonify({"error": "Message is required"}), 400

        # Retrieve or reset user's conversation context
        context = user_contexts.get(user_id, []) if use_context else []

        # Send request to Ollama with context only if enabled
        response = requests.post(
            f"{OLLAMA_SERVER}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": user_input}],
                "stream": False,
                "context": context  # Use context if enabled
            },
            timeout=60
        )

        if response.status_code != 200:
            return jsonify({
                "error": "Failed to get response from Ollama",
                "status": response.status_code,
                "response": response.text
            }), 500

        # Extract AI response
        result = response.json()
        ai_response = result.get("response", "")
        new_context = result.get("context", [])

        # Clean response
        cleaned_response = clean_response(ai_response)

        # Store updated context only if context is enabled
        if use_context:
            user_contexts[user_id] = new_context

        # Return AI response
        return jsonify({
            "choices": [{"message": {"content": cleaned_response}}],
            "context": new_context if use_context else []  # Return empty context if disabled
        })

    except requests.Timeout:
        return jsonify({"error": "Request timed out. Please try again later."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=6000, debug=True)

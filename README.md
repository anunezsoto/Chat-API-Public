# Chat-API-Public 🚀

A Flask-based API for interacting with Ollama models, with customizable settings via an auto-generated `config.json`.

## 📋 Prerequisites

- **Python 3.8+** and `pip` (Python package manager).
- **Ollama**: Ensure Ollama is installed and a model is downloaded.
  - 🐧 **Linux**: [Ollama Linux Setup](https://ollama.com/download/linux)
  - 🪟 **Windows**: [Ollama Windows Setup](https://ollama.com/download/windows)

## 🐧 Linux Setup

1. **Clone and Set Up Environment**  
   Clone the repository and install dependencies:
   ```bash
   cd ~/
   git clone https://github.com/anunezsoto/Chat-API-Public.git
   cd Chat-API-Public
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Ollama Service**  
   Modify the Ollama service to allow external access:
   ```bash
   sudo vim /etc/systemd/system/ollama.service
   ```
   Add or update the `[Service]` section:
   ```ini
   [Service]
   Environment="OLLAMA_ORIGINS=*"
   Environment="OLLAMA_HOST=0.0.0.0:11434"
   ```
   Save and restart:
   ```bash
   sudo systemctl restart ollama.service
   ```

3. **Set Up Flask Service**  
   Create a systemd service for the Flask API (replace `yourusername` with your Linux username):
   ```bash
   sudo su -
   vim /etc/systemd/system/flask_llm.service
   ```
   Paste and update paths (UPDATE WITH YOUR HOME /home/yourusername/Chat-API-Public):
   ```ini
   [Unit]
   Description=Flask API for Ollama
   After=network.target

   [Service]
   User=yourusername
   WorkingDirectory=/home/yourusername/Chat-API-Public
   ExecStart=/home/yourusername/Chat-API-Public/venv/bin/gunicorn -w 1 -b 0.0.0.0:6000 llmapi:app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   Enable and start:
   ```bash
   sudo systemctl enable flask_llm.service
   sudo systemctl start flask_llm.service
   ```
   Verify:
   ```bash
   sudo systemctl status flask_llm.service
   ```

## 🪟 Windows Setup

1. **Clone or Download**  
   - Clone with Git:
     ```bash
     git clone https://github.com/anunezsoto/Chat-API-Public.git
     cd Chat-API-Public
     ```
   - Or download the ZIP from GitHub, unzip, and navigate to the folder.

2. **Set Up Environment**  
   Create and activate a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run the API**  
   Start the API:
   ```bash
   python llmapi.py
   ```
   To run in the background:
   ```bash
   start /b python llmapi.py
   ```

4. **Allow Firewall Access**  
   Allow the API through Windows Defender Firewall (run as Administrator):
   ```bash
   netsh advfirewall firewall add rule name="Flask API" dir=in action=allow protocol=TCP localport=6000
   ```

## ⚙️ Configuration

- A `config.json` file is auto-generated on first run with defaults:
  ```json
  {
    "log_path": "flask.log",
    "ollama_server": "http://localhost:11434",
    "use_context": true,
    "flask_host": "0.0.0.0",
    "flask_port": 6000,
    "flask_debug": false,
    "db_path": "user_contexts.db"
  }
  ```
- Edit `config.json` to customize settings like the Ollama server URL or port.

## 📝 Notes

- The API runs at `http://0.0.0.0:6000` by default.
- Logs are saved to `flask.log`, and the database to `user_contexts.db` in the project directory.
- Ensure the Ollama server is running (default: `http://localhost:11434`).
- For troubleshooting:
  - Linux: Check `sudo journalctl -u ollama` or `flask.log`.
  - Windows: Check `flask.log`.


## 🔹 Configuring ChatAPI

- Configuring ChatAPI
Open the ChatAPI app.
Change API Provider to Custom LLM.
Enter the Hostname/IP in the field:
If using a public IP (not recommended without HTTPS):
Example:
```bash
192.168.1.20
```
If using a domain name (recommended with HTTPS):
```bash
your-domain.com
```
Set a Custom Port (if different from default 6000):
Note: Port 6000 can be changed in the llmapi.py
Example:
```bash
Port: 6000
```
Save the settings and test the connection.



# Optional Config
## 🔹 Configure SSL (NGINX RECOMMENDED)
Now that your API is accessible from outside your network, you can configure ChatAPI to use it securely.
- NGINX config example is availabe in main above. 





🎉 Conclusion

You have now successfully set up and deployed a Flask API with Ollama on Linux, allowing external access through port forwarding. 🚀

For troubleshooting, check the logs:

Install 
  cd ~/
  git clone https://github.com/anunezsoto/Chat-API-Public.git
  cd Chat-API-Public
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt



now edit ollama service and add the env variables:
vim /etc/systemd/system/ollama.service

Add & Save:
Environment="OLLAMA_ORIGINS=*"
Environment="OLLAMA_HOST=0.0.0.0:11434"

Now restart systemctl restart ollama.service



Create the flask service (update the /home/yourusername/llmapi fields with your actual home dir)
sudo su -
vim /etc/systemd/system/flask_llm.service
Paste the following contents into the file (modify paths as needed):

[Unit]
Description=Flask API for Ollama
After=network.target

[Service]
User=yourusername
WorkingDirectory=/home/yourusername/llmapi
ExecStart=/home/yourusername/llmapi/venv/bin/gunicorn -w 1 -b 0.0.0.0:6000 llmapi:app
Restart=always

[Install]
WantedBy=multi-user.target



Now enable and start
systemctl enable flask_llm.service
systemctl start flask_llm.service
To check if the service is running:

systemctl status flask_llm.service

Now add the flask pip env install for windows and instructions on how to run it on windows..
include ways to start 
To start the API, run:

python llmapi.py
If you want to run it in the background, use:

start /b python llmapi.py
Allow Firewall Access (Recommended)
If you're running the API on Windows, you'll need to allow it through the Windows Defender Firewall:

# Allow Flask API port (default: 6000)
netsh advfirewall firewall add rule name="Flask API" dir=in action=allow protocol=TCP localport=6000

# Chat-API-Public


## Flask API Setup with Ollama  

This guide walks you through setting up a Flask API to interface with Ollama and deploy it as a systemd service for stability and automatic startup.  

---

## Prerequisites  

Before proceeding, ensure you have the following installed on your system:  

### **OLLAMA:**
- This setup assumes you already installed Ollama and have downloaded a model.
- Ollama Setup Linux: https://ollama.com/download/linux
- Ollama Setup Windows: https://ollama.com/download/windowshttps://ollama.com/download/windows

### **For Linux:**  
- **Python 3** (Recommended: Python 3.8+)  
- **pip** (Python package manager)  
- **venv** (Python virtual environments)  
- **UFW (Uncomplicated Firewall)** (Optional but recommended for security)  

### **For Windows:**  
- **Python 3** (Recommended: Python 3.8+)  
- **pip** (Python package manager)  
- **venv** (Python virtual environments)  
- **Windows Terminal or Command Prompt**  

---

# 🔹 Linux Setup  

## 1. Set Up the Project Directory  

Run the following commands to create and set up a working environment for the Flask API:  

```bash
# Navigate to home directory and create a project folder
cd ~
mkdir llmapi && cd llmapi

# Create a Python virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install Flask, CORS, and Requests
pip install flask flask-cors requests

# Install Gunicorn for production deployment
pip install gunicorn
```
2. Create the Flask API

Create a Python script named llmapi.py inside your project directory:
```bash
vim llmapi.py
```
Then, paste your Flask API code(llmapi.py) into the file and save it.
Check the llmapi.py file in main above for the latest update. 

3. Set Up systemd Service

To ensure the API runs as a background service and starts automatically, create a systemd service file:
```bash
sudo su -
vim /etc/systemd/system/flask_llm.service
Paste the following contents into the file (modify paths as needed):

[Unit]
Description=Flask API for Ollama
After=network.target

[Service]
User=yourusername
WorkingDirectory=/home/yourusername/llmapi
ExecStart=/home/yourusername/llmapi/venv/bin/gunicorn -w 4 -b 0.0.0.0:6000 llmapi:app
Restart=always

[Install]
WantedBy=multi-user.target
```
Replace yourusername with your actual Linux username.

4. Enable and Start the Service

Run the following commands to enable and start the Flask API service:
```bash
systemctl enable flask_llm.service
systemctl start flask_llm.service
To check if the service is running:

systemctl status flask_llm.service
```
5. Configure Firewall (Recommended)

To allow external access to the API while maintaining security, configure the firewall:
```bash
# Allow SSH access (if using remote access)
ufw allow 22/tcp

# Allow Flask API port (default: 6000)
ufw allow 6000/tcp

# Enable the firewall
ufw enable
```
# 🔹 Windows Setup

If you're setting up the Flask API on Windows, follow these steps instead:

1. Install Python & Required Packages

Download and install Python 3 (if not installed) from python.org.
Open Command Prompt (cmd) or Windows Terminal and run:
```bash
# Create a project directory
mkdir llmapi && cd llmapi

# Create a Python virtual environment
python -m venv venv

# Activate the virtual environment
venv\Scripts\activate

# Install Flask, CORS, and Requests
pip install flask flask-cors requests
```
2. Create the Flask API

Create a Python script named llmapi.py inside your project directory:
```bash
notepad llmapi.py
```
Then, paste your Flask API code(llmapi.py) into the file and save it.
Check the llmapi.py file in main above for the latest update. 

3. Run the Flask API

To start the API, run:
```bash
python llmapi.py
If you want to run it in the background, use:

start /b python llmapi.py
```
4. Allow Firewall Access (Recommended)

If you're running the API on Windows, you'll need to allow it through the Windows Defender Firewall:
```bash
# Allow Flask API port (default: 6000)
netsh advfirewall firewall add rule name="Flask API" dir=in action=allow protocol=TCP localport=6000
```
# 🔹 Configure Port Forwarding

Now that the API is running, you need to allow external devices to connect to it.

1. Log in to your router's admin panel
This is usually accessible via http://192.168.1.1 or http://192.168.0.1.
Check your router's manual for the correct address.

2. Find the Port Forwarding section
This is usually under "Advanced Settings" or "NAT/Port Forwarding."

3. Create a new port forwarding rule
Internal IP Address: Set this to your local machine’s IP (e.g., 192.168.1.100).
Internal Port: 6000
External Port: 6000 (or another open port if 6000 is in use).
Protocol: TCP
Enable the rule and save the settings.

4. Find your public IP address
Run:
```bash
curl ifconfig.me
```
Or 
visit WhatIsMyIP.com

# 🔹 Configure SSL (NGINX RECOMMENDED)
- NGINX config example is availabe in main above. 
- Skip to next step if security is not a concern.

7. Connect ChatAPI to the Ollama Model

Now that your API is accessible from outside your network, you can configure ChatAPI to use it securely.

Recommended: Enable HTTPS for Encryption
To ensure secure communication between your app and the API, we recommend setting up HTTPS with a valid SSL certificate using Certbot (Let's Encrypt).

Step 1: Install Certbot & Generate an SSL Certificate

On your Linux server, run:
```bash
sudo apt update && sudo apt install certbot python3-certbot-nginx -y
Run Certbot to issue a certificate for your domain:

sudo certbot --nginx -d your-domain.com
Replace your-domain.com with your actual domain name.
```
Certbot will automatically configure Nginx for HTTPS. If you're using another web server, such as Apache, use:
```bash
sudo certbot --apache -d your-domain.com
Step 2: Auto-Renew SSL Certificates
```
Certbot automatically renews certificates, but to ensure it's working, run:
```bash
sudo certbot renew --dry-run
Your server is now secured with HTTPS, and you can use https://your-domain.com for encrypted communication.
```

# 🔹 Configuring ChatAPI

8. Configuring ChatAPI
Open the ChatAPI app.
Change API Provider to Custom LLM.
Enter the Hostname/IP in the field:
If using a public IP (not recommended without HTTPS):
Example:
```bash
108.67.190.24
```
If using a domain name (recommended with HTTPS):
```bash
your-domain.com
```
Set a Custom Port (if different from default 6000):
Note: Port 6000 can be changed in the llmapi.py
Example:
```bash
Port: 8080
```
Save the settings and test the connection.


🎉 Conclusion

You have now successfully set up and deployed a Flask API with Ollama on Linux, allowing external access through port forwarding. 🚀

For troubleshooting, check the logs:

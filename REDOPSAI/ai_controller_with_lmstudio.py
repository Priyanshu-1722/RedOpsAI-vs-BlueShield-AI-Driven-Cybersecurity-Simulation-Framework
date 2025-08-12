import paramiko
import requests
import json

# Load config
with open("config.json") as f:
    config = json.load(f)

# LM Studio Prompt
prompt = input("Enter RedOps prompt: ")
headers = {"Content-Type": "application/json"}
data = {
    "model": "local-model",  # Replace with your LM Studio model name like 'llama3'
    "messages": [{"role": "user", "content": prompt}],
    "temperature": 0.7
}

response = requests.post(config["lm_api_url"], headers=headers, json=data)
reply = response.json()
command = reply["choices"][0]["message"]["content"]

print("\n[AI Suggested Command]:", command)

# SSH to Kali (PC2)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(config["ssh_host"], username=config["ssh_username"], password=config["ssh_password"])
stdin, stdout, stderr = ssh.exec_command(command)

print("\n[Remote Output]:\n", stdout.read().decode())
ssh.close()

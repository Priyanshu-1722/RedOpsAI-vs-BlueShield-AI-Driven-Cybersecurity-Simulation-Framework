import paramiko
import os
import time
import smtplib
import json
import requests
from datetime import datetime
from email.message import EmailMessage

ATTACKER_IP = "192.168.1.218"  # PC2
ATTACKER_USERNAME = "redops-attack-engine"
ATTACKER_PASSWORD = "i"

SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
EMAIL_SENDER = 'your_email@gmail.com'
EMAIL_PASSWORD = 'your_app_password'
EMAIL_RECEIVER = 'receiver_email@gmail.com'

LM_STUDIO_ENDPOINT = "http://192.168.56.1:1234/v1/completions"

REMOTE_RESULT_FILE = "/home/kali/redops/nmap_scan.txt"
LOCAL_RESULT_FILE = "nmap_scan_local.txt"
CONVERSATION_LOG_FILE = "redops_ai_conversation_log.jsonl"
FEEDBACK_LOG_FILE = "redops_feedback_log.json"


def connect_ssh():
    print(f"[+] Connecting to attacker {ATTACKER_IP} via SSH...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ATTACKER_IP, username=ATTACKER_USERNAME, password=ATTACKER_PASSWORD)
    return client


def run_remote_command(client, command):
    stdin, stdout, stderr = client.exec_command(command)
    output = stdout.read().decode().strip()
    error = stderr.read().decode().strip()
    return output, error


def run_attack_chain(client, victim_ip):
    print("[+] Checking for offensive tools installed on attacker...")
    run_remote_command(client, "which nmap || sudo apt install -y nmap")
    run_remote_command(client, "which msfconsole || sudo apt install -y metasploit-framework")

    print("[+] Running Nmap scan on victim...")
    run_remote_command(client, f"nmap -sS -T4 -oN {REMOTE_RESULT_FILE} {victim_ip}")

    print("[+] Generating Metasploit RC file...")
    rc_content = f"use auxiliary/scanner/portscan/tcp\nset RHOSTS {victim_ip}\nrun\nexit"
    remote_rc_path = "/home/kali/redops/attack.rc"
    run_remote_command(client, f"mkdir -p /home/kali/redops && echo '{rc_content}' > {remote_rc_path}")

    print("[+] RC file uploaded.")
    print("[+] Launching Metasploit...")
    run_remote_command(client, f"msfconsole -q -r {remote_rc_path}")

    print("[+] Fetching scan result file from attacker to base machine...")
    sftp = client.open_sftp()
    sftp.get(REMOTE_RESULT_FILE, LOCAL_RESULT_FILE)
    sftp.close()
    print(f"[+] File downloaded to: {os.path.abspath(LOCAL_RESULT_FILE)}")

    return LOCAL_RESULT_FILE


def send_email_alert(subject, body):
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg.set_content(body)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)

        print("[+] Email alert sent successfully.")
    except Exception as e:
        print(f"[!] Failed to send email: {e}")


def load_file_contents(filepath):
    with open(filepath, 'r') as f:
        return f.read()


def send_to_lm_studio(prompt):
    payload = {
        "model": "local-model",
        "prompt": prompt,
        "temperature": 0.7,
        "max_tokens": 512
    }
    try:
        response = requests.post(LM_STUDIO_ENDPOINT, json=payload)
        response_data = response.json()
        return response_data.get("response", "No response")
    except Exception as e:
        return f"[!] LM Studio error: {e}"


def save_conversation_history(prompt, response_text):
    with open(CONVERSATION_LOG_FILE, "a") as log:
        log.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "response": response_text
        }) + "\n")


def save_structured_feedback(json_data):
    with open(FEEDBACK_LOG_FILE, "a") as f:
        f.write(json.dumps(json_data) + "\n")


def generate_ai_prompt(log_data):
    tags = []
    tools = log_data['attack_summary']['tools_used']
    if "nmap" in tools:
        tags.append("nmap")
    if "hydra" in tools:
        tags.append("hydra")
    if "metasploit" in tools:
        tags.append("metasploit")
    tag_line = ", ".join(["RedOps"] + tags)

    return f"""
[TAGS: {tag_line}]

You are a RedOps AI system learning from offensive cyber operations.

Here's a new attack log:
Victim IP: {log_data['victim_ip']}
Attacker IP: {log_data['attacker_ip']}
Timestamp: {log_data['timestamp']}
Tools Used: {', '.join(tools)}
Result File: {log_data['attack_summary']['result_file']}
Status: {log_data['status']}

Learn from this data and update your internal RedOps intelligence.
"""


def main():
    victim_ip = input("Enter victim IP (PC3): ")
    client = connect_ssh()
    local_file = run_attack_chain(client, victim_ip)
    client.close()

    log_data = {
        "victim_ip": victim_ip,
        "attacker_ip": ATTACKER_IP,
        "timestamp": datetime.now().isoformat(),
        "attack_summary": {
            "tools_used": ["nmap", "metasploit"],
            "result_file": os.path.abspath(local_file)
        },
        "status": "completed"
    }

    prompt = generate_ai_prompt(log_data)
    ai_response = send_to_lm_studio(prompt)
    save_conversation_history(prompt, ai_response)
    save_structured_feedback(log_data)

    send_email_alert(
        "[RedOps AI] New Attack Executed",
        f"RedOps attack on victim {victim_ip} completed.\n\nResult file: {os.path.abspath(local_file)}\n\nAI Response:\n{ai_response}"
    )


if __name__ == '__main__':
    main()

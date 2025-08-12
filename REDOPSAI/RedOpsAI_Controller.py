import paramiko
import requests
import json
import time
from datetime import datetime

# === CONFIGURATION ===
LM_STUDIO_API = "http://localhost:1234/v1/completions"  # LM Studio endpoint
LM_MODEL = "llama-3.1-8b-lexi-uncensored-v2:2"           # Update as per your LM Studio
KALI_IP = "192.168.1.218"
KALI_USER = "redops-attack-engine"
KALI_PASS = "i"  # Prefer SSH key for security
OUTPUT_FILE = "attack_report.json"

# === Get target IP/domain ===
victim = input("Enter the target/victim IP or domain (e.g., 192.168.80.133): ")

# === Ask LM Studio for attack command ===
def ask_lmstudio(victim_ip):
    headers = {"Content-Type": "application/json"}
    prompt = (
        f"Generate a one-line offensive Linux command using nmap, hydra, sqlmap, metasploit (msfconsole -x), or OpenVAS "
        f"to test or attack the target: {victim_ip}. Respond with the full CLI command only."
    )
    payload = {
        "model": LM_MODEL,
        "prompt": prompt,
        "temperature": 0.7,
        "max_tokens": 200
    }

    try:
        response = requests.post(LM_STUDIO_API, headers=headers, data=json.dumps(payload))
        result = response.json()
        command = result['choices'][0]['text'].strip()
        return command
    except Exception as e:
        print(f"[!] Error querying LM Studio: {e}")
        return None

# === Execute command on Kali Linux via SSH ===
def execute_ssh_command(command):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(KALI_IP, username=KALI_USER, password=KALI_PASS)
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        client.close()
        return output.strip(), error.strip()
    except Exception as e:
        return "", f"SSH Error: {e}"

# === Feed report back to LM Studio (optional) ===
def feedback_to_ai(report):
    prompt = f"Analyze the following output from a previous attack attempt:\n\n{json.dumps(report, indent=2)}\n\nSuggest the next logical command to chain or escalate the attack."
    payload = {
        "model": LM_MODEL,
        "prompt": prompt,
        "temperature": 0.8,
        "max_tokens": 250
    }
    try:
        response = requests.post(LM_STUDIO_API, headers={"Content-Type": "application/json"}, data=json.dumps(payload))
        result = response.json()
        suggestion = result['choices'][0]['text'].strip()
        print("[*] LM Studio Chained Suggestion:\n", suggestion)
    except Exception as e:
        print(f"[!] Error feeding back to LM Studio: {e}")

# === Main loop ===
def main():
    while True:
        print(f"\n[*] Asking LM Studio for attack on {victim}...")
        attack_cmd = ask_lmstudio(victim)
        if not attack_cmd:
            time.sleep(60)
            continue

        print("[+] AI Suggested Command:\n", attack_cmd)
        print("[*] Executing on Kali Attacker...")

        output, error = execute_ssh_command(attack_cmd)

        timestamp = datetime.now().isoformat()
        report = {
            "timestamp": timestamp,
            "victim": victim,
            "ai_command": attack_cmd,
            "output": output,
            "error": error
        }

        # Save report
        print("[+] Saving report...")
        with open(OUTPUT_FILE, "a") as f:
            f.write(json.dumps(report, indent=2) + ",\n")

        # Feed back to AI
        feedback_to_ai(report)

        print("[✓] Done. Sleeping 60 seconds...\n")
        time.sleep(60)

if __name__ == "__main__":
    main()

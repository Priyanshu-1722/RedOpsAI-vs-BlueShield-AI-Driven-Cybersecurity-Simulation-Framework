import json
import os
from datetime import datetime

# Input: JSON logs from RedOps runs
LOG_FILE = "redops_ai_logs.json"

# Output: Fine-tuning dataset for LM Studio (Q&A pairs or instruction format)
OUTPUT_FILE = "fine_tune_dataset.jsonl"

def convert_to_instruction_format(logs):
    fine_tune_data = []

    for log in logs:
        # Extract high-level summary as instruction
        instruction = f"Run {log.get('tool', 'RedOps')} against target {log.get('victim_ip', 'unknown')}"

        # Include timestamp, attacker IP, and attacker actions as context
        context = f"""
        Timestamp: {log.get('timestamp')}
        Attacker IP: {log.get('attacker_ip')}
        Victim IP: {log.get('victim_ip')}
        Tool: {log.get('tool')}
        Commands: {log.get('command')}
        Output Snippet: {log.get('output')[:300] if log.get('output') else "None"}
        """

        # Format as per LM Studio fine-tuning prompt/response pair
        fine_tune_data.append({
            "prompt": instruction.strip(),
            "completion": context.strip()
        })

    return fine_tune_data

def main():
    if not os.path.exists(LOG_FILE):
        print(f"[!] Log file not found: {LOG_FILE}")
        return

    with open(LOG_FILE, "r") as f:
        logs = json.load(f)

    print(f"[+] Loaded {len(logs)} log entries...")

    fine_tune_data = convert_to_instruction_format(logs)

    # Save as JSONL
    with open(OUTPUT_FILE, "w") as out_file:
        for entry in fine_tune_data:
            json.dump(entry, out_file)
            out_file.write("\n")

    print(f"[+] Fine-tuning dataset saved as {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

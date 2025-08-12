import os
import subprocess

LMSTUDIO_PATH = r"C:\Program Files\LM Studio\LM Studio.exe"
DATASET_PATH = r"C:\RedOpsAI\fine_tune_dataset.jsonl"

def launch_lm_studio():
    if not os.path.exists(LMSTUDIO_PATH):
        print("[!] LM Studio not found!")
        return

    print("[+] Launching LM Studio...")
    subprocess.Popen([LMSTUDIO_PATH])

    # Optional: Add automation here if LM Studio supports CLI/API fine-tuning.
    # E.g., via `lmstudio train --dataset fine_tune_dataset.jsonl`

if __name__ == "__main__":
    launch_lm_studio()

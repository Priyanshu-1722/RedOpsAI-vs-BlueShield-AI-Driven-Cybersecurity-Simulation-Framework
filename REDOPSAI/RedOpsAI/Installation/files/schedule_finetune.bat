@echo off
cd /d C:\RedOpsAI

:: Step 1: Prepare dataset from logs
python fine_tune_prep.py

:: Step 2: Launch LM Studio
python train_with_lmstudio.py

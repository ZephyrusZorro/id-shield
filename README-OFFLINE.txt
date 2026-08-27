ID-SHIELD — OFFLINE PACKAGE
Explainable Identity & Document Forensics Platform
====================================================

Everything in this package runs 100% on your PC. No internet connection is
required once setup is complete. All documents you screen stay on your device.

WHAT YOU NEED ON THE TARGET PC
------------------------------
1. Python 3.11 or newer          https://www.python.org/downloads/
   (tick "Add python.exe to PATH" during install)
2. Tesseract OCR 5               winget install UB-Mannheim.TesseractOCR
   or download the UB-Mannheim installer; for air-gapped PCs place the
   installer .exe inside this folder and run it manually.
3. (Only if frontend/dist was NOT included) Node.js — not needed when
   frontend\dist exists, which it does in this package.

FIRST-TIME SETUP (internet needed unless wheels\ is included)
-------------------------------------------------------------
Right-click Start -> Windows PowerShell, then:

    cd path\to\this\folder
    powershell -ExecutionPolicy Bypass -File scripts\setup_offline.ps1

If a wheels\ folder is included (fully offline install):

    powershell -ExecutionPolicy Bypass -File scripts\setup_offline.ps1 -UseWheels

START THE APP (everyday use)
----------------------------
Double-click:   start_idshield.bat
The app opens at http://localhost:8000 and works with Wi-Fi turned off.

QUICK TOUR
----------
* Screen Documents -> "Load Demo Case" -> watch the pipeline -> explore the
  evidence tabs (Documents / Validation / Comparison / Forensics / Report).
* Seed the full demo dataset:
      cd backend
      ..\.venv\Scripts\python -m demo.seed_cases

RESET ALL DATA
--------------
Delete the  backend\data\  folder.

NOTES
-----
* Everything is synthetic demo data; no real identity documents are included.
* This software only ASSISTS verification - final decisions belong to
  authorized human personnel.

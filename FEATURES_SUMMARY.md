# ID-SHIELD: Features & Document Verification Workflow Summary

This document explains all the features, workflow modules, and recent biometric enhancements implemented in **ID-SHIELD** in simple, plain English.

---

## 1. Smart Face Detection & Biometric Comparison
* **The Problem It Solves**: On Indian ID cards, there are often faint background security watermarks (such as Mahatma Gandhi in the center of a PAN card) and sharp printed text. Previously, the computer got confused and cropped the watermark or text instead of the actual human face, causing false "Facial Photo Mismatch" alerts.
* **What Was Implemented**: We upgraded the face detector to look for **real human skin tones (HSV color analysis)** and facial landmarks (eyes, facial structure).
* **The Result**: 
  - It automatically ignores printed black lettering and ghost-like card watermarks.
  - Accurately crops the real photo portrait on both Aadhaar (`[36, 137, 82, 82]`) and PAN cards (`[421, 274, 71, 71]`).
  - Correctly verifies that the same person is pictured across both documents with **98.7% local texture consistency**.

---

## 2. Image Quality Check Gate *(Workflow Module 2)*
* **What It Does**: Before the system tries to read words or numbers on an ID card, it checks the image clarity:
  * **Sharpness / Blur**: Is the photo in focus, or is it too blurry to read?
  * **Resolution**: Does the photo have enough pixels for accurate OCR?
  * **Glare / Overexposure**: Is there camera flash or a light reflection blinding part of the card?
* **Why It Matters**: If a user uploads an unreadable or glare-covered document, the system warns the officer: *"Image quality is poor — please inspect this manually before trusting the computer's reading."*

---

## 3. Evidence Fusion Matrix & "Majority Voting" *(Workflow Modules 4, 5, 6 & 13)*
* **What It Does**: Cross-checks all available evidence for every personal field (Full Name, Date of Birth, Document Number) across:
  1. Printed text read by OCR
  2. The digital QR code
  3. The Passport MRZ code (the code at the bottom of international passports)
  4. Any other uploaded document
* **How It Helps**: Instead of failing the entire application over a single minor typo, it uses **majority consensus**:
  - *Example*: If Aadhaar, PAN, and the printed card all agree on Date of Birth *10/01/1993*, but a single QR code has a slight discrepancy, it points out: *"3 out of 4 sources agree on 1993 — only the QR payload differs."*
  - Allows compliance officers to isolate isolated errors without rejecting authentic applicants.

---

## 4. Interactive Evidence Graph *(Workflow Module 12)*
* **What It Does**: A visual connection diagram on the **Comparison & Fusion** tab:
  * **Center Circle**: The applicant subject.
  * **Middle Circles**: The uploaded documents (Aadhaar, PAN, Passport).
  * **Outer Circles**: The extracted data attributes (Name, DOB, ID number).
* **Visual Lines**:
  * **Glowing Green Lines**: Everything matches and connects cleanly across documents.
  * **Pulsing Red Lines**: Highlights where there is a conflict between documents.
  * Clicking on any bubble opens an interactive drawer showing the raw extracted text and confidence percentage.

---

## 5. Suspicious Text Replacement Detection *(Workflow Module 10)*
* **What It Does**: A digital forensics tool that spots localized document tampering and digital forgery.
* **How It Works**: If a fraudster uses Photoshop or an image editor to paste a fake name or altered date over an existing card, the pixels around that text will have slightly different background tones and sharp rectangular edges. The system automatically detects these pixel borders and flags the altered text as suspicious.

---

## 6. Spoken Voice Assistant Briefing
* **What It Does**: An accessibility tool that summarizes the entire case out loud in plain, friendly English.
* **Why It Helps**: Perfect for busy review officers or elderly applicants who prefer listening rather than reading dense tables:
  * *"Hello. For this application, we processed 2 identity documents. Personal details match, and photos show consistent facial features. Recommended: Verification Passed."*
  * Responds to voice questions like *"Are there any discrepancies?"* or *"Does this card look edited?"*.

---

## 7. Indian Multilingual OCR Extension Preview *(Workflow Module 14)*
* **What It Does**: Added system support indicators for regional Indian languages (Hindi, Kannada, Urdu, Malayalam, Tamil, Telugu) so officers know the platform is ready to process vernacular identity cards.

---

## Quick Reference Summary

| Subsystem | Where to View in UI | What to Look For |
| :--- | :--- | :--- |
| **Face Biometrics** | `Face Biometrics` Tab | Real portraits cropped from both cards, sharpness scores, Genuine Photo badges. |
| **Image Quality Gate** | `Validation Checklist` Tab | Green pass badge or amber warning indicating blur/glare status. |
| **Evidence Graph** | `Comparison & Fusion` Tab | Visual node map connecting Person $\rightarrow$ Documents $\rightarrow$ Fields. |
| **Fusion Matrix** | `Comparison & Fusion` Tab | Multi-source consensus table showing agreement across OCR, QR, and MRZ. |
| **Forensics** | `Forensics` Tab | Error Level Analysis (ELA) heatmap and copy-move/tampering detection. |
| **Voice Assistant** | Header bar / Floating mic | Click to hear a spoken briefing of the case. |

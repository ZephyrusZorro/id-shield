"""Interactive / quick diagnostic tool to verify SMTP credentials."""
import sys
import smtplib
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.core.config import settings

def test_smtp(email=None, password=None, host="smtp.gmail.com", port=587):
    email = email or settings.smtp_user
    password = password or settings.smtp_pass
    host = host or settings.smtp_host or "smtp.gmail.com"
    port = port or settings.smtp_port or 587

    if not email or not password:
        print("❌ Error: Missing SMTP_USER or SMTP_PASS in .env")
        return False

    clean_pass = password.replace(" ", "").strip()
    print(f"\n[+] Connecting to {host}:{port}...")
    try:
        server = smtplib.SMTP(host, port, timeout=12)
        server.starttls()
        print(f"[+] Authenticating as '{email}'...")
        server.login(email.strip(), clean_pass)
        print(f"[OK] SUCCESS! Successfully authenticated to Google SMTP.")
        
        # Test sending a test email to self
        print(f"[+] Sending verification test email to '{email}'...")
        msg = (
            f"From: {email}\r\n"
            f"To: {email}\r\n"
            f"Subject: ID-SHIELD SMTP Verification Test\r\n\r\n"
            f"Hello!\r\n\r\nYour ID-SHIELD SMTP configuration is working perfectly.\r\n"
            f"You can now dispatch real discrepancy alerts directly to applicant inboxes.\r\n"
        )
        server.sendmail(email, [email], msg)
        server.quit()
        print(f"[OK] TEST EMAIL DELIVERED! Check your inbox ({email}).\n")
        return True
    except smtplib.SMTPAuthenticationError as exc:
        print(f"\n[X] AUTHENTICATION FAILED (Error 535 BadCredentials):")
        print(f"   Google rejected the username or app password.")
        print(f"   - User: {email}")
        print(f"   - App Password length: {len(clean_pass)} chars (expected 16)")
        print(f"   Details: {exc}\n")
        return False
    except Exception as exc:
        print(f"\n[X] CONNECTION ERROR: {exc}\n")
        return False

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        test_smtp(sys.argv[1], sys.argv[2])
    else:
        test_smtp()

"""
SMTP Connection Test Script
Run this to diagnose email sending issues.
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Your Brevo SMTP settings
SMTP_HOST = 'smtp-relay.brevo.com'
SMTP_PORT = 587
SMTP_USER = '8994af002@smtp-brevo.com'
SMTP_PASSWORD = 'xsmtpsib-8504de261c0de193f35b64f10733e3185d4399daa3b2d72b7abc0937beed437c-LGYt1GlmiIPc3Jwn'
FROM_EMAIL = 'no-reply@pctsb-travel.site'
TO_EMAIL = 'test@example.com'  # Change this to your email

def test_smtp_connection():
    """Test SMTP connection with detailed error reporting."""
    print("=" * 60)
    print("SMTP Connection Test")
    print("=" * 60)

    # Test 1: Basic socket connection
    print("\n1. Testing basic socket connection...")
    try:
        import socket
        sock = socket.create_connection((SMTP_HOST, SMTP_PORT), timeout=10)
        print(f"✓ Successfully connected to {SMTP_HOST}:{SMTP_PORT}")
        sock.close()
    except Exception as e:
        print(f"✗ Socket connection failed: {e}")
        print("  - Check your internet connection")
        print("  - Check if firewall/antivirus is blocking port 587")
        return False

    # Test 2: SMTP connection
    print("\n2. Testing SMTP connection...")
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
        print(f"✓ SMTP connection established")

        # Test 3: EHLO
        print("\n3. Testing EHLO handshake...")
        code, message = server.ehlo()
        if 200 <= code <= 299:
            print(f"✓ EHLO successful (code: {code})")
        else:
            print(f"✗ EHLO failed with code: {code}")
            server.quit()
            return False

        # Test 4: STARTTLS
        print("\n4. Testing STARTTLS...")
        try:
            server.starttls()
            print(f"✓ STARTTLS successful")
        except Exception as e:
            print(f"✗ STARTTLS failed: {e}")
            print("\nTrying alternative STARTTLS with custom context...")
            try:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                server.starttls(context=context)
                print(f"✓ STARTTLS successful with relaxed SSL")
            except Exception as e2:
                print(f"✗ Alternative STARTTLS also failed: {e2}")
                server.quit()
                return False

        # Test 5: EHLO after STARTTLS
        print("\n5. Testing EHLO after STARTTLS...")
        code, message = server.ehlo()
        if 200 <= code <= 299:
            print(f"✓ EHLO after STARTTLS successful")
        else:
            print(f"✗ EHLO after STARTTLS failed")
            server.quit()
            return False

        # Test 6: Authentication
        print("\n6. Testing authentication...")
        try:
            server.login(SMTP_USER, SMTP_PASSWORD)
            print(f"✓ Authentication successful")
        except smtplib.SMTPAuthenticationError as e:
            print(f"✗ Authentication failed: {e}")
            print("  - Check your EMAIL_HOST_USER and EMAIL_HOST_PASSWORD")
            print("  - Verify credentials at: https://app.brevo.com/settings/keys/smtp")
            server.quit()
            return False
        except Exception as e:
            print(f"✗ Login error: {e}")
            server.quit()
            return False

        # Test 7: Send test email
        print("\n7. Testing email send...")
        print(f"   Sending test email to: {TO_EMAIL}")

        msg = MIMEMultipart()
        msg['From'] = FROM_EMAIL
        msg['To'] = TO_EMAIL
        msg['Subject'] = 'SMTP Test - SynTra TMS'

        body = "This is a test email from SynTra TMS SMTP configuration."
        msg.attach(MIMEText(body, 'plain'))

        try:
            server.send_message(msg)
            print(f"✓ Test email sent successfully!")
        except Exception as e:
            print(f"✗ Failed to send email: {e}")
            server.quit()
            return False

        server.quit()
        print("\n" + "=" * 60)
        print("All tests passed! SMTP is configured correctly.")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"✗ SMTP test failed: {e}")
        return False

if __name__ == '__main__':
    print("\nBefore running this test:")
    print(f"1. Make sure you have internet connectivity")
    print(f"2. Check if firewall/antivirus allows outbound connections on port {SMTP_PORT}")
    print(f"3. Update TO_EMAIL variable to your email address for testing")
    print()

    test_smtp_connection()

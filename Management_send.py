import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64
import os
from dotenv import load_dotenv

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(SCRIPT_DIR, 'static')

def get_base64_image(image_path):
    """Convert image to base64 string."""
    try:
        with open(image_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"[ERROR] Unable to encode image {image_path}: {e}")
        return None

def send_subs_management_email_to_user(recipient_email):
    """
    Build a 'Management' HTML email and send it to 'recipient_email'.
    """
    # Email configuration
    sender = "newsletter@homesmartify.lu"
    sender_password = os.environ.get("EMAIL_PASSWORD")  # or app-specific password
    subject = "Manage Your AI Newsletter!"

    # Contact information
    contact = {
        "contact_phone": "+352 1234567",
        "contact_mail": "info@homesmartify.lu",
        "contact_web": "www.homesmartify.lu"
    }

    # Build subscription management link
    manage_link = f"https://www.ainewsletter.homesmartify.lu/management/?email={recipient_email}"

    # Convert images to base64
    images = {
        'company_logo': get_base64_image(os.path.join(STATIC_DIR, 'company_logo.png')),
        'phone_icon': get_base64_image(os.path.join(STATIC_DIR, 'phone.png')),
        'email_icon': get_base64_image(os.path.join(STATIC_DIR, 'mail.png')),
        'web_icon': get_base64_image(os.path.join(STATIC_DIR, 'web.png'))
    }

    # Create message container
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient_email

    # Plain text fallback
    text_part = MIMEText("Manage your DeepTech Digest Newsletter", 'plain')
    msg.attach(text_part)

    # Final HTML email with base64-embedded images
    welcome_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Manage Your DeepTech Digest Newsletter</title>
      <style type="text/css">
        :root {{
          --bg-color: linear-gradient(135deg, #add8e6, #ffffe0);
          --text-color: #333333;
          --title-color: #007AFF;
          --welcome-color: #34C759;
          --link-color: #34AADC;
          --box-bg: rgba(255,255,255,0.3);
          --footer-color: #666;
        }}

        @media (prefers-color-scheme: dark) {{
          :root {{
            --bg-color: #1a1a1a;
            --text-color: #ffffff;
            --title-color: #4a9eff;
            --welcome-color: #4cd964;
            --link-color: #4a9eff;
            --box-bg: rgba(255,255,255,0.1);
            --footer-color: #a0a0a0;
          }}
        }}

        body {{
          margin: 0;
          padding: 0;
          font-family: Arial, sans-serif;
          background: var(--bg-color);
          color: var(--text-color);
        }}
        .newsletter-title {{
          font-family: 'Titan One', sans-serif;
          font-size: 36px;
          color: var(--title-color);
          text-align: center;
          margin-bottom: 20px;
        }}
        .welcome-title {{
          font-family: 'Poppins', sans-serif;
          font-size: 30px;
          color: var(--welcome-color);
          text-align: center;
          margin: 0 auto 20px auto;
        }}
        .intro-text {{
          font-family: 'Nunito', sans-serif;
          font-size: 16px;
          color: var(--text-color);
          margin: 0 40px 20px;
          max-width: 700px;
          text-align: left;
          line-height: 1.6;
        }}
        a.manage-link {{
          color: var(--link-color);
          text-decoration: none;
          font-weight: bold;
          padding: 8px 16px;
          background: rgba(74, 158, 255, 0.1);
          border-radius: 6px;
          transition: all 0.3s ease;
        }}
        a.manage-link:hover {{
          background: rgba(74, 158, 255, 0.2);
          text-decoration: underline;
        }}
        .content-box {{
          background: var(--box-bg);
          border-radius: 12px;
          padding: 20px;
          margin: 20px auto 20px auto;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        @media only screen and (max-width: 600px) {{
          .newsletter-title {{
            font-size: 28px !important;
          }}
          .welcome-title {{
            font-size: 26px !important;
          }}
          .intro-text {{
            font-size: 20px !important;
            margin: 0 20px 15px !important;
          }}
          .manage-link {{
            font-size: 20px !important;
          }}
        }}
      </style>
    </head>
    <body style="background:var(--bg-color); font-family:'Nunito', Arial, sans-serif;">
      <table width="100%" cellspacing="0" cellpadding="0">
        <tr>
          <td align="center">
            <table width="600" cellpadding="0" cellspacing="0" style="border-spacing:0; border-collapse:collapse;">
              <tr>
                <td align="center" style="padding:20px;">
                  <!-- HEADER AREA -->
                  <table width="100%" style="background:var(--box-bg); border-radius:12px; padding:20px;">
                    <tr>
                      <td align="center" class="newsletter-title">
                        Manage your DeepTech Digest subscription
                      </td>
                    </tr>
                  </table>
                  <!-- INTRO AREA -->
                  <div class="content-box">
                    <h2 class="welcome-title">Subscription Management</h2>
                    <p class="intro-text">
                      Thank you for subscribing to our Deep Digest newsletter. We value your preferences and privacy. You can easily manage your subscription preferences or unsubscribe at any time by following the link below:
                      <a href="{manage_link}" target="_blank" class="manage-link">Manage Subscription</a>
                    </p>
                  </div>

                  <!-- COMPANY LOGO -->
                  <div style="text-align:center !important; margin-bottom:10px;">
                    <img src="data:image/png;base64,{images['company_logo']}" alt="Company Logo" style="display:block; width:140px !important; height:auto; margin:0 auto;">
                  </div>  
                  
                  <!-- CONTACT AREA -->
                  <div style="text-align:center; margin-top:20px;">
                    <div style="display:flex; justify-content:center; gap:15px;">
                      <img src="data:image/png;base64,{images['phone_icon']}" alt="Phone" style="width:20px; height:20px;">
                      <span style="font-size:14px; color:var(--text-color);">{contact['contact_phone']}</span>
                      <span style="font-size:14px; color:var(--text-color);">|</span>
                      <img src="data:image/png;base64,{images['email_icon']}" alt="Email" style="width:20px; height:20px;">
                      <span style="font-size:14px; color:var(--text-color);">{contact.get('contact_mail','')}</span>
                      <span style="font-size:14px; color:var(--text-color);">|</span>
                      <img src="data:image/png;base64,{images['web_icon']}" alt="Website" style="width:20px; height:20px;">
                      <span style="font-size:14px; color:var(--text-color);">{contact.get('contact_web','')}</span>
                    </div>
                  </div>

                  <!-- FOOTER AREA -->
                  <div style="text-align:center; font-size:12px; color:var(--footer-color); margin-top:15px; background:transparent;">
                    &copy; 2025 HomeSmartify.lu<br>
                    Transforming Technology: Where Smart Technology Meets Caring Comfort.<br>
                    Luxembourg City, Luxembourg 1329
                  </div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """
    msg.attach(MIMEText(welcome_html, "html"))

    # Send the email
    with smtplib.SMTP("smtp.openxchange.eu", 587) as server:
        server.starttls()
        server.login(sender, sender_password)
        server.sendmail(sender, recipient_email, msg.as_string())

    print(f"[DEBUG] Sent welcome email to {recipient_email}")


if __name__ == "__main__":
    load_dotenv()
    test_email = "yagebin79386@gmail.com"
    send_subs_management_email_to_user(test_email)

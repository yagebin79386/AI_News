import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import psycopg2
import psycopg2.extras
from urllib.parse import quote
import os
from dotenv import load_dotenv

def send_welcome_email_to_user(recipient_email):
    """
    Build a 'Welcome' HTML email and send it to 'recipient_email'.
    """
    # Email configuration
    sender = "newsletter@homesmartify.lu"
    sender_password = os.environ.get("EMAIL_PASSWORD")  # or app-specific password
    subject = "Welcome to DeepTech Digest!"

    # Contact information
    contact = {
        "contact_phone": "+352 1234567",
        "contact_mail": "info@homesmartify.lu",
        "contact_web": "www.homesmartify.lu"
    }

    # Build subscription management link
    manage_link = f"https://www.ainewsletter.homesmartify.lu/?email={recipient_email}"


    msg_root = MIMEMultipart('related')
    msg_root['Subject'] = subject
    msg_root['From'] = sender
    msg_root['To'] = recipient_email
    

    # Create a nested 'alternative' part for plain text and HTML.
    msg_alternative = MIMEMultipart('alternative')
    msg_root.attach(msg_alternative)

    # Plain text fallback.
    text_part = MIMEText("Welcome to our ", 'plain')
    msg_alternative.attach(text_part)

    # Final HTML email (all surplus parts removed and newsletter title fixed)
    welcome_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Welcome to DeepTech Digest</title>
      <style type="text/css">
        body {{
          margin: 0;
          padding: 0;
          font-family: Arial, sans-serif;
          background: linear-gradient(135deg, #add8e6, #ffffe0);
          color: #333333;
        }}
        .newsletter-title {{
          font-family: 'Titan One', sans-serif;
          font-size: 36px;
          color: #007AFF;
          text-align: center;
          margin-bottom: 20px;
        }}
        .welcome-title {{
          font-family: 'Poppins', sans-serif;
          font-size: 30px;
          color: #34C759;
          text-align: center;
          margin: 0 auto 20px auto;
        }}
        .intro-text {{
          font-family: 'Nunito', sans-serif;
          font-size: 16px;
          color: #333;
          margin: 0 40px 20px;
          max-width: 700px;
          text-align: left;
        }}
        a.manage-link {{
          color: #34AADC;
          text-decoration: none;
        }}
        .content-box {{
          background: rgba(255,255,255,0.3);
          border-radius: 12px;
          padding: 20px;
          margin: 20px auto 20px auto;
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
    <body style="background:linear-gradient(135deg, #add8e6, #ffffe0); font-family:'Nunito', Arial, sans-serif;">
      <table width="100%" cellspacing="0" cellpadding="0">
        <tr>
          <td align="center">
            <table width="600" cellpadding="0" cellspacing="0" style="border-spacing:0; border-collapse:collapse;">
              <tr>
                <td align="center" style="padding:20px;">
                  <!-- HEADER AREA -->
                  <table width="100%" style="background:rgba(255,255,255,0.3); border-radius:12px; padding:20px;">
                    <tr>
                      <td align="center" class="newsletter-title">
                        WELCOME TO DEEPTECH DIGEST
                      </td>
                    </tr>
                  </table>
                  <!-- INTRO AREA -->
                  <div class="content-box">
                    <h2 class="welcome-title">Welcome Aboard!</h2>
                    <p class="intro-text">
                      We’re excited to bring you the latest insights, breakthroughs, and trends in artificial intelligence — from cutting-edge research and enterprise adoption to the real-world impact of AI on how we live, work, and learn.
                    </p>
                    <p class="intro-text">
                      To manage your subscription preferences or unsubscribe at any time, please visit:
                      <a href="{manage_link}" target="_blank" class="manage-link">Manage Subscription</a>
                    </p>
                  </div>

                  <!-- COMPANY LOGO -->
                  <div style="text-align:center !important; margin-bottom:10px;">
                    <img src="cid:company_logo" alt="Company Logo" style="display:block; width:140px !important; height:auto; margin:0 auto;">
                  </div>  
                  
                  <!-- CONTACT AREA -->
                  <div style="text-align:center; margin-top:20px;">
                    <div style="display:flex; justify-content:center; gap:15px;">
                      <img src="cid:phone_icon" alt="Phone" style="width:20px; height:20px;">
                      <span style="font-size:14px;">{contact['contact_phone']}</span>
                      <span style="font-size:14px;">|</span>
                      <img src="cid:email_icon" alt="Email" style="width:20px; height:20px;">
                      <span style="font-size:14px;">{contact.get('contact_mail','')}</span>
                      <span style="font-size:14px;">|</span>
                      <img src="cid:web_icon" alt="Website" style="width:20px; height:20px;">
                      <span style="font-size:14px;">{contact.get('contact_web','')}</span>
                    </div>
                    <!-- FOOTER AREA -->
                    <div class="company-footer" style="text-align:center; font-size:12px; color:#666; margin-top:15px;">
                      &copy; 2025 HomeSmartify.lu<br>
                      Transforming Technology: Where Smart Technology Meets Caring Comfort.<br>
                      Luxembourg City, Luxembourg 1329
                    </div>
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
    msg_alternative.attach(MIMEText(welcome_html, "html"))

    # Load icon from the static folder
    # Define the images to attach with their corresponding CIDs.
    images = {
        'company_logo': 'static/company_logo.png',
        'phone_icon': 'static/phone.png',
        'email_icon': 'static/mail.png',
        'web_icon': 'static/web.png'
    }



      # Attach each image as MIMEImage with the correct Content-ID
    for cid, image_path in images.items():
        try:
            with open(image_path, 'rb') as f:
                img_data = f.read()
            mime_img = MIMEImage(img_data)
            mime_img.add_header('Content-ID', f'<{cid}>')
            mime_img.add_header('Content-Disposition', 'inline', filename=image_path)
            msg_root.attach(mime_img)
        except Exception as e:
            print(f"[ERROR] Unable to attach {image_path}: {e}")

    # Send the email
    with smtplib.SMTP("smtp.openxchange.eu", 587) as server:
        server.starttls()
        server.login(sender, sender_password)
        server.sendmail(sender, recipient_email, msg_root.as_string())

    print(f"[DEBUG] Sent welcome email to {recipient_email}")


if __name__ == "__main__":
    load_dotenv()
    test_email = "yagebin79386@gmail.com"
    send_welcome_email_to_user(test_email)

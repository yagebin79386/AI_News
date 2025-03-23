import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from urllib.parse import quote
import psycopg2
import psycopg2.extras
from urllib.parse import urlparse
import os


class SendNewsletter:
    def __init__(self, db_config):
        self.conn = psycopg2.connect(
            dbname=db_config["dbname"],
                user=db_config["user"],
                password=db_config["password"],
                host=db_config["host"],
                cursor_factory=psycopg2.extras.RealDictCursor,
        )


    def get_subscribers(self):
        conn=self.conn      
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM subscriber")
        rows = cursor.fetchall()
        return [row.get('email') for row in rows]

    def send_email(self, recipient, subject):
        conn = self.conn
        cursor = conn.cursor()
        cursor.execute("SELECT html FROM newsletter order by creation desc limit 1")
        html_row = cursor.fetchone()
        html_content = html_row['html']
        replaced_html = html_content.replace("{EMAIL}", quote(recipient))

        sender = 'newsletter@homesmartify.lu'
        password = 'jngo-aajx-zohu-zmxe'

        # Outer container: 'related' type to support inline images.
        msg_root = MIMEMultipart('related')
        msg_root['Subject'] = subject
        msg_root['From'] = sender
        msg_root['To'] = recipient

        # Create an 'alternative' part to include both plain text and HTML.
        msg_alternative = MIMEMultipart('alternative')
        msg_root.attach(msg_alternative)

        # Plain-text fallback
        text_part = MIMEText("Plain text fallback here", 'plain')
        msg_alternative.attach(text_part)
        # HTML part
        html_part = MIMEText(replaced_html, 'html')
        msg_alternative.attach(html_part)

        # Define the images to attach with their corresponding CIDs.
        images = {
            'company_logo': 'static/company_logo.png',
            'phone_icon': 'static/phone.png',
            'email_icon': 'static/mail.png',
            'web_icon': 'static/web.png',
            'copylink_icon':'static/link.png',
            'twitter_icon':'static/twitter.png',
            'whatsapp_icon':'static/whatsapp.png'
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

          
        # Connect to SMTP server and send email
        server = smtplib.SMTP('smtp.openxchange.eu', 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg_root.as_string())
        server.quit()


    def send_newsletter(self):
        subscribers = self.get_subscribers()
        subject = "DeepTech Digest: Your AI News Update"
        for email in subscribers:  
            self.send_email(email, subject)
            print(f"Newsletter to {email} has been sent.")

if __name__ == "__main__":
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("❌ DATABASE_URL environment variable not set.") 
    parsed_url = urlparse(db_url)
    db_config = {
        "dbname": parsed_url.path[1:],  # skip leading slash
        "user": parsed_url.username,
        "password": parsed_url.password,
        "host": parsed_url.hostname,
    }
    newsletter_sender = SendNewsletter(db_config)
    # Generate your HTML newsletter content (using your existing logic)
    newsletter_sender.send_newsletter()

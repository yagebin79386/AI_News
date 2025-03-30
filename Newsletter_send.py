import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import psycopg2
import psycopg2.extras
from urllib.parse import urlparse, quote
import os
from dotenv import load_dotenv

# Define the base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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
        conn = self.conn      
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
        
        # Only replace the email placeholder
        replaced_html = html_content.replace("{EMAIL}", quote(recipient))

        sender = 'newsletter@homesmartify.lu'
        password = os.environ.get("EMAIL_PASSWORD")

        # Create message container
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = recipient

        # Plain-text fallback
        text_part = MIMEText("Plain text fallback here", 'plain')
        msg.attach(text_part)
        
        # HTML part
        html_part = MIMEText(replaced_html, 'html')
        msg.attach(html_part)

        # Connect to SMTP server and send email
        server = smtplib.SMTP('smtp.openxchange.eu', 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()

    def send_newsletter(self):
        subscribers = self.get_subscribers()
        subject = "DeepTech Digest: Your AI News Update"
        for email in subscribers:  
            self.send_email(email, subject)
            print(f"Newsletter to {email} has been sent.")

if __name__ == "__main__":    
    load_dotenv()
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
    newsletter_sender.send_newsletter()

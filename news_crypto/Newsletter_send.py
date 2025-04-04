import smtplib
from email.mime.text import MIMEText
from urllib.parse import quote, urlparse
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

def is_valid_email(email):
    """Validate email address format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

class SendNewsletter:
    def __init__(self, db_config=None):
        # If db_config is not provided, use DATABASE_URL from environment
        if db_config is None:
            # Get DATABASE_URL from environment
            db_url = os.environ.get("DATABASE_URL")
            if not db_url:
                raise ValueError("DATABASE_URL environment variable not set")
                
            # Parse the URL to get the components
            parsed_url = urlparse(db_url)
            dbname = parsed_url.path[1:]  # Remove leading '/'
            user = parsed_url.username
            password = parsed_url.password
            host = parsed_url.hostname
            
            db_config = {
                "dbname": dbname,
                "user": user,
                "password": password,
                "host": host
            }
        
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
        cursor.execute("SELECT email FROM crypto_subscriber")
        rows = cursor.fetchall()
        return [row.get('email') for row in rows]

    def send_email(self, recipient, subject):
        # Validate email address
        if not is_valid_email(recipient):
            print(f"Invalid email address: {recipient}")
            return False

        conn = self.conn
        cursor = conn.cursor()
        cursor.execute("SELECT html FROM crypto_newsletter order by creation desc limit 1")
        html_row = cursor.fetchone()
        html_content = html_row['html']
        replaced_html = html_content.replace("{EMAIL}", quote(recipient))

        # Get email credentials from environment variables
        sender = os.environ.get("EMAIL_SENDER", "newsletter@homesmartify.lu")
        password = os.environ.get("SMTP_PASSWORD")
        smtp_server = os.environ.get("SMTP_SERVER", "smtp.openxchange.eu")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        
        if not password:
            raise ValueError("SMTP_PASSWORD environment variable not set")

        try:
            # Create message
            msg = MIMEText(replaced_html, 'html')
            msg['Subject'] = subject
            msg['From'] = sender
            msg['To'] = recipient

            # Connect to SMTP server and send email
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
            server.quit()
            return True
        except Exception as e:
            print(f"Error sending email to {recipient}: {str(e)}")
            return False

    def send_newsletter(self):
        subscribers = self.get_subscribers()
        subject = "Crypto News Digest"
        successful_sends = 0
        failed_sends = 0
        
        for email in subscribers:  
            if self.send_email(email, subject):
                successful_sends += 1
                print(f"Newsletter to {email} has been sent.")
            else:
                failed_sends += 1
                print(f"Failed to send newsletter to {email}")
        
        print(f"\nNewsletter sending completed:")
        print(f"Successfully sent: {successful_sends}")
        print(f"Failed to send: {failed_sends}")

if __name__ == "__main__":
    # Use environment variables for configuration
    newsletter_sender = SendNewsletter()
    newsletter_sender.send_newsletter()

import psycopg2
from flask import Flask, render_template, request, jsonify, send_file, Blueprint
from datetime import datetime
from Welcome_send import send_welcome_email_to_user 
import os
from dotenv import load_dotenv
from urllib.parse import urlparse
import logging
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Only set APPLICATION_ROOT when in production (when running under Gunicorn)
# This is detected by checking if the WSGI entry point isn't the main file
if os.environ.get('RUNNING_IN_PRODUCTION') == 'true':
    app.config['APPLICATION_ROOT'] = '/newsletter'
    logger.info("Running in production mode with APPLICATION_ROOT set to /newsletter")
else:
    logger.info("Running in development mode without APPLICATION_ROOT")

# Configure Flask to trust the proxy headers
app.config['PREFERRED_URL_SCHEME'] = 'https'

# This fixes the "Contradictory scheme headers" issue
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Get database configuration from environment
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

def get_pg_connection():
    return psycopg2.connect(
        dbname=db_config["dbname"],
        user=db_config["user"],
        password=db_config["password"],
        host=db_config["host"],
        connect_timeout=30
    )

# Health check route for deployment monitoring
@app.route("/health")
def health_check():
    """Simple health check endpoint for monitoring systems"""
    logger.debug("Health check accessed")
    try:
        # Verify database connection
        conn = get_pg_connection()
        conn.close()
        return jsonify({"status": "healthy", "service": "newsletter"}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

# Root route will display instructions
@app.route("/")
def index():
    """Display instructions for using the newsletter viewer"""
    logger.debug("Newsletter index page accessed")
    return """
    <html>
    <head><title>Newsletter Viewer</title></head>
    <body>
        <h1>Newsletter Viewer</h1>
        <p>To view a newsletter, use the URL format: /&lt;newsletter_id&gt;</p>
        <p>Example: <a href="/newsletter/1">/newsletter/1</a> to view newsletter #1</p>
    </body>
    </html>
    """

# Route for viewing a specific newsletter
@app.route("/<int:newsletter_id>", methods=["GET"])
def display_newsletter(newsletter_id):
    """Display a specific newsletter edition by ID"""
    logger.debug(f"Newsletter {newsletter_id} requested")
    
    if newsletter_id is None:
        logger.warning("No newsletter ID specified")
        return "Please specify a newsletter ID", 400
        
    conn = get_pg_connection()
    cursor = conn.cursor()
    
    try:
        # Fetch the newsletter HTML from the database
        cursor.execute("SELECT html FROM newsletter WHERE newsletter_id = %s", (newsletter_id,))
        result = cursor.fetchone()
        
        if not result:
            logger.warning(f"Newsletter {newsletter_id} not found")
            return f"Newsletter {newsletter_id} not found", 404
            
        newsletter_html = result[0]
        logger.debug(f"Successfully retrieved newsletter {newsletter_id}")
        
        # Return the HTML directly
        return newsletter_html
        
    except Exception as e:
        logger.error(f"Error fetching newsletter {newsletter_id}: {e}")
        return f"Error loading newsletter {newsletter_id}: {str(e)}", 500
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=3001, debug=True)

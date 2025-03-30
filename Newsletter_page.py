import sqlite3
from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime
from Welcome_send import send_welcome_email_to_user 
import psycopg2
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Configure application for path-based routing
# This makes the app work when mounted at /newsletter path
app.config['APPLICATION_ROOT'] = '/newsletter'

# Load environment variables
load_dotenv()

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



@app.route("/<int:newsletter_id>")
def display_newsletter(newsletter_id):
    """Display a specific newsletter edition by ID"""
    conn = get_pg_connection()
    cursor = conn.cursor()
    
    try:
        # Fetch the newsletter HTML from the database
        cursor.execute("SELECT html FROM newsletter WHERE newsletter_id = %s", (newsletter_id,))
        result = cursor.fetchone()
        
        if not result:
            return "Newsletter not found", 404
            
        newsletter_html = result[0]
        
        # Return the HTML directly
        return newsletter_html
        
    except Exception as e:
        print(f"Error fetching newsletter {newsletter_id}: {e}")
        return "Error loading newsletter", 500
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    app.run(debug=True)

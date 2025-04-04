from flask import Flask, render_template, request, jsonify
from datetime import datetime
from Welcome_send import send_welcome_email_to_user
from Management_send import send_subs_management_email_to_user
import psycopg2
import psycopg2.extras
import os
from urllib.parse import urlparse
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()




class DatabaseManager:
    def __init__(self, db_config):
        self.db_config = db_config
        self._get_connection()

    def _get_connection(self):
        try:
            self.conn = psycopg2.connect(
                dbname=self.db_config["dbname"],
                user=self.db_config["user"],
                password=self.db_config["password"],
                host=self.db_config["host"],
                cursor_factory=psycopg2.extras.RealDictCursor
            )
        except Exception as e:
            print(f"Database connection error: {e}")
            raise
        self.current_time = datetime.now().isoformat()

    def _ensure_connection(self):
        try:
            # Test if connection is still alive
            self.conn.cursor().execute('SELECT 1')
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            # If connection is dead, create a new one
            self._get_connection()

    def get_subscriber(self, email):
        try:
            self._ensure_connection()
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM subscriber WHERE email = %s", (email,))
            row = cursor.fetchone()
            cursor.close()
            print(f"[DEBUG] get_subscriber({email}) returned: {row}")
            if row:
                return self.parse_subscriber(row)
            return None
        except Exception as e:
            print(f"Error in get_subscriber: {e}")
            raise

    def parse_subscriber(self, row):
        """
        row order in DB: 
        subscriber_id, email, creation_time, update_time,
        preferences, age_range, gender,
        residence_country, ai_involvement, reason_for_subscriping
        """
        return {
            "subscriber_id": row['subscriber_id'],
            "email": row['email'],
            "creation_time": row['creation_time'],
            "update_time": row['update_time'],
            "preferences": row['preferences'],
            "age_range": row['age_range'],
            "gender": row['gender'],
            "residence_country": row['residence_country'],
            "ai_involement": row['ai_involement'],
            "reason_for_subscribing": row['reason_for_subscribing']
        }

    def add_subscriber(self, email):
        
        conn = self.conn
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO subscriber (email, creation_time, update_time) VALUES (%s, %s, %s)",
            (email, self.current_time, self.current_time)
        )
        conn.commit()
        cursor.close()

    def delete_subscriber(self, email):
        conn = self.conn
        cursor = conn.cursor()
        cursor.execute("DELETE FROM subscriber WHERE email = %s", (email,))
        conn.commit()
        cursor.close()

    def update_preferences(self, email, preferences):
        conn = self.conn
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE subscriber SET preferences = %s, update_time = %s WHERE email = %s",
            (preferences, self.current_time, email)
        )
        conn.commit()
        cursor.close()

    def update_general_info(self, email, age_range, gender, residence_country, ai_involvement, reason_for_subscribing):
        print(f"[DEBUG] update_general_info() for {email}: age_range={age_range}, gender={gender}, "
              f"residence_country={residence_country}, ai_involvement={ai_involvement}, reason_for_subscribing={reason_for_subscribing}")
        conn = self.conn
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE subscriber
            SET age_range = %s,
                gender = %s,
                residence_country = %s,
                ai_involement = %s,
                reason_for_subscribing = %s,
                update_time = %s
            WHERE email = %s
            """,
            (age_range, gender, residence_country, ai_involvement, reason_for_subscribing, self.current_time, email)
        )
        conn.commit()
        cursor.close()




app = Flask(__name__)
app.secret_key = "supersecretkey"

# Set the application root to "/ai/management" for proper URL handling
app.config['APPLICATION_ROOT'] = '/ai/management'

# Configure Flask to trust the proxy headers
app.config['PREFERRED_URL_SCHEME'] = 'https'

# This fixes the "Contradictory scheme headers" issue
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1, x_prefix=1)

print(f"[INFO] Application starting with APPLICATION_ROOT={app.config.get('APPLICATION_ROOT')}")

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

db_manager = DatabaseManager(db_config)

# Health check route for deployment monitoring
@app.route("/health")
def health_check():
    """Simple health check endpoint for monitoring systems"""
    try:
        # Verify database connection is working
        db_manager._ensure_connection()
        return jsonify({"status": "healthy", "service": "subscriber_management"}), 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route("/debug")
def debug_info():
    """Debug information about the request"""
    return jsonify({
        "script_root": request.script_root,
        "base_url": request.base_url,
        "url": request.url,
        "path": request.path,
        "headers": dict(request.headers),
        "app_root": app.config.get('APPLICATION_ROOT'),
        "preferred_scheme": app.config.get('PREFERRED_URL_SCHEME')
    })

@app.route("/", methods=["GET", "POST"])
def subscribe_management():
    try:
        # Email from query string (from emailed link)
        query_email = request.args.get("email", "").strip().lower()
        
        # Variables for template logic
        is_verified = False
        subscriber_info = None
        email_status = ""
        pref_status = ""
        general_status = ""
        email = ""  # Passed to the template

        if request.method == "POST":
            form_type = request.form.get("form_type", "")
            # The 'email' from the form overrides the query_email if present
            form_email = request.form.get("email", "").strip().lower()
            email = form_email if form_email else query_email

            if form_type == "email_form":
                # Unverified user is subscribing
                existing = db_manager.get_subscriber(email)
                if existing:
                    email_status = "This Email is already registered with Newsletter, you can VERIFY and MANAGE the subscription through the link we sent to your email Box."
                    subscriber_info = None
                    is_verified = False

                    # Attempt to send subs_management email
                    try:
                        send_subs_management_email_to_user(email)
                    except Exception as e:
                        print(f"[ERROR] Failed to send subs_management email: {e}")
                        email_status = "New subscriber registered but failed to send subs_management email."

                else:
                    # Insert new subscriber           
                    db_manager.add_subscriber(email)
                    email_status = "New subscriber registered! A welcome email has been sent to VERIFY and MANAGE your subscription."
                    subscriber_info = None
                    is_verified = False

                    # Attempt to send welcome email
                    try:
                        send_welcome_email_to_user(email)
                    except Exception as e:
                        print(f"[ERROR] Failed to send welcome email: {e}")
                        email_status = "New subscriber registered but failed to send welcome email."

            elif form_type == "unsubscribe":
                # Verified user unsubscribing
                email_to_unsubscribe = request.form.get("email", "").strip().lower()
                print(f"[DEBUG] Unsubscribe attempt for: {email_to_unsubscribe}")
                db_manager.delete_subscriber(email_to_unsubscribe)
                email_status = "You unsubscribed successfully."
                subscriber_info = None
                is_verified = False
                email = ""
                print("[DEBUG] Unsubscribe completed.")

            elif form_type == "pref_form":
                # Preferences update
                selected_prefs = request.form.get("preferences", "")
                db_manager.update_preferences(email, selected_prefs)
                pref_status = "Preferences updated!"
                subscriber_info = db_manager.get_subscriber(email)
                is_verified = True


            elif form_type == "general_form":
                # 1. Age Range
                age_range = request.form.get("age_range")
                # 2. Gender
                gender = request.form.get("gender")
                # 3. Residence Country
                residence_country = request.form.get("residence_country")
                # 4. AI Involvement
                ai_involvement = request.form.get("ai_involvement")
                # 5. Reason forsubscribing
                reason_for_subscribing = request.form.get("reason_for_subscribing")

                db_manager.update_general_info(email, age_range, gender, residence_country, ai_involvement, reason_for_subscribing)
        
                general_status = "General information updated!"
                subscriber_info = db_manager.get_subscriber(email)
                is_verified = True


            # If POST came via AJAX, return JSON instead of rendering template
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({
                    "email_status": email_status,
                    "pref_status": pref_status,
                    "general_status": general_status,
                    "subscriber_info": subscriber_info,
                    "is_verified": is_verified,
                    "email": email
                })

        # Handle GET: If there's an email in query, look up subscriber
        if query_email:
            try:
                info = db_manager.get_subscriber(query_email)
                if info:
                    subscriber_info = info
                    is_verified = True
                    email = query_email
                else:
                    email = query_email
            except Exception as e:
                print(f"Error looking up subscriber: {e}")
                return render_template(
                    "subscribe_management.html",
                    email=query_email,
                    is_verified=False,
                    subscriber_info=None,
                    email_status="Error verifying email. Please try again later.",
                    pref_status="",
                    general_status="",
                    preference_options=[
                        "1. Breakthrough Research & Frontier AI",
                        "2. Enterprise Adoption & Industrial Automation",
                        "3. AI in Daily Life (health, education, entertainment, etc.)",
                        "4. AI & Jobs: Workplace Transformation & Skills",
                        "5. Ethics, Regulation & Governance",
                        "6. Market Trends, Funding & Investment",
                        "7. Tools, Platforms & Developer Ecosystem"
                    ],
                    all_countries = [
                    "Afghanistan",
                    "Åland Islands",
                    "Albania",
                    "Algeria",
                    "American Samoa",
                    "Andorra",
                    "Angola",
                    "Anguilla",
                    "Antarctica",
                    "Antigua and Barbuda",
                    "Argentina",
                    "Armenia",
                    "Aruba",
                    "Australia",
                    "Austria",
                    "Azerbaijan",
                    "Bahamas",
                    "Bahrain",
                    "Bangladesh",
                    "Barbados",
                    "Belarus",
                    "Belgium",
                    "Belize",
                    "Benin",
                    "Bermuda",
                    "Bhutan",
                    "Bolivia",
                    "Bonaire, Sint Eustatius and Saba",
                    "Bosnia and Herzegovina",
                    "Botswana",
                    "Bouvet Island",
                    "Brazil",
                    "British Indian Ocean Territory",
                    "Brunei Darussalam",
                    "Bulgaria",
                    "Burkina Faso",
                    "Burundi",
                    "Cabo Verde",
                    "Cambodia",
                    "Cameroon",
                    "Canada",
                    "Cayman Islands",
                    "Central African Republic",
                    "Chad",
                    "Chile",
                    "China",
                    "Christmas Island",
                    "Cocos (Keeling) Islands",
                    "Colombia",
                    "Comoros",
                    "Congo",
                    "Congo, Democratic Republic of the",
                    "Cook Islands",
                    "Costa Rica",
                    "Croatia",
                    "Cuba",
                    "Curaçao",
                    "Cyprus",
                    "Czech Republic",
                    "Côte d'Ivoire",
                    "Denmark",
                    "Djibouti",
                    "Dominica",
                    "Dominican Republic",
                    "Ecuador",
                    "Egypt",
                    "El Salvador",
                    "Equatorial Guinea",
                    "Eritrea",
                    "Estonia",
                    "Eswatini",
                    "Ethiopia",
                    "Falkland Islands (Malvinas)",
                    "Faroe Islands",
                    "Fiji",
                    "Finland",
                    "France",
                    "French Guiana",
                    "French Polynesia",
                    "French Southern Territories",
                    "Gabon",
                    "Gambia",
                    "Georgia",
                    "Germany",
                    "Ghana",
                    "Gibraltar",
                    "Greece",
                    "Greenland",
                    "Grenada",
                    "Guadeloupe",
                    "Guam",
                    "Guatemala",
                    "Guernsey",
                    "Guinea",
                    "Guinea-Bissau",
                    "Guyana",
                    "Haiti",
                    "Heard Island and McDonald Islands",
                    "Holy See",
                    "Honduras",
                    "Hong Kong",
                    "Hungary",
                    "Iceland",
                    "India",
                    "Indonesia",
                    "Iran, Islamic Republic of",
                    "Iraq",
                    "Ireland",
                    "Isle of Man",
                    "Israel",
                    "Italy",
                    "Jamaica",
                    "Japan",
                    "Jersey",
                    "Jordan",
                    "Kazakhstan",
                    "Kenya",
                    "Kiribati",
                    "Korea, Democratic People's Republic of",
                    "Korea, Republic of",
                    "Kuwait",
                    "Kyrgyzstan",
                    "Lao People's Democratic Republic",
                    "Latvia",
                    "Lebanon",
                    "Lesotho",
                    "Liberia",
                    "Libya",
                    "Liechtenstein",
                    "Lithuania",
                    "Luxembourg",
                    "Macao",
                    "Madagascar",
                    "Malawi",
                    "Malaysia",
                    "Maldives",
                    "Mali",
                    "Malta",
                    "Marshall Islands",
                    "Martinique",
                    "Mauritania",
                    "Mauritius",
                    "Mayotte",
                    "Mexico",
                    "Micronesia, Federated States of",
                    "Moldova, Republic of",
                    "Monaco",
                    "Mongolia",
                    "Montenegro",
                    "Montserrat",
                    "Morocco",
                    "Mozambique",
                    "Myanmar",
                    "Namibia",
                    "Nauru",
                    "Nepal",
                    "Netherlands",
                    "New Caledonia",
                    "New Zealand",
                    "Nicaragua",
                    "Niger",
                    "Nigeria",
                    "Niue",
                    "Norfolk Island",
                    "North Macedonia",
                    "Northern Mariana Islands",
                    "Norway",
                    "Oman",
                    "Pakistan",
                    "Palau",
                    "Palestine, State of",
                    "Panama",
                    "Papua New Guinea",
                    "Paraguay",
                    "Peru",
                    "Philippines",
                    "Pitcairn",
                    "Poland",
                    "Portugal",
                    "Puerto Rico",
                    "Qatar",
                    "Réunion",
                    "Romania",
                    "Russian Federation",
                    "Rwanda",
                    "Saint Barthélemy",
                    "Saint Helena, Ascension and Tristan da Cunha",
                    "Saint Kitts and Nevis",
                    "Saint Lucia",
                    "Saint Martin (French part)",
                    "Saint Pierre and Miquelon",
                    "Saint Vincent and the Grenadines",
                    "Samoa",
                    "San Marino",
                    "Sao Tome and Principe",
                    "Saudi Arabia",
                    "Senegal",
                    "Serbia",
                    "Seychelles",
                    "Sierra Leone",
                    "Singapore",
                    "Sint Maarten (Dutch part)",
                    "Slovakia",
                    "Slovenia",
                    "Solomon Islands",
                    "Somalia",
                    "South Africa",
                    "South Georgia and the South Sandwich Islands",
                    "South Sudan",
                    "Spain",
                    "Sri Lanka",
                    "Sudan",
                    "Suriname",
                    "Svalbard and Jan Mayen",
                    "Sweden",
                    "Switzerland",
                    "Syrian Arab Republic",
                    "Taiwan",
                    "Tajikistan",
                    "Tanzania, United Republic of",
                    "Thailand",
                    "Timor-Leste",
                    "Togo",
                    "Tokelau",
                    "Tonga",
                    "Trinidad and Tobago",
                    "Tunisia",
                    "Turkey",
                    "Turkmenistan",
                    "Turks and Caicos Islands",
                    "Tuvalu",
                    "Uganda",
                    "Ukraine",
                    "United Arab Emirates",
                    "United Kingdom",
                    "United States of America",
                    "Uruguay",
                    "Uzbekistan",
                    "Vanuatu",
                    "Venezuela (Bolivarian Republic of)",
                    "Viet Nam",
                    "Virgin Islands, British",
                    "Virgin Islands, U.S.",
                    "Wallis and Futuna",
                    "Western Sahara",
                    "Yemen",
                    "Zambia",
                    "Zimbabwe"
                ]
            )

        # Render template with final context
        return render_template(
            "subscribe_management.html",
            email=email,
            is_verified=is_verified,
            subscriber_info=subscriber_info,
            preference_options=[
                "1. Breakthrough Research & Frontier AI",
                "2. Enterprise Adoption & Industrial Automation",
                "3. AI in Daily Life (health, education, entertainment, etc.)",
                "4. AI & Jobs: Workplace Transformation & Skills",
                "5. Ethics, Regulation & Governance",
                "6. Market Trends, Funding & Investment",
                "7. Tools, Platforms & Developer Ecosystem"
            ],
            email_status=email_status,
            pref_status=pref_status,
            general_status=general_status,
            all_countries = [
            "Afghanistan",
            "Åland Islands",
            "Albania",
            "Algeria",
            "American Samoa",
            "Andorra",
            "Angola",
            "Anguilla",
            "Antarctica",
            "Antigua and Barbuda",
            "Argentina",
            "Armenia",
            "Aruba",
            "Australia",
            "Austria",
            "Azerbaijan",
            "Bahamas",
            "Bahrain",
            "Bangladesh",
            "Barbados",
            "Belarus",
            "Belgium",
            "Belize",
            "Benin",
            "Bermuda",
            "Bhutan",
            "Bolivia",
            "Bonaire, Sint Eustatius and Saba",
            "Bosnia and Herzegovina",
            "Botswana",
            "Bouvet Island",
            "Brazil",
            "British Indian Ocean Territory",
            "Brunei Darussalam",
            "Bulgaria",
            "Burkina Faso",
            "Burundi",
            "Cabo Verde",
            "Cambodia",
            "Cameroon",
            "Canada",
            "Cayman Islands",
            "Central African Republic",
            "Chad",
            "Chile",
            "China",
            "Christmas Island",
            "Cocos (Keeling) Islands",
            "Colombia",
            "Comoros",
            "Congo",
            "Congo, Democratic Republic of the",
            "Cook Islands",
            "Costa Rica",
            "Croatia",
            "Cuba",
            "Curaçao",
            "Cyprus",
            "Czech Republic",
            "Côte d'Ivoire",
            "Denmark",
            "Djibouti",
            "Dominica",
            "Dominican Republic",
            "Ecuador",
            "Egypt",
            "El Salvador",
            "Equatorial Guinea",
            "Eritrea",
            "Estonia",
            "Eswatini",
            "Ethiopia",
            "Falkland Islands (Malvinas)",
            "Faroe Islands",
            "Fiji",
            "Finland",
            "France",
            "French Guiana",
            "French Polynesia",
            "French Southern Territories",
            "Gabon",
            "Gambia",
            "Georgia",
            "Germany",
            "Ghana",
            "Gibraltar",
            "Greece",
            "Greenland",
            "Grenada",
            "Guadeloupe",
            "Guam",
            "Guatemala",
            "Guernsey",
            "Guinea",
            "Guinea-Bissau",
            "Guyana",
            "Haiti",
            "Heard Island and McDonald Islands",
            "Holy See",
            "Honduras",
            "Hong Kong",
            "Hungary",
            "Iceland",
            "India",
            "Indonesia",
            "Iran, Islamic Republic of",
            "Iraq",
            "Ireland",
            "Isle of Man",
            "Israel",
            "Italy",
            "Jamaica",
            "Japan",
            "Jersey",
            "Jordan",
            "Kazakhstan",
            "Kenya",
            "Kiribati",
            "Korea, Democratic People's Republic of",
            "Korea, Republic of",
            "Kuwait",
            "Kyrgyzstan",
            "Lao People's Democratic Republic",
            "Latvia",
            "Lebanon",
            "Lesotho",
            "Liberia",
            "Libya",
            "Liechtenstein",
            "Lithuania",
            "Luxembourg",
            "Macao",
            "Madagascar",
            "Malawi",
            "Malaysia",
            "Maldives",
            "Mali",
            "Malta",
            "Marshall Islands",
            "Martinique",
            "Mauritania",
            "Mauritius",
            "Mayotte",
            "Mexico",
            "Micronesia, Federated States of",
            "Moldova, Republic of",
            "Monaco",
            "Mongolia",
            "Montenegro",
            "Montserrat",
            "Morocco",
            "Mozambique",
            "Myanmar",
            "Namibia",
            "Nauru",
            "Nepal",
            "Netherlands",
            "New Caledonia",
            "New Zealand",
            "Nicaragua",
            "Niger",
            "Nigeria",
            "Niue",
            "Norfolk Island",
            "North Macedonia",
            "Northern Mariana Islands",
            "Norway",
            "Oman",
            "Pakistan",
            "Palau",
            "Palestine, State of",
            "Panama",
            "Papua New Guinea",
            "Paraguay",
            "Peru",
            "Philippines",
            "Pitcairn",
            "Poland",
            "Portugal",
            "Puerto Rico",
            "Qatar",
            "Réunion",
            "Romania",
            "Russian Federation",
            "Rwanda",
            "Saint Barthélemy",
            "Saint Helena, Ascension and Tristan da Cunha",
            "Saint Kitts and Nevis",
            "Saint Lucia",
            "Saint Martin (French part)",
            "Saint Pierre and Miquelon",
            "Saint Vincent and the Grenadines",
            "Samoa",
            "San Marino",
            "Sao Tome and Principe",
            "Saudi Arabia",
            "Senegal",
            "Serbia",
            "Seychelles",
            "Sierra Leone",
            "Singapore",
            "Sint Maarten (Dutch part)",
            "Slovakia",
            "Slovenia",
            "Solomon Islands",
            "Somalia",
            "South Africa",
            "South Georgia and the South Sandwich Islands",
            "South Sudan",
            "Spain",
            "Sri Lanka",
            "Sudan",
            "Suriname",
            "Svalbard and Jan Mayen",
            "Sweden",
            "Switzerland",
            "Syrian Arab Republic",
            "Taiwan",
            "Tajikistan",
            "Tanzania, United Republic of",
            "Thailand",
            "Timor-Leste",
            "Togo",
            "Tokelau",
            "Tonga",
            "Trinidad and Tobago",
            "Tunisia",
            "Turkey",
            "Turkmenistan",
            "Turks and Caicos Islands",
            "Tuvalu",
            "Uganda",
            "Ukraine",
            "United Arab Emirates",
            "United Kingdom",
            "United States of America",
            "Uruguay",
            "Uzbekistan",
            "Vanuatu",
            "Venezuela (Bolivarian Republic of)",
            "Viet Nam",
            "Virgin Islands, British",
            "Virgin Islands, U.S.",
            "Wallis and Futuna",
            "Western Sahara",
            "Yemen",
            "Zambia",
            "Zimbabwe"
        ]
        )
    except Exception as e:
        print(f"Unexpected error in subscribe_management: {e}")
        return render_template(
            "subscribe_management.html",
            email="",
            is_verified=False,
            subscriber_info=None,
            email_status="An unexpected error occurred. Please try again later.",
            pref_status="",
            general_status="",
            preference_options=[],
            all_countries=[]
        )

if __name__ == "__main__":
    try:
        # Use internal port 3000 to match the Nginx configuration
        app.run(host="127.0.0.1", port=3000, debug=True)
    finally:
        # Close the persistent database connection when the server stops
        db_manager.conn.close()

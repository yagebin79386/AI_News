import sqlite3
from flask import Flask, render_template, request, jsonify
from datetime import datetime
from Welcome_send import send_welcome_email_to_user 

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_PATH = "/app/data/news.db"

def get_subscriber(email):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subscriber WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    print(f"[DEBUG] get_subscriber({email}) returned: {row}")
    if row:
        return parse_subscriber(row)
    return None

def parse_subscriber(row):
    """
    row order in DB: 
      subscriber_id, email, creation_time, update_time,
      preferences, age_range, gender,
      residence_country, annual_income, crypto_involvement
    """
    return {
        "subscriber_id": row[0],
        "email": row[1],
        "creation_time": row[2],
        "update_time": row[3],
        "preferences": row[4],
        "age_range": row[5],
        "gender": row[6],
        "residence_country": row[7],
        "annual_income": row[8],
        "crypto_involvement": row[9]
    }


@app.route("/", methods=["GET", "POST"])
def subscribe_management():
    # Email from query string (from emailed link)
    query_email = request.args.get("email", "").strip().lower()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT image_base64 FROM images WHERE image_name = 'company_logo'")
    company_logo_b64 = cursor.fetchone()[0]  

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
        current_time = datetime.now().strftime("%b. %Y")  # e.g. "Mar. 2025"

        if form_type == "email_form":
            # Unverified user is subscribing
            existing = get_subscriber(email)
            if existing:
                email_status = "This Email is already registered with Newsletter, please check your email Box."
                subscriber_info = None
                is_verified = False
            else:
                # Insert new subscriber
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO subscriber (email, creation_time, update_time) VALUES (?, ?, ?)",
                    (email, current_time, current_time)
                )
                conn.commit()
                conn.close()
                email_status = "New subscriber registered. A welcome email has been sent to manage your subscription."
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

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM subscriber WHERE email = ?", (email_to_unsubscribe,))
            conn.commit()
            conn.close()

            email_status = "You unsubscribed successfully."
            subscriber_info = None
            is_verified = False
            email = ""
            print("[DEBUG] Unsubscribe completed.")

        elif form_type == "pref_form":
            # Preferences update
            selected_prefs = request.form.get("preferences", "")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE subscriber SET preferences = ?, update_time = ? WHERE email = ?",
                           (selected_prefs, current_time, email))
            conn.commit()
            conn.close()

            pref_status = "Preferences updated!"
            subscriber_info = get_subscriber(email)
            is_verified = True

        elif form_type == "general_form":
            # 1. Age Range
            age_range = request.form.get("age_range")
            # 2. Gender
            gender = request.form.get("gender")
            # 3. Residence Country
            residence_country = request.form.get("residence_country")
            # 4. Annual Household Income
            annual_income = request.form.get("annual_income")
            # 5. Crypto Involvement
            crypto_involvement = request.form.get("crypto_involvement")

            current_time = datetime.now().strftime("%b. %Y")  # e.g. "Mar. 2025"
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE subscriber
                SET age_range = ?,
                    gender = ?,
                    residence_country = ?,
                    annual_income = ?,
                    crypto_involvement = ?,
                    update_time = ?
                WHERE email = ?
                """,
                (age_range, gender, residence_country, annual_income, crypto_involvement, current_time, email)
            )
            conn.commit()
            conn.close()

            general_status = "General information updated!"
            subscriber_info = get_subscriber(email)
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
        info = get_subscriber(query_email)
        if info:
            subscriber_info = info
            is_verified = True
            email = query_email
        else:
            email = query_email

    # Render template with final context
    return render_template(
        "subscribe_management.html",
        email=email,
        is_verified=is_verified,
        subscriber_info=subscriber_info,
        company_logo_b64 = company_logo_b64,
        preference_options=[
            "Market Trends & Investment Analysis",
            "Regulatory & Policy Developments",
            "Blockchain Technology & Infrastructure",
            "Decentralized Ecosystem (DeFi, NFTs, dApps)",
            "Security & Cybersecurity",
            "Enterprise Adoption & Institutional Integration",
            "Community, Culture & Thought Leadership"
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

if __name__ == "__main__":
    app.run(debug=True)

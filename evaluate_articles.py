import openai
from datetime import datetime
import psycopg2
import psycopg2.extras
from urllib.parse import urlparse
from dotenv import load_dotenv
import os

# Set your OpenAI API key (preferably load from an environment variable for security)

def evaluate_articles():
    # Connect to the PostgreSQL database
    conn = psycopg2.connect(
        dbname= db_config["dbname"],
        user= db_config["user"],
        password= db_config["password"],
        host= db_config["host"],
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    cursor = conn.cursor()

    # Query articles that have Title, summary, Publication_Date but no InfluentialFactor set
    cursor.execute("""
        SELECT news_id, title, summary
        FROM news
        WHERE title IS NOT NULL
          AND summary IS NOT NULL
          AND publication_date IS NOT NULL
          AND influentialfactor IS NULL
    """)

    articles = cursor.fetchall()
    print(f"Fetched {len(articles)} articles for evaluation.")

    for article in articles:
        news_id = article['news_id']
        title = article['title']
        summary = article['summary']
        print(f"Evaluating article ID {news_id} with title: {title}")
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": (
                    f"Evaluate the potential influential factor or popularity of the article titled '{title}' with the summary: {summary}. "
                    "Consider the following criteria: "
                    "1. Public & Social Impact (PSI, 30%): Does this article highlight changes in how people live, work, learn, or interact due to AI? Look for shifts in behavior, mass adoption, or ethical/social debates. "
                    "2. Industry Transformation Potential (ITP, 25%): Does the article describe AI affecting a major industry (e.g., healthcare, finance, education, manufacturing)? Consider scale, disruption potential, or cross-sector relevance. "                   
                    "3. Technological Breakthrough Significance (TBS, 20%): Does it feature novel capabilities, architectures, or models (e.g., new LLMs, multimodal models)? Evaluate its innovation level and technical leap. "                    
                    "4. Governance & Regulation Influence (GRI, 10%): Does it involve AI-related policies, bans, global alignment, or government frameworks? Consider international attention, legal implications, and political interest. "                   
                    "5. Virality & Media Buzz (VMB, 10%): Is the topic trending, meme-worthy, emotionally provocative, or viral on social platforms? Think about shareability, outrage factor, or media attention. "                    
                    "6. Long-Term Societal Shift Indicator (LSSI, 5%): Could this news indicate a deep, lasting shift in human-AI relations or infrastructure? Assess ideological, educational, or systemic changes. "                   
                    "Return a **popularity score between 0 and 1**, rounded to **two decimal places**, with **no explanation or extra text**."
                )
            }],
            max_tokens=50
        )

        # Attempt to parse the evaluated factor from the response
        factor_str = response.choices[0].message.content.strip()
        try:
            influential_factor = float(factor_str)
        except ValueError:
            influential_factor = None  # or handle error as needed

        print(f"The evaluated score for the article '{title}' is: {influential_factor}")

        # Update the database if we got a valid numeric factor
        if influential_factor is not None:
            cursor.execute("""
                UPDATE news
                SET InfluentialFactor = %s
                WHERE news_id = %s
            """, (influential_factor, news_id))

    conn.commit()
    conn.close()

# Example usage
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
    evaluate_articles()

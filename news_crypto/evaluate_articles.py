import openai
from datetime import datetime
import psycopg2
import psycopg2.extras
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def evaluate_articles():
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
    
    # Connect to the PostgreSQL database
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    cursor = conn.cursor()

    # Query articles that have Title, summary, Publication_Date but no InfluentialFactor set
    cursor.execute("""
        SELECT news_id, title, summary
        FROM crypto_news
        WHERE title IS NOT NULL
          AND summary IS NOT NULL
          AND publication_date IS NOT NULL
          AND influentialfactor IS NULL
    """)

    articles = cursor.fetchall()
    print(f"Fetched {len(articles)} articles for evaluation.")

    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key not found in environment variables")

    for article in articles:
        news_id = article['news_id']
        title = article['title']
        summary = article['summary']
        print(f"Evaluating article ID {news_id} with title: {title}")
        
        try:
            # Create the client with API key
            client = openai.OpenAI(api_key=api_key)
            
            # Make the API call
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "user",
                    "content": (
                        f"Evaluate the potential influential factor or popularity of the article titled '{title}' with the summary: {summary}. "
                        "Consider the following criteria: "
                        "1. Market Impact Potential (MIP, 35%): Does the news likely affect crypto prices, trading volume, or investor behavior? Look for big financial stakes, sentiment shifts (FUD/FOMO), or adoption signals. "
                        "2. Scandal or Controversy Factor (SCF, 25%): Is there drama, loss, or ethical breaches? Check for large-scale losses, notable figures, or legal fallout. "
                        "3. Technological Innovation Significance (TIS, 15%): Does it introduce or impact blockchain tech? Assess novelty, scalability, or ecosystem relevance. "
                        "4. Regulatory or Policy Influence (RPI, 15%): Does it shape laws or government actions? Evaluate jurisdictional scope, precedent, or clarity. "
                        "5. Social Buzz and Virality (SBV, 5%): Will it spark online discussion? Look for emotional hooks, community ties, or shareability. "
                        "6. Long-Term Industry Impact (LTI, 5%): Does it alter the sector's future? Consider structural changes, narrative shifts, or stakeholder effects. "
                        "Evaluate the crypto/blockchain news article's influence/popularity using these criteria. Return a score between 0 and 1 with 2 digits, without extra text."
                    )
                }],
                max_tokens=50,
                temperature=0.1
            )

            # Extract the score from the response
            factor_str = response.choices[0].message.content.strip()
            
            try:
                influential_factor = float(factor_str)
                print(f"✅ Evaluated score for '{title}': {influential_factor}")
                
                # Update the database with the score
                cursor.execute("""
                    UPDATE crypto_news
                    SET InfluentialFactor = %s
                    WHERE news_id = %s
                """, (influential_factor, news_id))
                conn.commit()
                
            except ValueError:
                print(f"❌ Invalid score format: '{factor_str}' for article: {title}")
        
        except Exception as e:
            print(f"❌ Error with OpenAI API for article '{title}': {e}")

    conn.close()
    print("✅ Evaluation process completed.")

# Example usage
if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    evaluate_articles()

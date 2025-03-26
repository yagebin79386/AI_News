import openai
import json
from datetime import datetime, timedelta
import base64
import os
import psycopg2
import psycopg2.extras
from urllib.parse import urlparse
import os
from dotenv import load_dotenv


class NewsletterGenerator:
    """
    A class to:
      1) Fetch top articles from a PostgreSQL database.
      2) Generate an introduction & top news via LLM.
      3) Insert the generated newsletter into 'newsletter' table.
      4) Render the newsletter HTML from DB data (so no repeated LLM calls).
    """

    def __init__(self, db_config: dict, days_from_now: int):
        self.conn = psycopg2.connect(
            dbname=db_config["dbname"],
            user=db_config["user"],
            password=db_config["password"],
            host=db_config["host"],
            cursor_factory=psycopg2.extras.RealDictCursor,
            connect_timeout=30
        )
        self.days_from_now = days_from_now
        self.current_date = datetime.now()
        self.start_date = self.current_date - timedelta(days=self.days_from_now)
        self.contact = {
            "contact_phone": "+352 661777082",
            "contact_mail": "info@homesmartify.lu",
            "contact_web": "https://www.homesmartify.lu"
        }
        self.redirect_link = "https://www.homesmartify.lu"
        # Internal storage for the top articles and generated text
        self.top_articles = []
        self.introduction = ""
        self.very_top_news = ""
        self.very_top_news_id = None
        self.top_title = ""
        self.newsletter_title = ""

        # Initialize OpenAI
        print(f"[DEBUG] NewsletterGenerator initialized. Date range: {self.start_date} to {self.current_date}")


    def fetch_top_articles(self):
        """
        Fetch top 5 articles from 'news' table based on InfluentialFactor
        within the specified date range.
        """
        conn = self.conn
        cursor = conn.cursor()
        print("[DEBUG] Connected to database:", self.conn.dsn)

        query = """
            SELECT news_id, title, summary, article
            FROM news
            WHERE influentialfactor IS NOT NULL
              AND publication_date >= %s
            ORDER BY influentialfactor DESC
            LIMIT 5
        """
        cursor.execute(query, (self.start_date.strftime("%Y-%m-%d"),))
        self.top_articles = cursor.fetchall()

        print(f"[DEBUG] Fetched {len(self.top_articles)} top articles:")
        for article in self.top_articles:
            print("[DEBUG] Article ID:", article['news_id'], "Title:", article['title'])  
        cursor.close()


    def generate_intro_and_top_news(self):
        """
        Use the LLM to generate:
         - A newsletter introduction covering the top articles
         - A highlighted top news summary for the first article
        """
        if not self.top_articles:
            print("[WARNING] No articles fetched. Call fetch_top_articles() first.")
            return

        # Prepare the article summaries for LLM
        article_summaries = "\n".join(
            f"Title: {article.get('title', 'N/A')}\nSummary: {article.get('summary', 'N/A')}"
            for article in self.top_articles 
        )

        print("[DEBUG] Sending request for newsletter introduction to OpenAI...")
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        intro_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": (
                    "Based on the following top article summaries:\n"
                    f"{article_summaries}\n"
                    "Generate an engaging newsletter introduction that seamlessly ties these articles together, exciting and inviting the reader to explore more. "
                    "Follow these writing style guidelines:\n"
                    "- **Conversational and Inclusive:** Use a friendly, community-driven tone that speaks directly to the reader.\n"
                    "- **Informative with a Casual Edge:** Present facts clearly but with a relaxed, accessible tone—avoid overly formal language.\n"
                    "- **Inquisitive and Thought-Provoking:** Ask questions or raise points that encourage readers to think deeply about the topics.\n"
                    "- **Balanced Critique:** Acknowledge both the benefits and potential concerns related to the articles' subjects.\n"
                    "- **Dynamic and Playful:** Use light, engaging language with personality—don't be afraid of playful expressions.\n"
                    "Structure the introduction into multiple paragraphs to improve the readability and flow, with each paragraph separated by newline characters. "
                    "Also, generate an eye-catching, highly attractive title for this edition of the newsletter that captures the essence of the articles.\n"
                    "Please provide your response in JSON format with the keys \"introduction\" and \"newsletter_title\"."
                )
            }],
            max_tokens=750
        )


        # Parse JSON from the LLM response 
        try:
            parsed_content = json.loads(intro_response.choices[0].message.content.strip())
            self.introduction = parsed_content.get("introduction", "No introduction found.")
            self.newsletter_title = parsed_content.get("newsletter_title", "No title found.")
        except json.JSONDecodeError:
            # If the response isn't valid JSON, fallback to the entire string
            text_content = intro_response.choices[0].message.content.strip()
            self.introduction = text_content
            self.newsletter_title = "Untitled Newsletter"

        print("[DEBUG] Newsletter title:", self.newsletter_title)
        print("[DEBUG] Newsletter introduction:", self.introduction)

        # Use local variable top_article_text, not self.top_article_text
        self.very_top_news_id = self.top_articles[0].get('news_id')
        very_top_title = self.top_articles[0].get('title')
        very_top_article_text = self.top_articles[0].get('article')

        # Combine the top article's title and content
        top_article = ":".join([very_top_title, very_top_article_text])

        print("[DEBUG] Sending request for top news summary to OpenAI...")
        top_news_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": (
                    "Summarize the following article to highlight its special importance or contribution:\n"
                    f"{top_article}\n"
                    f"for this edition of the newsletter {self.introduction}. "
                    "Using the similar transitional phrases like this 'For the top news of this edition....'"
                )
            }],
            max_tokens=600
        )
        self.very_top_news = top_news_response.choices[0].message.content.strip()
        print("[DEBUG] Top news summary:", self.very_top_news)


    def insert_newsletter_db(self):
        """
        Insert the generated newsletter data into the 'newsletter' table.
        This includes the introduction, top_news, selected_news_ids, etc.
        """
        if not self.top_articles or not self.introduction or not self.very_top_news or not self.newsletter_title:
            print("[WARNING] Missing data. Make sure you've generated the newsletter content.")
            return

        conn = self.conn
        cursor = conn.cursor()

        selected_ids = ",".join(str(article.get('news_id')) for article in self.top_articles)
        creation_date_str = self.current_date.strftime("%Y-%m-%d %H:%M:%S")

        # Attempt to find the highest edition_number for this newsletter title
        cursor.execute("SELECT MAX(edition_number) FROM newsletter WHERE newsletter_title = %s", (self.newsletter_title,))
        result = cursor.fetchone()
        if result and result['max']:
            edition_number = result['max'] + 1
        else:
            edition_number = 1

        print("[DEBUG] Inserting newsletter into the database...")
        cursor.execute("""
            INSERT INTO newsletter (creation, selected_news_id, edition_number, introduction, top_news_id, top_news, newsletter_title)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            creation_date_str,
            selected_ids,
            edition_number,
            self.introduction,
            self.very_top_news_id,
            self.very_top_news,
            self.newsletter_title
        ))
        conn.commit()
        print("[DEBUG] Newsletter inserted into database.")


    @staticmethod
    def estimate_reading_time(text: str) -> int:
        """
        Estimate reading time in minutes (≥1) based on ~170 words/minute.
        """
        words = len(text.split())
        wpm = 170
        return max(1, round(words / wpm))


    def render_html_from_db(self, output_filename="newsletter.html"):
        """
        Retrieves the newest newsletter record from the database,
        builds an inline-styled, mobile-responsive HTML suitable for most email clients,
        and writes the final HTML to a file.
        """
        

        # 1) Connect & fetch the newest newsletter record
        conn = self.conn
        cursor = conn.cursor()
        cursor.execute("""
            SELECT newsletter_id, selected_news_id, newsletter_title, introduction, 
                top_news_id, top_news, edition_number, creation
            FROM newsletter
            ORDER BY creation DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        if not row:
            print(f"[WARNING] No newsletter data found.")
            return

        newsletter_id=row['newsletter_id']
        selected_news_id_str = row['selected_news_id']
        newsletter_title=row['newsletter_title'] 
        introduction=row['introduction']
        top_news_id=row['top_news_id']
        top_news_text=row['top_news']
        edition_number=row['edition_number']
        creation=row['creation']

        # 2) Convert CSV string to list of ints, remove top news ID
        
        selected_ids = [int(x) for x in selected_news_id_str.split(",")]
        print(f"[DEBUG] selected_ids before top remove are '{selected_ids}'")
        if top_news_id in selected_ids:
            selected_ids.remove(top_news_id)
        print(f"[DEBUG] selected_ids after remove are '{selected_ids}'")

        # 3) Fetch top news article
        cursor.execute("SELECT title, publication_date, article, link FROM news WHERE news_id=%s LIMIT 1", (top_news_id,))
        top_row = cursor.fetchone()
        if top_row:
            top_title = top_row['title']
            publication_date = top_row['publication_date']
            top_article = top_row['article']
            top_link = top_row['link']
            top_read_time = self.estimate_reading_time(top_title + top_article)
        else:
            print(f"[WARNING] No top news article found for generate read estimation.")
            top_read_time = 0

        # 4) Fetch remaining articles
        placeholders = ",".join("%s" for _ in selected_ids)
        cursor.execute(f"""
            SELECT news_id, title, publication_date, article, summary, link
            FROM news
            WHERE news_id IN ({placeholders})
        """, tuple(selected_ids))
        articles = cursor.fetchall()
        print(f"[DEBUG] Fetched {len(articles)} additional articles:", [article['title'] for article in articles])

        # 5) Format date
        if isinstance(self.current_date, datetime):
            date_only_str = self.current_date.strftime("%Y-%m-%d")
        else:
            date_only_str = str(self.current_date).split()[0]


        # 7) Build inline-styled blocks
        # HEAD Area using table layout with issue info (left) and share buttons (right), then the title below
        head_area_html = f"""
        <!-- HEAD Area Table -->
        <table width="100%" border="0" cellspacing="0" cellpadding="0" 
            style="background: rgba(0, 87, 231, 0); border-radius:12px;">
        <!-- Top row: Issue info (left) and share buttons (right) -->
        <tr class="issue-info-block">
            <td align="left" style="font-family: 'Roboto Condensed', sans-serif; font-size: 13px; color: #666666; padding:0 0 20px 0;">
            Issue No.{newsletter_id} Edition {edition_number}<br>
            Current Date: {date_only_str}
            </td>
            <td align="right" style="vertical-align:top;">
            <table border="0" cellspacing="0" cellpadding="0">
                <tr>
                <!-- Twitter Share Button -->
                <td align="center" style="padding:5px;">
                    <a href="https://twitter.com/intent/tweet?url=YOUR_URL&text=Check%20this%20out!" 
                    target="_blank" style="text-decoration:none; color:#666666;">
                    <img src="cid:twitter_icon" alt="Twitter" style="width:20px; height:20px;">
                    <span style="font-family:'Nunito', sans-serif; font-size:12px;">Twitter</span>
                    </a>
                </td>
                <!-- Copy Link Button -->
                <td align="center" style="padding:5px;">
                    <a href="YOUR_URL" target="_blank" style="text-decoration:none; color:#666666;">
                    <img src="cid:copylink_icon" alt="Copy Link" style="width:23px; height:23px;">
                    <span style="font-family:'Nunito', sans-serif; font-size:12px;">Copy Link</span>
                    </a>
                </td>
                <!-- WhatsApp Share Button -->
                <td align="center" style="padding:5px;">
                    <a href="https://api.whatsapp.com/send?text=YOUR_URL" target="_blank" style="text-decoration:none; color:#666666;">
                    <img src="cid:whatsapp_icon" alt="WhatsApp" style="width:20px; height:20px;">
                    <span style="font-family:'Nunito', sans-serif; font-size:12px;">WhatsApp</span>
                    </a>
                </td>
                </tr>
            </table>
            </td>
        </tr>
        <!-- Second row: Newsletter title -->
        <tr>
            <td class="newsletter" colspan="2" align="center" 
                style="font-family: 'Poppins', sans-serif; letter-spacing: 2px; font-size:38px; color:#0057e7; text-transform:uppercase; padding:20px 0;">
            DEEPTECH DIGEST
            </td>
        </tr>
        </table>
        """

        # Intro
        intro_html = f"""
        <div style="margin-bottom:20px;">
        <h2 class="newsletter_title" style="
            display:block;
            font-family:'Poppins', sans-serif;
            font-size:22px; 
            color:#0057e7; 
            margin:0 auto 20px auto; 
            text-align:center; 
            max-width:600px;
        ">
            {newsletter_title}
        </h2>
        <p class="newsletter_intro" style="
            font-size:16px;
            font-family:'Nunito', sans-serif;
            color:#333333; 
            margin:0 30px 40px 30px; 
            max-width:700px; 
            text-align:left;
        ">
            {introduction}
        </p>
        </div>
        """

        # Article blocks
        article_block_template = """
        <div style="margin:0 20px; padding:10px;">
        <h3 class="article-title" style="
            font-size:20px;
            font-family:'Poppins', sans-serif;
            color:#0057e7; 
            margin:10px 35px 10px 35px; 
            text-align:center;
        ">
            {title}
        </h3>
        <p class="publication-date" style="
            font-size:14px;
            font-family:'Nunito', sans-serif;
            color:#666666;
            text-align:center;
            margin-bottom:10px;
        ">
            {article_publication_date}
        </p>
        <p class="article-summary" style="
            font-family:'Nunito', sans-serif;
            font-size:14px; 
            color:#333333; 
            margin-bottom:20px; 
            text-align:left;
        ">
            {summary}
        </p>
        <div style="text-align:center;">
            <a href="{link}" target="_blank" style="text-decoration:none;">
            <button style="
                padding:6px 12px; 
                background:#0057e7; 
                color:#ffffff; 
                border:none; 
                border-radius:20px; 
                cursor:pointer;
                font-size:12px;
                font-family:'Poppins', sans-serif;
                transition: background-color 0.2s;
            ">
                READ MORE ({read_time} mins)
            </button>
            </a>
        </div>
        </div>
        """

        article_blocks = ""
        for article in articles: 
            title=article['title']
            article_publication_date=article['publication_date']
            link=article['link'] 
            summary=article['summary']
            read_time = self.estimate_reading_time(title + article['article'])
            article_blocks += article_block_template.format(
                title=title,
                article_publication_date=article_publication_date,
                summary=summary,
                link=link,
                read_time=read_time
            )
        # Top News header
        top_news_header_html = """
        <div class="top-news-header">
            TOP NEWS!
        </div>
        """

        # Top news
        top_news_html = f"""
        <div style="margin:0 20px 30px 20px; padding:10px;">
        <h3 class="top-news-title" style="
            font-family:'Poppins', sans-serif;
            font-size:20px; 
            color:#0057e7; 
            margin:0 35px 12px 35px; 
            text-align:center;
        ">
            {top_title}
        </h3>
        <p class="publication-date" style="
            font-size:14px;
            font-family:'Nunito', sans-serif;
            color:#666666;
            text-align:center;
            margin-bottom:10px;
        ">
            {publication_date}
        </p>
        <p class="top-news-text" style="
            font-family:'Nunito', sans-serif; 
            font-size:14px; 
            color:#333333; 
            margin-bottom:20px; 
            text-align:left;
        ">
            {top_news_text}
        </p>
        <div style="text-align:center;">
            <a href="{top_link}" target="_blank" style="text-decoration:none;">
            <button style="
                padding:6px 12px; 
                background:#0057e7; 
                color:#ffffff; 
                border:none; 
                border-radius:20px; 
                cursor:pointer;
                font-size:12px;
                font-family:'Poppins', sans-serif;
                transition: background-color 0.2s;
            ">
                READ MORE ({top_read_time} mins)
            </button>
            </a>
        </div>
        </div>
        """

        # Redirect block
        redirect_html = f"""
        <div style="text-align:center; margin-top:20px;">
        <p style="font-size:14px; font-family:'Poppins', sans-serif; color:#333333; margin-bottom:10px;">
            Feel free to visit our website for more news and smart technologies possibilities!
        </p>
        <a href="{self.redirect_link}" target="_blank" style="text-decoration:none;">
            <button style="
                padding:8px 16px; 
                background:#0057e7; 
                color:#ffffff; 
                border:none; 
                border-radius:20px; 
                cursor:pointer; 
                font-family:'Poppins', sans-serif; 
                text-transform:uppercase; 
                font-size:14px;
                transition: background-color 0.2s;
            ">
                Explore More
            </button>
        </a>
        </div>
        """

        # Company logo
        company_logo_html = f"""
        <div class="logo-container">
        <img src="cid:company_logo" alt="Company Logo" class="company-logo-img">
        </div>
        """

        # Contact icons
        contact_html = f"""
        <div class="contact-container">
        <div class="contact-item">
            <img src="cid:phone_icon" alt="Phone" class="contact-icon">
            <span class="contact-text">{self.contact.get('contact_phone','')}</span>
            <span style="font-size:14px;">|</span>
        </div>
        <div class="contact-item">
            <img src="cid:email_icon" alt="Email" class="contact-icon">
            <span class="contact-text">{self.contact.get('contact_mail','')}</span>
            <span style="font-size:14px;">|</span>
        </div>
        <div class="contact-item">
            <img src="cid:web_icon" alt="Website" class="contact-icon">
            <span class="contact-text">{self.contact.get('contact_web','')}</span>
        </div>
        </div>
        """

        subscribe_html = f"""
        <div class="subscribe-container">
        Update your email preferences or unsubscribe
        <a href="https://www.ainewsletter.homesmartify.lu/?email={{EMAIL}}" target="_blank" rel="noopener nofollow">here</a>.
        </div>
        """

        company_footer_html = """
        <div class="footer-container">
        &copy; 2025 HomeSmartify.lu<br>
        Transforming Technology: Where Smart Technology Meets Caring Comfort.<br>
        Luxembourg City, Luxembourg 1329
        </div>
        """

        # 8) Combine everything into final HTML, adding a meta viewport and responsive CSS
        final_html = f"""
        <html lang="en">
        <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Newsletter</title>
        <style type="text/css">
            /* Default Style */
            .top-news-header {{
                text-align: center;
                color: #0057e7;
                font-family: 'Titan One', sans-serif;
                font-size: 28px;
                letter-spacing: 2px;
                margin-bottom: 10px;
            }}
            .logo-container {{
                text-align: center;
                margin-bottom: 10px;
            }}
            .company-logo-img {{
                display: block;
                width: 140px;
                max-width: 140px;
                height: auto;
                margin: 0 auto;
            }}
            .contact-container {{
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 15px;
                margin: 20px 0;
            }}
            .contact-item {{
                display: flex;
                align-items: center;
                gap: 5px;
            }}
            .contact-icon {{
                width: 20px;
                height: 20px;
            }}
            .contact-text {{
                font-size: 14px;
                color: #666666;
            }}
            .subscribe-container {{
                text-align: center;
                font-size: 14px;
                font-style: italic;
                color: #666666;
                margin: 25px 0;
            }}
            .footer-container {{
                text-align: center;
                font-size: 12px;
                color: #666666;
                margin-top: 20px;
                line-height: 1.4;
            }}

            /* Mobile Styles */
            @media only screen and (max-width: 600px) {{
                .top-news-header {{
                    font-size: 36px !important;  
                }}
                .company-logo-img {{
                    width: 150px !important;
                    max-width: 150px !important;
                }}
                .contact-container {{
                    flex-direction: column;
                    gap: 10px;
                }}
                .contact-text {{
                    font-size: 20px !important;
                }}
                .contact-icon {{
                    width: 30px;
                    height: 30px;
                }}
                .subscribe-container {{
                    font-size: 20px !important;
                }}
                .footer-container {{
                    font-size: 18px !important;
                }}
                .head-container * {{
                    font-size: 26px;
                }}
                .main-container * {{    
                    font-size: 26px !important;
                }}
                .newsletter_title {{
                    font-size: 36px !important;
                    margin:0 30px 20px 30px !important;
                }}
                .newsletter_intro {{
                    font-size: 28px !important;
                }}
                .article-title {{
                    font-size: 32px !important;
                }}
                .article-summary {{ 
                    font-size: 26px !important;
                }}
                .top-news-title {{ 
                    font-size: 32px !important;
                }}
                .top-news-text {{
                    font-size: 26px !important;
                }}
                .newsletter {{ 
                    font-size: 45px !important;
                }}
                .issue-info-block * {{
                    font-size: 26px !important; 
                }}
                .issue-info-block img {{
                    width: 40px !important; 
                    height: auto !important;
                }}
            }}
        </style>
        </head>
        <body style="margin:0; padding:0; background:linear-gradient(135deg, #add8e6, #ffffe0); font-family:'Nunito', sans-serif;">

        <!-- Outer table for full width background -->
        <table width="100%" border="0" cellspacing="0" cellpadding="0" align="center" style="background: linear-gradient(135deg, #add8e6, #ffffe0);">
            <tr>
            <td align="center" valign="top">

                <!-- Nested table to constrain width & center the newsletter -->
                <table width="600" border="0" cellspacing="0" cellpadding="0" align="center" style="border-spacing:0; border-collapse:collapse;">
                <tr>
                    <td align="center" valign="top" style="padding:20px;">

                    <!-- HEAD Container -->
                    <table class="head-container" width="100%" border="0" cellspacing="0" cellpadding="0" align="center"
                            style="background: rgba(0, 87, 231, 0.1); border-radius:12px; margin-bottom:20px;">
                        <tr>
                        <td style="padding:20px;">
                            {head_area_html}
                        </td>
                        </tr>
                    </table>

                    <!-- MAIN Container -->
                    <table class="main-container" width="100%" border="0" cellspacing="0" cellpadding="0" align="center"
                            style="background: rgba(0, 87, 231, 0.1); border-radius:12px; margin-bottom:20px;">
                        <tr>
                        <td style="padding:20px;">
                            {intro_html}
                            <hr style="border:none; border-top:2px solid #0057e7; margin:20px 0;">
                            {article_blocks}
                            <hr style="border:none; border-top:2px solid #0057e7; margin:40px 0;">
                            {top_news_header_html}
                            {top_news_html}
                            {redirect_html}
                        </td>
                        </tr>
                    </table>

                    <!-- TAIL Container -->
                    <table class="tail-container" width="100%" border="0" cellspacing="0" cellpadding="0" align="center"
                            style="background: rgba(0, 87, 231, 0.1); border-radius:12px;">
                        <tr>
                        <td style="padding:20px;">
                            {company_logo_html}
                            {contact_html}
                            {subscribe_html}
                            {company_footer_html}
                        </td>
                        </tr>
                    </table>

                    </td>
                </tr>
                </table>

            </td>
            </tr>
        </table>

        </body>
        </html>
        """

        # 9) Write final HTML to file
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(final_html)

        print(f"[DEBUG] Successfully wrote simplified, mobile-responsive newsletter to '{output_filename}' for {creation}.")

        # 10) Save the generated HTML back into the DB
        conn = self.conn
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE newsletter SET html = %s WHERE newsletter_id = %s",
            (final_html, newsletter_id),
        )
        conn.commit()
        print("[DEBUG] Updated newsletter record with generated HTML.")


    
# Example usage:
if __name__ == "__main__":
    load_dotenv()
    # 1) Instantiate the generator
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
    generator = NewsletterGenerator(db_config, days_from_now=2)

    # 2) Fetch top articles & call LLM (optional if you only want to re-render an existing newsletter)
    generator.fetch_top_articles()
    generator.generate_intro_and_top_news()

    # 3) Insert newly generated newsletter into DB
    generator.insert_newsletter_db()

    # 4) Render the HTML from DB data for the current date (no new LLM calls)
    generator.render_html_from_db(output_filename="newsletter.html")
    generator.conn.close()

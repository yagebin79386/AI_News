import os
import openai
import json
from urllib.parse import urlparse, urljoin
import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
import psycopg2
import psycopg2.extras
from newspaper import Article, Config # Requires: pip install newspaper3k
from dateutil import parser
from urllib.parse import urlparse
import sys
from dotenv import load_dotenv

# Print startup information for debugging
print(f"Script started at: {datetime.now().isoformat()}")
print(f"Current working directory: {os.getcwd()}")
print(f"Python version: {sys.version}")

# Load environment variables from .env file if it exists
# This helps with local development and ensures variables are loaded
# even when running via cron/supercronic
try:
    print("Attempting to load environment variables from .env file")
    load_dotenv()
    print("Environment loaded from .env file")
except Exception as e:
    print(f"Note: Failed to load .env file - this is expected in production: {e}")

# Check critical environment variables and print status (without exposing secrets)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not OPENAI_API_KEY:
    print("⚠️ Warning: OPENAI_API_KEY environment variable is not set")
else:
    print("✅ OPENAI_API_KEY is set")

if not DATABASE_URL:
    print("⚠️ Warning: DATABASE_URL environment variable is not set")
else:
    print(f"✅ DATABASE_URL is set, connecting to: {urlparse(DATABASE_URL).hostname}")

class NewsScrapperGeneral:
    def __init__(self, base_urls, db_config=None):
        """
        Initialize the NewsScrapperGeneral with a list of base URLs.
        For each base URL, we maintain:
          - paginated_url: a list of discovered URLs (pages)
          - html: a dict mapping each paginated URL to its cleaned HTML
          - extracted_news: a dict mapping each paginated URL to the raw extracted text (markdown)
        """
        self.webpages = [
            {
                "base_url": url,
                "paginated_url": [],
                "html": {},           # {paginated_url: cleaned_html, ...}
                "extracted_news": {}  # {paginated_url: extracted_text, ...}
            }
            for url in base_urls
        ]
        
        # Use DATABASE_URL if db_config is not provided
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
            port = parsed_url.port or "5432"  # Default PostgreSQL port
            
            self.db_config = {
                "dbname": dbname,
                "user": user,
                "password": password,
                "host": host,
                "port": port
            }
        else:
            self.db_config = db_config
            
        # Connect to the database
        self.conn = psycopg2.connect(
            dbname=self.db_config["dbname"],
            user=self.db_config["user"],
            password=self.db_config["password"],
            host=self.db_config["host"],
            cursor_factory=psycopg2.extras.RealDictCursor  # to get dictionary-like rows
        )

    def find_all_pagination_urls(self):
        """
        Extracts pagination URLs from different webpage structures.
        Stops after finding 10 additional pages per base URL (total 11 pages).
        """
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_argument("--single-process")
        options.add_argument("--disable-dev-tools")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--homedir=/tmp")

        driver = uc.Chrome(options=options)
        max_pages = 5  # base URL + 10 additional pages

        for page in self.webpages:
            current_url = page["base_url"]
            page["paginated_url"].append(current_url)
            try:
                driver.get(current_url)
                wait = WebDriverWait(driver, 5)
                while True:
                    if len(page["paginated_url"]) >= max_pages:
                        print("🚫 Reached the maximum page limit for", page["base_url"])
                        break
                    time.sleep(2)
                    next_page_url = None
                    try:
                        next_button = driver.find_element(By.XPATH, '//a[contains(@class, "Pagination-Link") and contains(@href, "page=")]')
                        next_page_url = next_button.get_attribute("href")
                        print("✅ Found 'Next' button:", next_page_url)
                    except:
                        print("❌ No explicit 'Next' button found.")
                    if not next_page_url:
                        try:
                            next_button = driver.find_element(By.XPATH, '//a[@rel="next"]')
                            next_page_url = next_button.get_attribute("href")
                        except:
                            print("❌ No `rel=next` button found.")
                    if next_page_url and not next_page_url.startswith("http"):
                        next_page_url = urljoin(current_url, next_page_url)
                    if next_page_url and next_page_url not in page["paginated_url"]:
                        print("✅ Next page URL found:", next_page_url)
                        page["paginated_url"].append(next_page_url)
                        driver.get(next_page_url)
                    else:
                        print("🚫 No new next page found, stopping pagination.")
                        break
            except Exception as e:
                print(f"🔥 Error during pagination search: {e}")
        driver.quit()

    def get_and_clean_html(self):
        """
        Fetches raw HTML from each paginated URL using requests first,
        falls back to undetected_chromedriver if needed,
        cleans it, and stores the cleaned HTML in the 'html' dict keyed by the paginated URL.
        """
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        def clean_html(raw_html):
            soup = BeautifulSoup(raw_html, "html.parser")
            for tag in soup(["script", "style", "noscript", "iframe", "svg", "path", "object",
                           "embed", "picture", "video", "audio", "source", "input",
                           "ins", "del", "form", "button"]):
                tag.decompose()
            for tag in soup.find_all():
                if not tag.get_text(strip=True):
                    tag.decompose()
            for tag in soup.find_all(True):
                attrs_to_remove = ["class", "id", "role", "data-*", "aria-*", "onclick", "onload", "style"]
                for attr in list(tag.attrs):
                    if tag.name == "a" and attr == "href":
                        continue
                    if any(re.match(pattern.replace("*", ".*"), attr) for pattern in attrs_to_remove):
                        del tag[attr]
            cleaned_html = str(soup)
            cleaned_html = re.sub(r">\s+<", "><", cleaned_html)
            cleaned_html = re.sub(r"\n+", "", cleaned_html)
            cleaned_html = re.sub(r"\s{2,}", " ", cleaned_html)
            return cleaned_html

        for page in self.webpages:
            if page['base_url'] not in page["paginated_url"]:
                page["paginated_url"].append(page["base_url"])
            
            for single_url in page["paginated_url"]:
                try:
                    # First try with requests
                    response = session.get(single_url, timeout=30)
                    response.raise_for_status()
                    raw_html = response.text
                    page["html"][single_url] = clean_html(raw_html)
                    print(f"✅ Successfully fetched {single_url} using requests")
                    continue
                except Exception as e:
                    print(f"⚠️ Failed to fetch {single_url} with requests: {e}")
                    print("Falling back to Selenium...")

                # Fall back to Selenium if requests fails
                try:
                    options = uc.ChromeOptions()
                    options.add_argument("--headless=new")
                    options.add_argument("--disable-blink-features=AutomationControlled")
                    options.add_argument("--no-sandbox")
                    options.add_argument("--disable-dev-shm-usage")
                    options.add_argument("--disable-gpu")
                    options.add_argument("--window-size=1920,1080")
                    options.add_argument("--remote-debugging-port=9222")
                    options.add_argument("--disable-setuid-sandbox")
                    options.add_argument("--disable-extensions")
                    options.add_argument("--disable-infobars")
                    options.add_argument("--single-process")
                    options.add_argument("--disable-dev-tools")
                    options.add_argument("--ignore-certificate-errors")
                    options.add_argument("--homedir=/tmp")

                    try:
                        # Use undetected-chromedriver with version_main parameter to automatically match Chrome version
                        driver = uc.Chrome(options=options, use_subprocess=True)
                    except Exception as chrome_error:
                        print(f"⚠️ Error with default Chrome setup: {chrome_error}")
                        print("Trying with explicit version handling...")
                        try:
                            # Get the installed Chrome version using selenium-stealth
                            import subprocess
                            version_output = ""
                            try:
                                if os.name == 'nt':  # Windows
                                    process = subprocess.Popen(
                                        'reg query "HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon" /v version',
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
                                    )
                                    output, error = process.communicate()
                                    version_output = output.decode('utf-8')
                                    chrome_version = re.search(r'version\s+REG_SZ\s+([\d.]+)', version_output).group(1)
                                else:  # Linux/Mac
                                    process = subprocess.Popen(
                                        'google-chrome --version',
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
                                    )
                                    output, error = process.communicate()
                                    version_output = output.decode('utf-8')
                                    chrome_version = re.search(r'Chrome\s+([\d.]+)', version_output).group(1)
                                
                                main_version = int(chrome_version.split('.')[0])
                                print(f"Detected Chrome version: {chrome_version} (Main: {main_version})")
                                driver = uc.Chrome(options=options, version_main=main_version, use_subprocess=True)
                            except Exception as version_error:
                                print(f"⚠️ Error detecting Chrome version: {version_error}")
                                print(f"Version output: {version_output}")
                                # If we still can't detect, try with a hardcoded recent version
                                driver = uc.Chrome(options=options, version_main=114, use_subprocess=True)
                        except Exception as detailed_error:
                            print(f"❌ Failed to create Chrome driver with explicit version: {detailed_error}")
                            # Skip this URL and continue with the next one
                            continue
                            
                    try:
                        driver.get(single_url)
                        raw_html = driver.page_source
                        page["html"][single_url] = clean_html(raw_html)
                        print(f"✅ Successfully fetched {single_url} using Selenium")
                    finally:
                        driver.quit()
                except Exception as e:
                    print(f"❌ Failed to fetch {single_url} with both methods: {e}")
                    continue

    def extract_news_articles_with_chatgpt(self):
        """
        For each cleaned HTML (keyed by URL in the 'html' dict),
        uses the OpenAI API to extract news article information.
        The extracted markdown is accumulated per URL and stored in the 'extracted_news' dict.
        """
        # Check if OpenAI API key is available before trying to use it
        if not OPENAI_API_KEY:
            print("❌ Error: Cannot extract news articles. OPENAI_API_KEY not set in environment variables.")
            for page in self.webpages:
                for url_key in page["html"].keys():
                    page["extracted_news"][url_key] = ""
            return

        for page in self.webpages:
            for url_key, html_content in page["html"].items():
                if not isinstance(html_content, str):
                    print("Skipping non-string content for URL:", url_key)
                    continue
                raw_html = html_content[:100000]
                parsed_url = urlparse(page["base_url"])
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
                prompt = f"""
                You are an AI that extracts structured data from raw HTML of a crypto news portal.
                Extract the following details for each news article:
                - **Title**: the title of the article.
                - **Publication Date**: If no date is explicitly given, return null.
                - **Author**: the name(s) of the author(s).
                - **Link**: the article's full hyperlink. If the hyperlink is relative, prepend the base URL (e.g., "https://cointelegraph.com/") so that the result is an absolute URL starting with "http://" or "https://".
                Extract this from the following HTML:
                ```html
                {raw_html}
                Return the result as a JSON array of objects, e.g.:
                [{{"Title": "Example", "Publication Date": "2023-01-01", "Author": "John Doe", "Link": "https://cointelegraph.com/article1"}}, ...]
                ```
                """
                try:
                    client = openai.OpenAI(api_key=OPENAI_API_KEY)
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "system", "content": prompt}],
                        temperature=0.1,
                        max_tokens=2000
                    )
                    extracted_text = response.choices[0].message.content.strip()
                    print(f"✅ Extracted for {url_key}:\n{extracted_text[:500]}...\n")
                    page["extracted_news"][url_key] = extracted_text
                except Exception as e:
                    print(f"❌ Error with OpenAI API for {url_key}: {e}")
                    page["extracted_news"][url_key] = ""

    def flatten_news(self):
        def convert_markdown_to_articles(markdown_text):
            blocks = re.split(r"\n(?=\d+\.)", markdown_text.strip())
            articles = []
            for block in blocks:
                title_match = re.search(r"\d+\.\s*\*\*Title\*\*:\s*(.*)", block)
                pub_date_match = re.search(r"-\s*\*\*Publication Date\*\*:\s*(.*)", block)
                author_match = re.search(r"-\s*\*\*Author\*\*:\s*(.*)", block)
                link_match = re.search(r"-\s*\*\*Link\*\*:\s*(.*)", block)
                if title_match and link_match:
                    article = {}
                    article["Title"] = title_match.group(1).strip()
                    article["Publication Date"] = pub_date_match.group(1).strip() if pub_date_match else None
                    article["Author"] = author_match.group(1).strip() if author_match else None
                    article["Link"] = link_match.group(1).strip() if link_match else None
                    if article["Link"]:  # Only add if Link exists
                        articles.append(article)
            return articles

        for page in self.webpages:
            new_extracted = {}
            for url_key, news_data in page.get("extracted_news", {}).items():
                if not news_data:  # Skip empty or None
                    print(f"Skipping empty news data for {url_key}")
                    continue
                news_data = news_data.strip()
                print(f"Processing news data for {url_key}:\n{news_data}")  # Debug output
                if news_data.startswith("```json"):
                    news_data = news_data[len("```json"):].strip()
                    if news_data.endswith("```"):
                        news_data = news_data[:-3].strip()
                if not news_data.startswith("[") and not news_data.startswith("{"):
                    articles = convert_markdown_to_articles(news_data)
                else:
                    try:
                        articles = json.loads(news_data)
                        if not isinstance(articles, list):
                            print(f"Invalid JSON format for {url_key}: expected list, got {type(articles)}")
                            continue
                    except json.JSONDecodeError as e:
                        print(f"⚠️ Error decoding JSON from extracted_news for {url_key}: {e}")
                        print(f"Problematic content:\n{news_data}")
                        continue
                base_url = page.get("base_url", "")
                valid_articles = []
                for article in articles:
                    if not isinstance(article, dict):  # Skip if not a dict
                        print(f"Skipping invalid article for {url_key}: {article}")
                        continue
                    link = article.get("Link", "") or ""  # Default to empty string if None
                    link = link.strip()
                    if not link:
                        continue
                    if not link.startswith("http"):
                        article["Link"] = urljoin(base_url, link)
                    valid_articles.append(article)
                new_extracted[url_key] = valid_articles
                print(f"✅ Successfully flattened {len(valid_articles)} articles for {url_key}")
            page["extracted_news"] = new_extracted

    def save_to_db(self):
        conn = self.conn
        c = conn.cursor()
        created_time = datetime.now().isoformat()
        for page in self.webpages:
            base_url = page.get("base_url")
            for paginated_url, articles in page.get("extracted_news", {}).items():
                for article in articles:
                    title = article.get("Title")
                    author = article.get("Author")
                    pub_date = article.get("Publication Date")
                    link = article.get("Link")
                    if not (title and link and base_url and paginated_url):
                        continue
                    insert_sql = """
                    INSERT INTO crypto_news (Title, Author, Publication_Date, Link, base_url, paginated_url, created_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (Title) DO NOTHING;
                    """
                    c.execute(insert_sql, (title, author, pub_date, link, base_url, paginated_url, created_time))
        conn.commit()
        print("✅ Data saved to PostgreSQL database:", self.db_config['dbname'])


    def update_article_details(self):
        """
        For each record in the 'crypto_news' table where the article text, Author, or Publication_Date is NULL,
        scrape the main article text from the Link using Newspaper3k, and update the record.
        The scraped main text is saved under the 'article' column, and if Author or Publication_Date
        are missing, they are updated as well.
        If the article text cannot be retrieved successfully, the record will be dropped from the database.
        """
        config = Config()
        config.browser_user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0.0.0 Safari/537.36"
        )
        conn = self.conn
        c = conn.cursor()
        # Update the rows where the article text, Author, or Publication_Date is NULL
        c.execute("SELECT Title, Link, Author, Publication_Date FROM crypto_news WHERE article IS NULL OR Author IS NULL OR Publication_Date IS NULL;")
        rows = c.fetchall()
        
        for row in rows:
            title = row['title']
            link = row['link']
            db_author = row['author']
            db_pub_date = row['publication_date']
            try:
                art = Article(link, config=config)
                art.download()
                art.parse()
                main_text = art.text
                
                # Verify if the article text was successfully retrieved
                if not main_text or len(main_text.strip()) < 50:  # Minimum length check
                    print(f"❌ Article text retrieval failed for: {title}")
                    # Drop the record if text retrieval failed
                    c.execute("DELETE FROM crypto_news WHERE Title = %s", (title,))
                    print(f"Deleted record for article: {title}")
                    continue
                
                scraped_author = ", ".join(art.authors) if art.authors else db_author
                scraped_pub_date = art.publish_date.isoformat() if art.publish_date else db_pub_date
                update_sql = """
                UPDATE crypto_news 
                SET article = %s, Author = COALESCE(%s, Author),
                    Publication_Date = COALESCE(%s, Publication_Date)
                WHERE Title = %s;
                """
                c.execute(update_sql, (main_text, scraped_author, scraped_pub_date, title))
                print(f"✅ Updated details for article: {title}")
            except Exception as e:
                print(f"❌ Error scraping article at {link}: {e}")
                # Drop the record if scraping failed
                c.execute("DELETE FROM crypto_news WHERE Title = %s", (title,))
                print(f"Deleted record for article: {title}")
        conn.commit()
        print("✅ Article details updated in the database.")

    def normalize_and_update_publication_dates(self):
        """
        Connects to PostgreSQL database, retrieves publication dates, normalizes them to "%Y-%m-%d",
        and updates them only if the date isn't already in the correct format.
        """
        conn = self.conn
        c = conn.cursor()
        
        c.execute("SELECT news_id, publication_date FROM crypto_news")
        rows = c.fetchall()
        
        for row in rows:
            news_id = row['news_id']
            pub_date = row['publication_date']
            
            # Skip processing if date is already in the correct format
            try:
                # This ensures the date is strictly "%Y-%m-%d"
                if parser.parse(pub_date).strftime("%Y-%m-%d") == pub_date:
                    continue  # Date already in the target format, skip updating
            except:
                pass  # If parsing fails here, it'll be handled below
                
            # Attempt to normalize date
            normalized_date = self.normalize_date(pub_date)
            
            # Update only if normalization is successful
            if normalized_date:
                c.execute("UPDATE crypto_news SET publication_date = %s WHERE news_id = %s", (normalized_date, news_id))
                print(f"Updated news_id {news_id}: '{pub_date}' -> '{normalized_date}'")
            else:
                print(f"Skipping news_id {news_id} with unparseable date: '{pub_date}'")

        conn.commit()

    def normalize_date(self, date_str):
        """
        Attempts to parse date_str and returns a string formatted as "%Y-%m-%d".
        If parsing fails, returns None.
        """
        if not date_str or date_str.lower() == 'null' or date_str.strip() == '':
            return None
            
        try:
            dt = parser.parse(date_str)
            return dt.strftime("%Y-%m-%d")
        except Exception as e:
            return None


if __name__ == "__main__":
    # Load environment variables already done at the top of the file
    
    # Check for required environment variables
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable not set. News extraction will fail.")
    
    base_url = ["https://cointelegraph.com", "https://decrypt.co", "https://bitcoinmagazine.com", "https://cryptoslate.com", "https://www.coindesk.com", "https://www.bloomberg.com/crypto"]
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL environment variable not set.")
        print("Please set DATABASE_URL in your .env file or container environment.")
        sys.exit(1)
    
    parsed_url = urlparse(db_url)
    db_config = {
        "dbname": parsed_url.path[1:],  # skip leading slash
        "user": parsed_url.username,
        "password": parsed_url.password,
        "host": parsed_url.hostname,
    }
    
    try:
        print(f"Connecting to database: {db_config['host']}/{db_config['dbname']} as {db_config['user']}")
        scrapper = NewsScrapperGeneral(base_url, db_config)
        
        # Uncomment or comment out steps as needed
        # scrapper.find_all_pagination_urls()
        scrapper.get_and_clean_html()
        scrapper.extract_news_articles_with_chatgpt()
        scrapper.flatten_news()
        scrapper.save_to_db()
        scrapper.update_article_details()  # Update article details
        scrapper.normalize_and_update_publication_dates()
        
        # Close database connection
        scrapper.conn.close()
        print("✅ Script completed successfully at:", datetime.now().isoformat())
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


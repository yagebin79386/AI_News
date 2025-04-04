import json
import requests
from pydantic import BaseModel, Field
from typing import List
from urllib.parse import urljoin
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
import psycopg2
import psycopg2.extras
import os
from urllib.parse import urlparse
import openai
from dotenv import load_dotenv


# Define the Pydantic model for extraction response
class ArticleExtractionResponse(BaseModel):
    keywords: List[str] = Field(..., description="Keywords extracted from the article.")
    main_category: str = Field(..., description="The main category of the article.")
    summary: str = Field(..., description="A brief summary of the article in a personal blogger's style.")

class ArticleExtractor:
    def __init__(self, db_config: dict):
        """
        Initialize with the path to the PostgreSQL database and the Corcel API key.
        """

        # ✅ Improved system prompt for strict JSON format
        self.system_prompt = """
            You are an AI assistant for article classification and extraction. Your task is to analyze an article and extract structured information, ensuring that the extracted data **strictly** follows the provided JSON schema. 

            📌 **Guidelines:**
            - **Keywords:** Extract relevant terms from the article.
            - **Main Category:** Select **ONLY** from the following categories:
            1. Breakthrough Research & Frontier AI
            2. Enterprise Adoption & Industrial Automation
            3. AI in Daily Life (health, education, entertainment, etc.)
            4. AI & Jobs: Workplace Transformation & Skills
            5. Ethics, Regulation & Governance
            6. Market Trends, Funding & Investment
            7. Tools, Platforms & Developer Ecosystem
            - **Summary:** Provide an engaging, human-style summary (~3–5 sentences) like a blogger or tech journalist. Focus on **why it matters**, who’s involved, and the **impact on society, work, or innovation**.

            ❌ **Strict Rules:**
            - The `main_category` **must be one of the provided categories**.
            - If the main category **does not match any of the predefined categories**, choose `"AI in Daily Life"` as a fallback.
        """
        
        self.client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        # Connect to the PostgreSQL database.
        self.conn = psycopg2.connect(
            dbname=db_config["dbname"],
            user=db_config["user"],
            password=db_config["password"],
            host=db_config["host"],
            cursor_factory=psycopg2.extras.RealDictCursor
        )

    def _call_llm(self, article_text: str) -> ArticleExtractionResponse:
        """
        Call the Corcel API (using streaming) with the GPT-4o model and return the parsed extraction response.
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": article_text},
        ]
        
        try: 
            # Create a streaming response
            stream = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=10000,
                temperature=0.1,
                stream=True,
                response_format={"type": "json_object"}
            )

            accumulated_chunks = []

            # Process the streaming response
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    accumulated_chunks.append(chunk.choices[0].delta.content)

            # Join accumulated JSON chunks to form a complete JSON string
            extracted_text = "".join(accumulated_chunks).strip()

            # Remove markdown code fences if present
            if extracted_text.startswith("```"):
                lines = extracted_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                extracted_text = "\n".join(lines).strip()

            # Debugging output (print extracted text)
            print("📝 Extracted JSON Text:", extracted_text)

            # Try parsing the full JSON at once
            try:
                parsed_response = json.loads(extracted_text)
                extraction = ArticleExtractionResponse(**parsed_response)
                return extraction
            except Exception as e:
                raise Exception(f"⚠ Failed to parse LLM response for categorization: {str(e)}. Extracted text: {extracted_text}")
        
        except Exception as e:
            raise Exception(f"Calling API error for categorization: {str(e)}")

    def process_articles(self):
        """
        Extract information from articles and update the database.
        """
        articles = self.load_articles()
        cursor = self.conn.cursor()

        for row in articles:
            article_title = row["title"]
            article_text = row["article"]

            try:
                extraction = self._call_llm(article_text)
                
                cursor.execute(
                    """
                    UPDATE news
                    SET keywords = %s, main_category = %s, summary = %s
                    WHERE Title = %s
                    """,
                    (json.dumps(extraction.keywords), extraction.main_category, extraction.summary, article_title)
                )
                self.conn.commit()
                print(f"✅ Processed article: {article_title}")
            except Exception as e:
                print(f"❌ Error processing '{article_title}': {e}")

    def load_articles(self):
        """Load articles missing extracted data."""
        cursor = self.conn.cursor()
        # Delete the row where article is empty
        cursor.execute("""
            DELETE FROM news WHERE article IS NULL
        """)
        # Select articles where extracted
        cursor.execute("""
            SELECT Title, article FROM news 
            WHERE summary IS NULL OR keywords IS NULL OR main_category IS NULL
        """)
        return cursor.fetchall()

    def close(self):
        """Close the database connection."""
        self.conn.close()


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
    
    extractor = ArticleExtractor(db_config=db_config)
    try:
        extractor.process_articles()
    finally:
        extractor.close()

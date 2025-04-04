import json
import requests
from pydantic import BaseModel, Field
from typing import List
from urllib.parse import urljoin, urlparse
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
import psycopg2
import psycopg2.extras
import openai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define the Pydantic model for extraction response
class ArticleExtractionResponse(BaseModel):
    keywords: List[str] = Field(..., description="Keywords extracted from the article.")
    main_category: str = Field(..., description="The main category of the article.")
    summary: str = Field(..., description="A brief summary of the article in a personal blogger's style.")

class ArticleExtractor:
    def __init__(self, db_config=None, api_key=None):
        """
        Initialize with the path to the PostgreSQL database and the OpenAI API key.
        
        Parameters:
        db_config (dict, optional): Database configuration. If not provided, uses environment variables.
        api_key (str, optional): OpenAI API key. If not provided, will try to use the OPENAI_API_KEY environment variable.
        """
        # Get API key from parameter or environment variable
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("OpenAI API key is not provided and not found in environment variables")

        # ✅ Improved system prompt for strict JSON format
        self.system_prompt = """
            You are an AI assistant for article classification and extraction. Your task is to analyze an article and extract structured information, ensuring that the extracted data **strictly** follows the provided JSON schema. 

            📌 **Guidelines:**
            - **Keywords:** Extract relevant terms from the article.
            - **Main Category:** Select **ONLY** from the following categories:
            1. Market Trends & Investment Analysis
            2. Regulatory & Policy Developments
            3. Blockchain Technology & Infrastructure
            4. Decentralized Ecosystem (DeFi, NFTs, dApps)
            5. Security & Cybersecurity
            6. Enterprise Adoption & Institutional Integration
            7. Community, Culture & Thought Leadership
            - **Summary:** Write a personal-blogger-style summary that explains the **main idea** and **significance** of the article in an engaging way.
            
            ❌ **Strict Rules:**
            - The `main_category` **must be one of the provided categories**.
            - If the main category **does not match any of the predefined categories**, choose `"Blockchain Technology & Infrastructure"` as a fallback.
        """

        # If db_config is not provided, use DATABASE_URL environment variable
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
            
            db_config = {
                "dbname": dbname,
                "user": user,
                "password": password,
                "host": host,
                "port": port
            }

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
        Call the OpenAI API with the GPT-4o model and return the parsed extraction response.
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": article_text},
        ]
        
        try:
            # Create the client with API key
            client = openai.OpenAI(api_key=self.api_key)
            
            # Make the API call
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.1,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )

            # Extract the content from the response
            extracted_text = response.choices[0].message.content.strip()

            # Remove markdown code fences if present
            if extracted_text.startswith("```"):
                lines = extracted_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                extracted_text = "\n".join(lines).strip()

            # Debugging output
            print(f"✅ Extracted JSON:\n{extracted_text[:500]}...\n")

            # Parse the JSON response
            try:
                parsed_response = json.loads(extracted_text)
                extraction = ArticleExtractionResponse(**parsed_response)
                return extraction
            except Exception as e:
                raise Exception(f"⚠ Failed to parse LLM response: {str(e)}. Extracted text: {extracted_text}")
        
        except Exception as e:
            print(f"❌ Error with OpenAI API: {e}")
            raise Exception(f"OpenAI API error: {str(e)}")

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
                    UPDATE crypto_news
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
        cursor.execute("""
            SELECT Title, article FROM crypto_news 
            WHERE article IS NOT NULL 
            AND (summary IS NULL OR keywords IS NULL OR main_category IS NULL)
        """)
        return cursor.fetchall()

    def close(self):
        """Close the database connection."""
        self.conn.close()


if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    
    # Create an instance of the ArticleExtractor with default configurations from environment variables
    extractor = ArticleExtractor()
    
    try:
        extractor.process_articles()
    finally:
        extractor.close()

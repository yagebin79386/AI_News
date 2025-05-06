# AI Newsletter

This application automatically scrambles relevant news and uses LLM assistance for news categorization, rephrasing, and selection.

![Newsletter Operation](https://raw.githubusercontent.com/yagebin79386/AI_News/main/assets/Newsletter_operation.gif)

## Features

- **News Scraping**: Automatically scrapes the latest news articles.
- **Categorization**: Utilizes LLM for categorizing news articles.
- **Newsletter Generation**: Generates newsletters based on selected articles.
- **Automated Scheduling**: Uses cron jobs to automate tasks.
=======
# Crypto & Blockchain Newsletter

This application automatically scrambles relevant news and uses LLM assistance for news categorization, rephrasing, and selection.

## Project Introduction

This project is an end-to-end automated solution designed to deliver a cutting-edge crypto & blockchain newsletter. The system combines robust web scraping techniques with advanced artificial intelligence to curate, categorize, and rephrase news content tailored for blockchain enthusiasts.

**Key Components and Tools:**

- **Web Scraping and Data Extraction:**  
  Traditional scraping methods using libraries such as **BeautifulSoup**, **newspaper3k**, and **Selenium** (with **undetected-chromedriver**) extract news content from various sources. CSS selectors are used to pinpoint relevant HTML elements, ensuring high-quality content is captured.

- **AI-Powered Content Processing:**  
  An innovative integration of large language models (LLMs) is used to:
  - **Categorize** articles into specific topics.
  - **Rephrase and summarize** news items for enhanced readability.
  - **Evaluate relevance** of each article, so readers receive only the most pertinent news.

- **Backend and Automation:**  
  Developed in **Python** with the **Flask** framework, the backend coordinates the workflow—from news scraping and AI processing to subscriber management and automated email deliveries. Tools such as **psycopg2-binary** (for database interactions), **gunicorn**, and **supervisord** ensure reliable deployment and operation.

- **Responsive Frontend Design:**  
  The newsletter’s presentation layer is independently crafted using modern **HTML** and **CSS**, including media queries for mobile responsiveness. This design not only offers an attractive visual experience but also simplifies subscription management and preference updates for users.

**Innovative Approach:**

The project uniquely fuses traditional techniques with modern AI methodologies. By combining the precision of CSS-based extraction with the contextual intelligence of AI models, the system achieves:
- **Efficient News Crawling:** Traditional scrapers collect raw data while AI filters and selects the most relevant content.
- **Dynamic Content Categorization:** AI models classify and rephrase articles, ensuring that the newsletter is both engaging and tailored to the interests of crypto and blockchain readers.
- **Enhanced User Experience:** An independently designed, responsive frontend provides subscribers with an intuitive interface for managing their subscriptions and content preferences.

## Features

- **News Scraping:** Automatically scrapes the latest news articles.
- **Categorization:** Utilizes LLM for categorizing news articles.
- **Newsletter Generation:** Generates newsletters based on selected articles.
- **Automated Scheduling:** Uses cron jobs to automate tasks.
>>>>>>> 1ada6fd61a12a7ae3a0809c56bd9f8db25b46474

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/news-crypto.git
   cd news-crypto
   ```

2. **Build the Docker image**:
   ```bash
   docker build -t news-crypto .
   ```

## Usage
<<<<<<< HEAD

- **Run the application**:
  ```bash
  docker run -p 8080:8080 news-crypto
  ```

- **Scripts**:
  - `ScraperNewsLLM.py`: Scrapes news articles.
  - `categorizationLLM.py`: Categorizes articles.
  - `generate_newsletter.py`: Generates newsletters.
  - `Newsletter_send.py`: Sends newsletters.

## Contribution

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Commit your changes (`git commit -am 'Add new feature'`).
4. Push to the branch (`git push origin feature-branch`).
5. Create a new Pull Request.

## Deployment

- **Fly.io**:
  - Ensure you have the Fly CLI installed.
  - Deploy the application:
    ```bash
    flyctl deploy
    ```

- **Domain Setup**:
  - Use the `setup_domain.sh` script to manage domains and SSL certificates.
  - Add domains manually via the Fly.io dashboard if needed.

## License

This project is licensed under the MIT License.
=======
- **Run the application:**
  ```bash
  docker run -p 8080:8080 news-crypto
  ```
- **Scripts:**
ScraperNewsLLM.py: Scrapes news articles.
categorizationLLM.py: Categorizes articles.
generate_newsletter.py: Generates newsletters.
Newsletter_send.py: Sends newsletters.

## Deployment
- **Fly.io:**
  Ensure you have the Fly CLI installed.
  Deploy the application:
  ```bash
  flyctl deploy
  ```
- **Domain Setup:**
  Use the setup_domain.sh script to manage domains and SSL certificates.
  Add domains manually via the Fly.io dashboard if needed.
>>>>>>> 1ada6fd61a12a7ae3a0809c56bd9f8db25b46474

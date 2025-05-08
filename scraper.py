import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import re
import logging
import trafilatura
import random
import time
import os
from serpapi import GoogleSearch

# List of user agents to rotate for requests to avoid being blocked
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
]

def get_random_user_agent():
    """Returns a random user agent from the list"""
    return random.choice(USER_AGENTS)

def search_google(query, num_results=10, research_mode=False):
    """
    Use SerpAPI to retrieve Google search results for the given query
    
    Args:
        query (str): The search query
        num_results (int): Number of results to return
        research_mode (bool): If True, limit results to .edu, .org, and .gov domains
        
    Returns:
        list: List of dictionaries containing search result data
    """
    try:
        api_key = os.environ.get("SERPAPI_API_KEY")
        if not api_key:
            logging.error("SERPAPI_API_KEY environment variable not set")
            raise Exception("API key for search service not configured")
        
        logging.info(f"Searching for: {query}")
        # Set up the search parameters
        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "num": num_results
        }
        
        # Execute the search
        search = GoogleSearch(params)
        results = search.get_dict()
        
        if "error" in results:
            logging.error(f"SerpAPI error: {results['error']}")
            raise Exception(f"Search API error: {results['error']}")
        
        # Process the organic search results
        search_results = []
        if "organic_results" in results:
            for result in results["organic_results"]:
                # Extract relevant data
                title = result.get("title", "No title")
                link = result.get("link", "")
                description = result.get("snippet", "No description available")
                
                # Skip if not a valid link or from Google itself
                if not link.startswith('http') or 'google.com' in link:
                    continue
                
                # Check if Research Mode is enabled, and if so, filter by domain
                if research_mode:
                    # Parse the URL to get the domain
                    domain = urlparse(link).netloc.lower()
                    # Check if the domain ends with educational extensions
                    if not (domain.endswith('.edu') or domain.endswith('.org') or domain.endswith('.gov')):
                        logging.info(f"Research mode: Skipping non-educational site: {domain}")
                        continue
                    
                search_results.append({
                    "title": title,
                    "link": link,
                    "description": description
                })
                
                # Limit the number of results
                if len(search_results) >= num_results:
                    break
        
        logging.info(f"Found {len(search_results)} search results")
        return search_results
    
    except Exception as e:
        logging.error(f"Error retrieving search results: {str(e)}")
        raise Exception(f"Failed to retrieve search results: {str(e)}")

def scrape_website(url):
    """
    Scrape and extract text content from a website
    
    Args:
        url (str): The URL to scrape
        
    Returns:
        str: The extracted text content from the website
    """
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    try:
        logging.info(f"Scraping website: {url}")
        # Use trafilatura to get the website content
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            logging.warning(f"Failed to download content from {url}")
            return "Could not retrieve content from this website."
        
        # Extract the main text content
        text = trafilatura.extract(downloaded)
        
        if not text or text.strip() == "":
            logging.info(f"Trafilatura failed for {url}, using fallback method")
            # Fallback to manual extraction if trafilatura fails
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "header", "footer", "nav"]):
                script.extract()
            
            # Get text and clean it
            text = soup.get_text(separator='\n')
            
            # Clean extra whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Log the length of the extracted text
        text_length = len(text)
        logging.info(f"Extracted {text_length} characters from {url}")
        
        return text
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Error making request to {url}: {str(e)}")
        return f"Error retrieving content: {str(e)}"
    
    except Exception as e:
        logging.error(f"Error scraping website {url}: {str(e)}")
        return f"Error processing website content: {str(e)}"

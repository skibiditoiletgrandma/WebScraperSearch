import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import re
import logging
import trafilatura
import random
import time

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

def search_google(query, num_results=10):
    """
    Scrape Google search results for the given query
    
    Args:
        query (str): The search query
        num_results (int): Number of results to return
        
    Returns:
        list: List of dictionaries containing search result data
    """
    # Prepare the Google search URL
    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}&num={num_results}"
    
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    try:
        # Send the request to Google
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML response
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find search result elements
        search_results = []
        for div in soup.find_all('div', class_='g'):
            # Extract link, title and description
            link_element = div.find('a')
            title_element = div.find('h3')
            
            if link_element and title_element:
                link = link_element.get('href')
                
                # Clean the link (Google prepends links with /url?q=)
                if link.startswith('/url?'):
                    parsed_url = urlparse(link)
                    link = parse_qs(parsed_url.query)['q'][0]
                
                # Skip if not a valid link or from Google itself
                if not link.startswith('http') or 'google.com' in link:
                    continue
                
                title = title_element.get_text()
                
                # Get the description if available
                description_element = div.find('div', class_=['VwiC3b', 'yXK7lf', 'MUxGbd', 'yDYNvb', 'lyLwlc'])
                description = description_element.get_text() if description_element else "No description available"
                
                search_results.append({
                    "title": title,
                    "link": link,
                    "description": description
                })
                
                # Limit the number of results
                if len(search_results) >= num_results:
                    break
        
        return search_results
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Error making request to Google: {str(e)}")
        raise Exception(f"Failed to retrieve search results: {str(e)}")
    
    except Exception as e:
        logging.error(f"Error scraping Google search results: {str(e)}")
        raise Exception(f"Error processing search results: {str(e)}")

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
        # Use trafilatura to get the website content
        downloaded = trafilatura.fetch_url(url, headers=headers)
        if not downloaded:
            logging.warning(f"Failed to download content from {url}")
            return "Could not retrieve content from this website."
        
        # Extract the main text content
        text = trafilatura.extract(downloaded)
        
        if not text or text.strip() == "":
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
        
        return text
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Error making request to {url}: {str(e)}")
        return f"Error retrieving content: {str(e)}"
    
    except Exception as e:
        logging.error(f"Error scraping website {url}: {str(e)}")
        return f"Error processing website content: {str(e)}"

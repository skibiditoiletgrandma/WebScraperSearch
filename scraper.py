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

def search_google(query, num_results=10, research_mode=False, timeout=30, **kwargs):
    """
    Use SerpAPI to retrieve Google search results for the given query

    Args:
        query (str): The search query
        num_results (int): Number of results to return
        research_mode (bool): If True, limit results to .edu, .org, and .gov domains
        timeout (int): Time in seconds to wait for API response before timing out
        **kwargs: Additional parameters, such as:
            hide_wikipedia (bool): If True, filter out Wikipedia results

    Returns:
        list: List of dictionaries containing search result data

    Raises:
        TimeoutError: If the API request exceeds the specified timeout
        ValueError: If there are issues with the API key or search parameters
        ConnectionError: If there are network connectivity issues
        Exception: For other unexpected errors
    """
    logging.debug(f"[SEARCH_DEBUG] Starting search_google with query: {query}, num_results: {num_results}")
    logging.debug(f"[SEARCH_DEBUG] Research mode: {research_mode}, Additional params: {kwargs}")
    
    # Create a unique identifier for this search request
    import uuid
    search_id = str(uuid.uuid4())[:8]
    logging.info(f"[SEARCH:{search_id}] New search request initiated for query: '{query}'")
    
    try:
        # Log environment variable access
        api_key = os.environ.get("SERPAPI_KEY")
        logging.debug(f"[SEARCH:{search_id}] SERPAPI_KEY present: {bool(api_key)}")
        
        if not api_key:
            logging.error(f"[SEARCH:{search_id}] SERPAPI_KEY environment variable not set")
            raise ValueError("API key for search service not configured. Please add a valid SerpAPI key.")

        logging.info(f"Searching for: {query}")
        # Set up the search parameters
        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "num": num_results
        }

        # Execute the search with timeout
        import signal

        class TimeoutHandler:
            def __init__(self, seconds=30):
                self.seconds = seconds
                self.triggered = False

            def handle_timeout(self, signum, frame):
                self.triggered = True
                raise TimeoutError(f"Search API request timed out after {self.seconds} seconds")

        # Set timeout handler
        timeout_handler = TimeoutHandler(timeout)

        # Initialize original_handler to None
        original_handler = None

        # Only use signal on Unix-like systems
        if hasattr(signal, 'SIGALRM'):
            original_handler = signal.signal(signal.SIGALRM, timeout_handler.handle_timeout)
            signal.alarm(timeout)

        try:
            # Execute the search
            search = GoogleSearch(params)
            results = search.get_dict()

            # Reset the alarm and restore original handler
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
                if original_handler is not None:
                    signal.signal(signal.SIGALRM, original_handler)

            # Check for error response
            if not isinstance(results, dict):
                raise ValueError("Invalid response format from search API")

            if "error" in results:
                error_msg = results.get("error", "Unknown error")
                if "Authentication failed" in error_msg:
                    raise ValueError("Invalid API key. Please check your SERPAPI_KEY configuration.")
                elif "quota" in error_msg.lower():
                    raise ValueError("Search quota exceeded. Please try again later.")
                else:
                    raise ValueError(f"Search API error: {error_msg}")

        except TimeoutError as te:
            logging.error(f"SerpAPI timeout: {str(te)}")
            raise TimeoutError(f"Search service took too long to respond. Please try again later.")
        except Exception as e:
            # Reset the alarm and restore original handler in case of other exceptions
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
                if original_handler is not None:
                    signal.signal(signal.SIGALRM, original_handler)
            raise

            # Provide more user-friendly error messages based on common API errors
            if "authorization" in error_msg.lower() or "api key" in error_msg.lower():
                raise ValueError("Invalid API key. Please check your SerpAPI key.")
            elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
                raise ValueError("API usage limit reached. Please try again later.")
            else:
                raise ValueError(f"Search API error: {error_msg}")

        # Validate response format
        if not isinstance(results, dict):
            logging.error("Invalid response format from SerpAPI")
            raise ValueError("Invalid response format from search API")

        # Check for API errors
        if "error" in results:
            error_msg = results.get("error", "Unknown error")
            if "Invalid API key" in error_msg:
                raise ValueError("Invalid API key. Please check your SERPAPI_KEY configuration.")
            logging.error(f"SerpAPI error response: {error_msg}")
            raise ValueError(f"Search API error: {error_msg}")

        # Process organic results
        organic_results = results.get("organic_results", [])
        if not organic_results:
            logging.warning(f"No organic results found for query: {query}")
            return []

        # Process the organic search results
        search_results = []
        for result in organic_results:
            # Extract relevant data
            title = result.get("title", "No title")
            link = result.get("link", "")
            description = result.get("snippet", "No description available")

            # Skip if not a valid link or from Google itself
            if not link.startswith('http') or 'google.com' in link:
                continue

            # Parse the URL to get the domain
            domain = urlparse(link).netloc.lower()

            # Store domain in the result metadata
            result_metadata = {
                "is_wikipedia": 'wikipedia.org' in domain
            }

            # Check if Research Mode is enabled, and if so, filter by domain
            if research_mode:
                # Check if the domain ends with educational extensions
                if not (domain.endswith('.edu') or domain.endswith('.org') or domain.endswith('.gov')):
                    logging.info(f"Research mode: Skipping non-educational site: {domain}")
                    continue

            # Check if filtering out Wikipedia results was requested
            if kwargs.get('hide_wikipedia', False) and 'wikipedia.org' in domain:
                logging.info(f"Wikipedia filter: Skipping Wikipedia result: {domain}")
                continue

            search_results.append({
                "title": title,
                "link": link,
                "description": description,
                "metadata": result_metadata
            })

            # Limit the number of results
            if len(search_results) >= num_results:
                break

        logging.info(f"Found {len(search_results)} search results")
        return search_results

    except TimeoutError as te:
        logging.error(f"Search timeout: {str(te)}")
        raise
    except ValueError as ve:
        logging.error(f"API value error: {str(ve)}")
        raise
    except requests.exceptions.ConnectionError:
        logging.error("Network connection error while connecting to search API")
        raise ConnectionError("Network error while connecting to search service. Please check your internet connection.")
    except Exception as e:
        logging.error(f"Error retrieving search results: {str(e)}")
        raise Exception(f"Search error: {str(e)}")

def scrape_website(url, timeout=20):
    """
    Scrape and extract text content from a website

    Args:
        url (str): The URL to scrape
        timeout (int): Timeout in seconds for HTTP requests

    Returns:
        str: The extracted text content from the website
    """
    # Create a unique ID for this scraping operation
    import uuid
    scrape_id = str(uuid.uuid4())[:8]
    
    logging.info(f"[SCRAPE:{scrape_id}] Starting to scrape website: {url} (timeout: {timeout}s)")
    
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    logging.debug(f"[SCRAPE:{scrape_id}] Using User-Agent: {headers['User-Agent']}")

    try:
        # Use trafilatura to get the website content with timeout
        try:
            logging.info(f"[SCRAPE:{scrape_id}] Using trafilatura to fetch URL: {url}")
            
            # Set a timeout for the download - implement our own timeout mechanism
            # since trafilatura doesn't directly support timeout parameter
            import socket
            logging.debug(f"[SCRAPE:{scrape_id}] Current socket timeout: {socket.getdefaulttimeout()}")
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(timeout)
            logging.debug(f"[SCRAPE:{scrape_id}] Socket timeout temporarily set to: {timeout}s")
            
            try:
                logging.debug(f"[SCRAPE:{scrape_id}] Calling trafilatura.fetch_url()")
                downloaded = trafilatura.fetch_url(url)
                
                if downloaded:
                    logging.info(f"[SCRAPE:{scrape_id}] Successfully downloaded content from {url} (size: {len(downloaded)} bytes)")
                else:
                    logging.warning(f"[SCRAPE:{scrape_id}] Failed to download content from {url}, returned None or empty content")
                    return "Could not retrieve content from this website."
            finally:
                # Restore original timeout
                socket.setdefaulttimeout(original_timeout)
                logging.debug(f"[SCRAPE:{scrape_id}] Socket timeout restored to: {original_timeout}")

            # Extract the main text content
            text = trafilatura.extract(downloaded)

            if text and text.strip() != "":
                # Log the length of the extracted text
                text_length = len(text)
                logging.info(f"Extracted {text_length} characters from {url}")
                return text

            # If we get here, trafilatura failed to extract meaningful content
            logging.info(f"Trafilatura failed for {url}, using fallback method")
        except Exception as trafilatura_error:
            logging.warning(f"Trafilatura error for {url}: {str(trafilatura_error)}")
            logging.info("Falling back to requests/BeautifulSoup method")

        # Fallback to manual extraction if trafilatura fails
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
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

            # Check if we got any meaningful content
            if not text or text.strip() == "":
                return "No meaningful content could be extracted from this website."

            # Log the length of the extracted text
            text_length = len(text)
            logging.info(f"Extracted {text_length} characters from {url} using fallback method")

            return text
        except requests.exceptions.Timeout:
            logging.error(f"Timeout while scraping {url}")
            return "Website took too long to respond. Could not retrieve content."
        except requests.exceptions.RequestException as request_error:
            logging.error(f"Request error for {url}: {str(request_error)}")
            # Return a more user-friendly message instead of the raw error
            return "Could not access this website. The site may be unavailable or blocking automated access."

    except requests.exceptions.Timeout:
        logging.error(f"Timeout while scraping {url}")
        return "Website took too long to respond. Could not retrieve content."

    except requests.exceptions.RequestException as e:
        logging.error(f"Error making request to {url}: {str(e)}")
        if "timeout" in str(e).lower():
            return "Website took too long to respond. Could not retrieve content."
        elif "connection" in str(e).lower():
            return "Could not connect to this website. Please check the URL or try again later."
        else:
            return "Could not retrieve content from this website due to a network error."

    except Exception as e:
        logging.error(f"Error scraping website {url}: {str(e)}")
        return "Error processing website content. The content may be in an unsupported format."
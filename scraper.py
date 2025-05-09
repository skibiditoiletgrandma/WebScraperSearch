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
    Scrape and extract text content from a website with multiple fallback mechanisms.
    
    This function uses a multi-layered approach:
    1. First tries BeautifulSoup for HTML parsing (most reliable for logged-in users)
    2. Falls back to trafilatura if BeautifulSoup fails
    3. Implements multiple request strategies with different SSL settings
    4. Has robust error handling for timeouts and connection issues
    
    Args:
        url (str): The URL to scrape
        timeout (int): Timeout in seconds for HTTP requests

    Returns:
        str: The extracted text content from the website
    """
    # Create a unique ID for this scraping operation
    import uuid
    import requests
    from bs4 import BeautifulSoup
    import trafilatura
    from urllib3.exceptions import InsecureRequestWarning
    from requests.packages.urllib3.exceptions import InsecureRequestWarning as RequestsInsecureRequestWarning
    
    # Suppress only the specific warnings about insecure requests
    import warnings
    warnings.filterwarnings('ignore', category=InsecureRequestWarning)
    warnings.filterwarnings('ignore', category=RequestsInsecureRequestWarning)
    
    scrape_id = str(uuid.uuid4())[:8]
    
    logging.info(f"[SCRAPE:{scrape_id}] Starting to scrape website: {url} (timeout: {timeout}s)")
    
    # Prepare headers with a random user agent
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    
    logging.debug(f"[SCRAPE:{scrape_id}] Using User-Agent: {headers['User-Agent']}")
    
    # Store our final text content here
    html_content = None
    text_content = None
    
    # Track which methods we've tried
    methods_tried = []
    
    # STAGE 1: Try to get the raw HTML content with multiple fallbacks
    # ----------------------------------------------------------------
    
    # Method 1: First try - Standard requests with SSL verification
    try:
        methods_tried.append("requests_verified")
        logging.debug(f"[SCRAPE:{scrape_id}] Trying method 1: Standard requests with verification")
        
        response = requests.get(
            url, 
            headers=headers, 
            timeout=timeout,
            verify=True,  # Standard SSL verification
            allow_redirects=True
        )
        response.raise_for_status()
        html_content = response.text
        logging.debug(f"[SCRAPE:{scrape_id}] Method 1 successful, got {len(html_content)} bytes")
        
    except Exception as e:
        logging.warning(f"[SCRAPE:{scrape_id}] Method 1 failed: {str(e)}")
        
        # Method 2: If first method fails, try without SSL verification
        try:
            methods_tried.append("requests_unverified")
            logging.debug(f"[SCRAPE:{scrape_id}] Trying method 2: Requests without SSL verification")
            
            response = requests.get(
                url, 
                headers=headers, 
                timeout=timeout,
                verify=False,  # Skip SSL verification to handle some SSL errors
                allow_redirects=True
            )
            response.raise_for_status()
            html_content = response.text
            logging.debug(f"[SCRAPE:{scrape_id}] Method 2 successful, got {len(html_content)} bytes")
            
        except Exception as e:
            logging.warning(f"[SCRAPE:{scrape_id}] Method 2 failed: {str(e)}")
            
            # Method 3: If standard methods fail, try trafilatura's built-in fetcher
            try:
                methods_tried.append("trafilatura_fetch")
                logging.debug(f"[SCRAPE:{scrape_id}] Trying method 3: Trafilatura's fetch_url")
                
                downloaded = trafilatura.fetch_url(url)
                if downloaded:
                    html_content = downloaded
                    logging.debug(f"[SCRAPE:{scrape_id}] Method 3 successful")
                else:
                    logging.warning(f"[SCRAPE:{scrape_id}] Method 3 failed: trafilatura returned None")
            except Exception as e:
                logging.warning(f"[SCRAPE:{scrape_id}] Method 3 failed: {str(e)}")
    
    # STAGE 2: If we have HTML content, try to extract the text using different methods
    # ------------------------------------------------------------------------------
    
    if html_content:
        logging.info(f"[SCRAPE:{scrape_id}] Successfully fetched HTML content ({len(html_content)} bytes), extracting text...")
        
        # Method A: Try BeautifulSoup first (works better for logged-in users and complex sites)
        try:
            methods_tried.append("beautifulsoup")
            logging.debug(f"[SCRAPE:{scrape_id}] Trying extraction method A: BeautifulSoup")
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script, style and other non-content elements
            for tag in soup(['script', 'style', 'header', 'footer', 'nav', 'meta']):
                tag.extract()
                
            # Get the text content
            text = soup.get_text(separator='\n')
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text_content = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Check if we got meaningful content
            if text_content and len(text_content.strip()) > 200:  # Require at least 200 chars for "good" content
                logging.debug(f"[SCRAPE:{scrape_id}] Method A successful, extracted {len(text_content)} characters")
            else:
                logging.warning(f"[SCRAPE:{scrape_id}] Method A extracted too little content ({len(text_content) if text_content else 0} chars), will try next method")
                text_content = None  # Reset to try next method
                
        except Exception as e:
            logging.warning(f"[SCRAPE:{scrape_id}] Method A failed: {str(e)}")
            text_content = None
        
        # Method B: If BeautifulSoup didn't get good content, try trafilatura (good for articles)
        if not text_content:
            try:
                methods_tried.append("trafilatura")
                logging.debug(f"[SCRAPE:{scrape_id}] Trying extraction method B: Trafilatura")
                
                extracted = trafilatura.extract(html_content)
                if extracted and len(extracted.strip()) > 0:
                    text_content = extracted
                    logging.debug(f"[SCRAPE:{scrape_id}] Method B successful, extracted {len(text_content)} characters")
                else:
                    logging.warning(f"[SCRAPE:{scrape_id}] Method B failed to extract meaningful content")
            except Exception as e:
                logging.warning(f"[SCRAPE:{scrape_id}] Method B failed: {str(e)}")
    
    # STAGE 3: Final result determination and fallbacks
    # ------------------------------------------------
    
    # If we got content via any method, return it
    if text_content and len(text_content.strip()) > 0:
        content_length = len(text_content)
        logging.info(f"[SCRAPE:{scrape_id}] Successfully extracted {content_length} characters using methods: {', '.join(methods_tried)}")
        return text_content
    
    # If we got HTML but couldn't extract good text, return a fragment of the HTML
    if html_content and len(html_content) > 0:
        # Convert HTML to text as a last resort
        logging.warning(f"[SCRAPE:{scrape_id}] Falling back to raw HTML conversion")
        
        try:
            # Try to extract title at minimum
            soup = BeautifulSoup(html_content, 'html.parser')
            title = soup.title.string if soup.title else "No title"
            
            # Simple HTML to text conversion
            content = re.sub(r'<[^>]+>', ' ', html_content)
            content = re.sub(r'\s+', ' ', content).strip()
            
            # Limit content length to avoid excessively large returns
            if len(content) > 5000:
                content = content[:5000] + "... [content truncated]"
            
            fallback_text = f"Title: {title}\n\nContent extract:\n{content}"
            logging.info(f"[SCRAPE:{scrape_id}] Returning fallback HTML-derived content, {len(fallback_text)} characters")
            return fallback_text
            
        except Exception as e:
            logging.error(f"[SCRAPE:{scrape_id}] Error creating fallback content: {str(e)}")
            return f"Could only retrieve HTML content from this website. Methods tried: {', '.join(methods_tried)}"
    
    # If all extraction methods failed but we have some information, return user-friendly error
    logging.error(f"[SCRAPE:{scrape_id}] All content extraction methods failed for URL: {url}")
    
    if "timeout" in str(methods_tried):
        return "Website took too long to respond. Could not retrieve content."
    elif "connection" in str(methods_tried):
        return "Could not connect to this website. Please check the URL or try again later."
    else:
        return f"Unable to extract content from this website. Methods tried: {', '.join(methods_tried)}"
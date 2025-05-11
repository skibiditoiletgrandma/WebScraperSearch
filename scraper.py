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
from flask import flash

# Import ApiKey model and db from app
# Handle the case where we're importing this module outside of Flask context
try:
    from app import db
    from models import ApiKey
    HAS_DB = True
except ImportError:
    # Mock ApiKey for when models is not available (e.g., during imports)
    class ApiKey:
        @classmethod
        def get_next_active_key(cls, service, current_key_id=None):
            return None
        
        def mark_used(self):
            pass
        
        def record_error(self, error_message):
            pass
    
    HAS_DB = False
    db = None
# List of user agents to rotate for requests to avoid being blocked
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59"
]

def get_random_user_agent():
    """Returns a random user agent from the list"""
    return random.choice(USER_AGENTS)

def search_google(query, num_results=10, research_mode=False, timeout=30, **kwargs):
    """
    Use SerpAPI to retrieve Google search results with multiple API key support and fallback

    Args:
        query (str): The search query
        num_results (int): Number of results to return
        research_mode (bool): If True, limit results to .edu, .org, and .gov domains
        timeout (int): Time in seconds to wait for API response before timing out
        **kwargs: Additional parameters, such as:
            hide_wikipedia (bool): If True, filter out Wikipedia results
            current_key_id (int): ID of API key currently being used (for fallback)

    Returns:
        list: List of dictionaries containing search result data

    Raises:
        TimeoutError: If the API request exceeds the specified timeout
        ValueError: If there are issues with the API key or search parameters
        ConnectionError: If there are network connectivity issues
        Exception: For other unexpected errors
    """
    fallback_attempt = kwargs.get('fallback_attempt', False)
    hide_wikipedia = kwargs.get('hide_wikipedia', False)
    current_key_id = kwargs.get('current_key_id', None)
    
    # If a current key ID is provided, we're in a fallback scenario
    if current_key_id is not None:
        fallback_attempt = True
        
    # Generate a random search ID for tracking in logs
    search_id = ''.join(random.choice('0123456789abcdef') for _ in range(8))
    logging.info(f"[SEARCH:{search_id}] Starting search for: {query}")
    
    # Get the next active API key
    api_key_obj = ApiKey.get_next_active_key('serpapi', current_key_id)
    api_key = None
    
    # If we found an API key in the database, use it
    if api_key_obj is not None:
        api_key = api_key_obj.key
        logging.info(f"[SEARCH:{search_id}] Using API key ID {api_key_obj.id}")
    # Otherwise, try to get key from environment
    else:
        api_key = os.environ.get('SERPAPI_KEY')
        if api_key:
            logging.info(f"[SEARCH:{search_id}] Using API key from environment variables")
        else:
            # No API key available
            logging.error(f"[SEARCH:{search_id}] No SerpAPI key available")
            raise ValueError("No SerpAPI key available. Please add a key in the admin interface or as an environment variable.")
    
    # Set up the timeout handler for SerpAPI request
    class TimeoutHandler:
        def __init__(self, seconds=30):
            self.seconds = seconds
            self.triggered = False
            
        def handle_timeout(self, signum, frame):
            self.triggered = True
            raise TimeoutError(f"SerpAPI request timed out after {self.seconds} seconds")

    # Set up search parameters for SerpAPI
    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": min(100, num_results),  # SerpAPI has a maximum of 100 results
        "start": 0
    }
    
    # Add research mode filter if requested
    if research_mode:
        # Filter to educational, organizational, and government domains
        params["q"] += " site:.edu OR site:.org OR site:.gov"
    
    try:
        # Set up timeout handler
        timeout_handler = TimeoutHandler(seconds=timeout)
        signal.signal(signal.SIGALRM, timeout_handler.handle_timeout)
        signal.alarm(timeout)
        
        try:
            logging.info(f"[SEARCH:{search_id}] Sending request to SerpAPI with params: {params}")
            search = GoogleSearch(params)
            results = search.get_dict()
            signal.alarm(0)  # Cancel the alarm
            
            # If API key object exists, mark it as used
            if api_key_obj is not None and hasattr(api_key_obj, 'mark_used'):
                try:
                    api_key_obj.mark_used()
                    if HAS_DB and db is not None:
                        if HAS_DB and db is not None:
            db.session.commit()
                    logging.debug(f"[SEARCH:{search_id}] Marked API key {api_key_obj.id} as used")
                except Exception as db_err:
                    logging.error(f"[SEARCH:{search_id}] Failed to mark API key usage: {str(db_err)}")
            
        except Exception as e:
            signal.alarm(0)  # Cancel the alarm
            error_msg = str(e)
            logging.error(f"[SEARCH:{search_id}] SerpAPI error: {error_msg}")
            
            # Check if this is an API key error
            key_error = False
            if "Authentication failed" in error_msg or "Invalid API key" in error_msg:
                key_error = True
            elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
                key_error = True
                
            if key_error:
                try:
                    # Record the error
                    api_key_obj.record_error(error_msg)
                    if HAS_DB and db is not None:
                        if HAS_DB and db is not None:
            db.session.commit()
                    logging.warning(f"[SEARCH:{search_id}] API key error recorded for key {api_key_obj.id}: {error_msg}")
                    
                    # If we haven't tried a fallback yet, try the next key
                    if not fallback_attempt:
                        logging.info(f"[SEARCH:{search_id}] Attempting fallback to next API key after error: {error_msg}")
                        kwargs['current_key_id'] = api_key_obj.id
                        
                        # Flash message to user about the fallback
                        flash("We're experiencing issues with the search API. Trying an alternative key...", "warning")
                        
                        # Call this function recursively with the next key
                        return search_google(query, num_results, research_mode, timeout, **kwargs)
                except Exception as db_err:
                    logging.error(f"[SEARCH:{search_id}] Failed to record API key error: {str(db_err)}")
            
            # If this was already a fallback attempt or not a key error, re-raise
            raise
            
        # Handle the results
        if 'error' in results:
            error_msg = results['error']
            logging.error(f"[SEARCH:{search_id}] SerpAPI returned error: {error_msg}")
            
            # Check if this is an API key error
            key_error = False
            if "Authentication failed" in error_msg or "Invalid API key" in error_msg:
                key_error = True
            elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
                key_error = True
                
            if key_error:
                try:
                    # Record the error
                    api_key_obj.record_error(error_msg)
                    if HAS_DB and db is not None:
                        if HAS_DB and db is not None:
            db.session.commit()
                    logging.warning(f"[SEARCH:{search_id}] API key error recorded for key {api_key_obj.id}: {error_msg}")
                    
                    # Try the next key if this wasn't already a fallback attempt
                    if not fallback_attempt:
                        logging.info(f"[SEARCH:{search_id}] Attempting fallback to next API key after error: {error_msg}")
                        kwargs['current_key_id'] = api_key_obj.id
                        
                        # Flash message to user about the fallback
                        flash("We're experiencing issues with the search API. Trying an alternative key...", "warning")
                        
                        # Call this function recursively with the next key
                        return search_google(query, num_results, research_mode, timeout, **kwargs)
                except Exception as db_err:
                    logging.error(f"[SEARCH:{search_id}] Failed to record API key error: {str(db_err)}")
                    
            raise ValueError(f"SerpAPI error: {error_msg}")
        
        # Check if we have organic results
        if 'organic_results' not in results or not results['organic_results']:
            logging.warning(f"[SEARCH:{search_id}] No organic results found")
            return []
        
        # Process the results
        processed_results = []
        for result in results['organic_results']:
            # Skip Wikipedia results if requested
            if hide_wikipedia and 'wikipedia.org' in result.get('link', ''):
                continue
                
            processed_results.append({
                'title': result.get('title', 'No Title'),
                'link': result.get('link', '#'),
                'snippet': result.get('snippet', 'No description available.'),
                'position': result.get('position', 0),
                'source': 'Google (via SerpAPI)'
            })
            
            # Limit to requested number of results
            if len(processed_results) >= num_results:
                break
                
        logging.info(f"[SEARCH:{search_id}] Returning {len(processed_results)} results")
        return processed_results
        
    except TimeoutError as te:
        logging.error(f"[SEARCH:{search_id}] Search timed out: {str(te)}")
        
        # Try fallback if this is a timeout error
        if api_key_obj and not fallback_attempt:
            try:
                api_key_obj.record_error(f"Timeout: {str(te)}")
                if HAS_DB and db is not None:
                    if HAS_DB and db is not None:
            db.session.commit()
                
                # Try the next key
                logging.info(f"[SEARCH:{search_id}] Attempting fallback to next API key after timeout")
                kwargs['current_key_id'] = api_key_obj.id
                
                # Flash message about the fallback
                flash("The search is taking longer than expected. Trying an alternative method...", "warning")
                
                # Call this function recursively with the next key
                return search_google(query, num_results, research_mode, timeout, **kwargs)
            except Exception as db_err:
                logging.error(f"[SEARCH:{search_id}] Failed to record timeout error: {str(db_err)}")
        
        # If no fallback is possible or this was already a fallback, raise the timeout error
        raise
        
    except Exception as e:
        logging.error(f"[SEARCH:{search_id}] Unexpected error: {str(e)}")
        raise

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
    
    # Skip empty URLs
    if not url:
        return "No URL provided for scraping."
    
    # Skip PDFs and other non-HTML content
    if url.lower().endswith(('.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx')):
        return f"This is a document file ({url.split('.')[-1].upper()}) which cannot be scraped directly."
        
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.google.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # Prepare verification modes to try (in order)
    verification_modes = [
        {'verify': True, 'desc': 'with SSL verification'},
        {'verify': False, 'desc': 'without SSL verification (insecure)'}
    ]
    
    # Initialize result with error message
    extracted_text = f"Failed to extract content from {url}"
    
    # Try multiple strategies for robustness
    for verify_mode in verification_modes:
        try:
            # Attempt to get the page with current verification settings
            response = requests.get(
                url, 
                headers=headers, 
                timeout=timeout,
                verify=verify_mode['verify']
            )
            
            # Check if we got a successful response
            if response.status_code == 200:
                # Try BeautifulSoup extraction first (better for normal HTML)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove script and style elements that contain non-content
                for script_or_style in soup(['script', 'style', 'iframe', 'nav', 'footer']):
                    script_or_style.decompose()
                
                # Get text and normalize whitespace
                text = soup.get_text(separator=' ')
                text = re.sub(r'\s+', ' ', text).strip()
                
                # If BeautifulSoup extraction yielded little text, try trafilatura
                if len(text) < 500:
                    try:
                        trafilatura_text = trafilatura.extract(response.text)
                        if trafilatura_text and len(trafilatura_text) > len(text):
                            text = trafilatura_text
                    except Exception as e:
                        logging.warning(f"Trafilatura extraction failed for {url}: {str(e)}")
                
                # If we got substantial text, return it
                if len(text) > 200:
                    return text
                    
                # If text is still too short, continue to next extraction method
                extracted_text = f"Limited content extracted from {url} (only {len(text)} characters)"
                
            elif response.status_code == 403 or response.status_code == 401:
                extracted_text = f"Access denied for {url} (requires login or subscription)"
                break  # No point trying other verification modes
                
            elif response.status_code == 404:
                extracted_text = f"Page not found: {url}"
                break  # No point trying other verification modes
                
            else:
                extracted_text = f"Failed to access {url} (HTTP {response.status_code})"
                # Continue to next verification mode
                
        except requests.exceptions.Timeout:
            extracted_text = f"Timeout occurred while fetching {url}"
            # Continue to next verification mode
            
        except requests.exceptions.SSLError:
            # Only log this; we'll try without verification next
            logging.warning(f"SSL error for {url}, trying without verification")
            continue
            
        except requests.exceptions.ConnectionError:
            extracted_text = f"Connection error when accessing {url}"
            # Continue to next verification mode
            
        except Exception as e:
            extracted_text = f"Error extracting text from {url}: {str(e)}"
            logging.error(f"Unexpected error scraping {url}: {str(e)}")
            # Continue to next verification mode
    
    # If we get here, all extraction methods failed
    return extracted_text
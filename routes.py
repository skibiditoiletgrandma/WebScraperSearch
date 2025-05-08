import logging
from flask import render_template, request, jsonify, flash, redirect, url_for
from app import app
from scraper import search_google, scrape_website
from summarizer import summarize_text
import traceback
import time
import os

@app.route("/")
def index():
    """Route for the home page"""
    # Check if API key is available
    has_api_key = bool(os.environ.get("SERPAPI_API_KEY"))
    return render_template("index.html", has_api_key=has_api_key)

@app.route("/search", methods=["POST"])
def search():
    """Handle search queries and return results"""
    query = request.form.get("query", "")
    
    if not query:
        flash("Please enter a search query", "warning")
        return redirect(url_for("index"))
    
    # Check if API key is available
    if not os.environ.get("SERPAPI_API_KEY"):
        flash("Search API key is not configured. Please contact the administrator.", "danger")
        return redirect(url_for("index"))
    
    try:
        # Get search results from Google using SerpAPI
        search_results = search_google(query)
        
        if not search_results:
            flash("No search results found", "info")
            return render_template("results.html", query=query, results=[])
        
        # Process each search result to get summaries
        processed_results = []
        for result in search_results:
            try:
                logging.info(f"Processing result: {result['link']}")
                
                # Extract text content from the website
                content = scrape_website(result["link"])
                
                # Generate a summary of the content
                summary = summarize_text(content, result["title"])
                
                processed_results.append({
                    "title": result["title"],
                    "link": result["link"],
                    "description": result["description"],
                    "summary": summary
                })
                
                # Add a short delay to avoid overwhelming target servers
                time.sleep(0.5)
                
            except Exception as e:
                logging.error(f"Error processing {result['link']}: {str(e)}")
                continue
        
        # Log the total number of processed results
        logging.info(f"Processed {len(processed_results)} results out of {len(search_results)} search results")
        
        return render_template("results.html", query=query, results=processed_results)
    
    except Exception as e:
        error_details = traceback.format_exc()
        logging.error(f"Search error: {str(e)}\n{error_details}")
        flash(f"Error processing your search request: {str(e)}", "danger")
        return redirect(url_for("index"))

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template("index.html", error="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return render_template("index.html", error="Internal server error"), 500

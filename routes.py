import logging
from flask import render_template, request, jsonify, flash, redirect, url_for
from app import app, db
from scraper import search_google, scrape_website
from summarizer import summarize_text
from models import SearchQuery, SearchResult
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
        
        # Create a new search query record in the database
        new_search = SearchQuery()
        new_search.query_text = query
        new_search.ip_address = request.remote_addr
        
        # Save to database (if available)
        try:
            db.session.add(new_search)
            db.session.commit()
            logging.info(f"Saved search query to database: {query}")
        except Exception as db_error:
            logging.error(f"Error saving search query to database: {str(db_error)}")
            db.session.rollback()
        
        # Process each search result to get summaries
        processed_results = []
        for index, result in enumerate(search_results):
            try:
                logging.info(f"Processing result: {result['link']}")
                
                # Extract text content from the website
                content = scrape_website(result["link"])
                
                # Generate a summary of the content
                summary = summarize_text(content, result["title"])
                
                processed_result = {
                    "title": result["title"],
                    "link": result["link"],
                    "description": result["description"],
                    "summary": summary
                }
                
                processed_results.append(processed_result)
                
                # Save search result to database (if available)
                try:
                    # Only save to database if the search query was successfully saved
                    if new_search.id:
                        search_result = SearchResult()
                        search_result.search_query_id = new_search.id
                        search_result.title = result["title"]
                        search_result.link = result["link"]
                        search_result.description = result["description"]
                        search_result.summary = summary
                        search_result.rank = index + 1
                        db.session.add(search_result)
                except Exception as db_error:
                    logging.error(f"Error saving search result to database: {str(db_error)}")
                
                # Add a short delay to avoid overwhelming target servers
                time.sleep(0.5)
                
            except Exception as e:
                logging.error(f"Error processing {result['link']}: {str(e)}")
                continue
        
        # Commit all search results to database
        try:
            db.session.commit()
            logging.info(f"Saved {len(processed_results)} search results to database")
        except Exception as db_error:
            logging.error(f"Error committing search results to database: {str(db_error)}")
            db.session.rollback()
        
        # Log the total number of processed results
        logging.info(f"Processed {len(processed_results)} results out of {len(search_results)} search results")
        
        return render_template("results.html", query=query, results=processed_results)
    
    except Exception as e:
        error_details = traceback.format_exc()
        logging.error(f"Search error: {str(e)}\n{error_details}")
        flash(f"Error processing your search request: {str(e)}", "danger")
        return redirect(url_for("index"))

@app.route("/history")
def history():
    """Display search history"""
    try:
        # Get the most recent searches
        recent_searches = SearchQuery.query.order_by(SearchQuery.timestamp.desc()).limit(20).all()
        return render_template("history.html", searches=recent_searches)
    except Exception as e:
        logging.error(f"Error retrieving search history: {str(e)}")
        flash("Unable to retrieve search history", "warning")
        return redirect(url_for("index"))

@app.route("/history/<int:search_id>")
def view_search(search_id):
    """View a specific search and its results"""
    try:
        # Get the search query
        search = SearchQuery.query.get_or_404(search_id)
        # Get the results for this search
        results = SearchResult.query.filter_by(search_query_id=search_id).order_by(SearchResult.rank).all()
        
        return render_template("results.html", 
                              query=search.query_text, 
                              results=[{
                                  "title": r.title,
                                  "link": r.link,
                                  "description": r.description,
                                  "summary": r.summary
                              } for r in results],
                              from_history=True)
    except Exception as e:
        logging.error(f"Error retrieving search details: {str(e)}")
        flash("Unable to retrieve search details", "warning")
        return redirect(url_for("history"))

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template("index.html", error="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return render_template("index.html", error="Internal server error"), 500

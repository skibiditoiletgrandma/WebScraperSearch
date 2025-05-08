import logging
import traceback
import time
import os
from flask import render_template, request, jsonify, flash, redirect, url_for, current_app
from werkzeug.exceptions import HTTPException, NotFound, InternalServerError  # For error handling
from app import app, db
from scraper import search_google, scrape_website
from summarizer import summarize_text
from suggestions import get_suggestions_for_ui
from models import SearchQuery, SearchResult, SummaryFeedback

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
        new_search = SearchQuery(
            query_text=query,
            ip_address=request.remote_addr
        )
        
        # Create a flag to track if search was saved to database
        search_saved = False
        
        # Save to database (if available)
        try:
            db.session.add(new_search)
            db.session.commit()
            search_saved = True  # Mark as saved successfully
            logging.info(f"Saved search query to database: {query}")
        except Exception as db_error:
            logging.error(f"Error saving search query to database: {str(db_error)}")
            try:
                db.session.rollback()
            except:
                pass
        
        # Process each search result to get summaries
        processed_results = []
        for index, result in enumerate(search_results):
            try:
                logging.info(f"Processing result: {result['link']}")
                
                # Extract text content from the website
                content = scrape_website(result["link"])
                
                # Generate a summary of the content
                summary = summarize_text(content, result["title"])
                
                # Save search result to database (if available)
                search_result = None
                try:
                    # Only save to database if the search query was successfully saved
                    if search_saved and new_search.id is not None:
                        search_result = SearchResult(
                            search_query_id=new_search.id,
                            title=result["title"],
                            link=result["link"],
                            description=result["description"],
                            summary=summary,
                            rank=index + 1
                        )
                        db.session.add(search_result)
                        db.session.flush()  # Flush to get the ID without committing
                        
                except Exception as db_error:
                    logging.error(f"Error saving search result to database: {str(db_error)}")
                
                processed_result = {
                    "id": search_result.id if search_result else None,
                    "title": result["title"],
                    "link": result["link"],
                    "description": result["description"],
                    "summary": summary
                }
                
                processed_results.append(processed_result)
                
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
                                  "id": r.id,
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
    logging.warning(f"404 error: {str(e)}")
    return render_template("error.html", error="Page not found", status_code=404), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    logging.error(f"500 error: {str(e)}")
    return render_template("error.html", error="Internal server error", status_code=500), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all other exceptions"""
    logging.error(f"Unhandled exception: {str(e)}")
    # Pass through HTTP errors
    if isinstance(e, HTTPException):
        return e
    # Handle non-HTTP exceptions with 500 error
    return render_template("error.html", error=f"Server error: {str(e)}", status_code=500), 500

@app.route("/feedback/<int:result_id>", methods=["POST"])
def submit_feedback(result_id):
    """Handle summary feedback submission"""
    try:
        # Get the search result
        search_result = SearchResult.query.get_or_404(result_id)
        
        # Create a new feedback record
        feedback = SummaryFeedback(
            search_result_id=result_id,
            rating=int(request.form.get("rating", 0)),
            comment=request.form.get("comment", ""),
            helpful="helpful" in request.form,
            accurate="accurate" in request.form,
            complete="complete" in request.form,
            ip_address=request.remote_addr
        )
        
        # Save to database
        db.session.add(feedback)
        db.session.commit()
        
        # Flash success message
        flash("Thank you for your feedback! It helps us improve our summaries.", "success")
        
        # Redirect back to the search results
        return redirect(url_for("view_search", search_id=search_result.search_query_id))
    
    except Exception as e:
        logging.error(f"Error submitting feedback: {str(e)}")
        flash("Unable to submit feedback", "danger")
        return redirect(url_for("history"))

@app.route("/feedback")
def view_feedback():
    """View all feedback for developers"""
    try:
        # Get all feedback with related search results
        feedback_list = SummaryFeedback.query.order_by(SummaryFeedback.timestamp.desc()).limit(50).all()
        
        # Calculate statistics
        feedback_count = SummaryFeedback.query.count()
        
        # Average rating (default to 0 if no feedback)
        average_rating = 0
        if feedback_count > 0:
            average_rating = db.session.query(db.func.avg(SummaryFeedback.rating)).scalar() or 0
            
        # Count attributes
        helpful_count = SummaryFeedback.query.filter_by(helpful=True).count()
        accurate_count = SummaryFeedback.query.filter_by(accurate=True).count()
        complete_count = SummaryFeedback.query.filter_by(complete=True).count()
        
        # Rating distribution
        rating_distribution = {}
        for i in range(1, 6):
            rating_distribution[i] = SummaryFeedback.query.filter_by(rating=i).count()
        
        return render_template(
            "feedback.html",
            feedback_list=feedback_list,
            feedback_count=feedback_count,
            average_rating=average_rating,
            helpful_count=helpful_count,
            accurate_count=accurate_count,
            complete_count=complete_count,
            rating_distribution=rating_distribution
        )
    
    except Exception as e:
        logging.error(f"Error retrieving feedback: {str(e)}")
        flash("Unable to retrieve feedback", "warning")
        return redirect(url_for("index"))

@app.route("/api/suggestions", methods=["GET"])
def get_search_suggestions():
    """API endpoint to get search query suggestions"""
    query = request.args.get("query", "").strip()
    
    if not query or len(query) < 3:
        return jsonify({
            "success": False,
            "suggestions": []
        })
    
    try:
        # Get suggestions using our suggestions module
        suggestions = get_suggestions_for_ui(query, db)
        
        return jsonify({
            "success": True,
            "suggestions": suggestions
        })
    
    except Exception as e:
        logging.error(f"Error generating suggestions: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "suggestions": []
        })

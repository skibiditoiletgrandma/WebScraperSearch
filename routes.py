import logging
import traceback
import time
import os
import uuid
from datetime import datetime, timedelta
from flask import render_template, request, jsonify, flash, redirect, url_for, current_app, session
from werkzeug.exceptions import HTTPException, NotFound, InternalServerError  # For error handling
from flask_login import login_user, logout_user, current_user, login_required
from functools import wraps
from app import app, db
from scraper import search_google, scrape_website
from summarizer import summarize_text
from suggestions import get_suggestions_for_ui
from models import SearchQuery, SearchResult, SummaryFeedback, User, AnonymousSearchLimit
from forms import LoginForm, RegistrationForm

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("You must be an admin to access this page.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def index():
    """Route for the home page"""
    # Check if API key is available
    has_api_key = bool(os.environ.get("SERPAPI_API_KEY"))
    
    # Get remaining searches based on authentication status
    remaining_searches = 0
    
    if current_user.is_authenticated:
        # For logged-in users: Daily limit of 15 searches
        remaining_searches = current_user.remaining_searches()
    else:
        # For anonymous users: Total limit of 3 searches
        # Get the anonymous session ID
        if 'anon_id' in session:
            session_id = session['anon_id']
            # Check for existing search limit record
            anon_limit = AnonymousSearchLimit.query.filter_by(session_id=session_id).first()
            if anon_limit:
                remaining_searches = anon_limit.remaining_searches()
            else:
                # No searches used yet
                remaining_searches = 3
        else:
            # New anonymous session
            remaining_searches = 3
    
    return render_template("index.html", has_api_key=has_api_key, remaining_searches=remaining_searches)

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
        
    # Check search limits based on authentication status
    if current_user.is_authenticated:
        # For logged-in users: Check daily search limit (15 searches per day)
        if not current_user.check_search_limit():
            flash("You have reached your daily search limit of 15 searches. Please try again tomorrow.", "warning")
            return redirect(url_for("index"))
        # Increment the user's search count if they are under the limit
        current_user.increment_search_count()
        
        # Display remaining searches for the user
        remaining = current_user.remaining_searches()
        flash(f"You have {remaining} searches remaining today.", "info")
        
    else:
        # For anonymous users: Check lifetime search limit (3 searches)
        # Make sure we have a unique identifier in the session
        if 'anon_id' not in session:
            # Create a unique ID for this anonymous user's session
            session.permanent = True  # Make the session persistent
            app.permanent_session_lifetime = timedelta(days=365)  # Session lasts for 1 year
            session['anon_id'] = str(uuid.uuid4())
            
        # Use our unique session ID as the identifier
        session_id = session['anon_id']
            
        # Get or create an anonymous search limit record
        anon_limit = AnonymousSearchLimit.query.filter_by(session_id=session_id).first()
        
        if not anon_limit:
            # Create new record if none exists
            anon_limit = AnonymousSearchLimit(
                session_id=session_id,
                ip_address=request.remote_addr,
                search_count=0
            )
            try:
                db.session.add(anon_limit)
                db.session.commit()
            except Exception as e:
                logging.error(f"Error creating anonymous search limit record: {str(e)}")
                db.session.rollback()
        
        # Check if anonymous user has reached their search limit
        if not anon_limit.check_search_limit():
            flash("You have used all 3 of your anonymous searches. Please register for a free account to get 15 searches per day.", "warning")
            return redirect(url_for("index"))
            
        # Increment the anonymous user's search count
        anon_limit.increment_search_count()
        
        # Display remaining searches for the anonymous user
        remaining = anon_limit.remaining_searches()
        flash(f"You have {remaining} anonymous searches remaining. Register for a free account to get 15 searches per day.", "info")
        
        try:
            db.session.commit()
        except Exception as e:
            logging.error(f"Error updating anonymous search limit: {str(e)}")
            db.session.rollback()
    
    try:
        # Get search results from Google using SerpAPI
        search_results = search_google(query)
        
        if not search_results:
            flash("No search results found", "info")
            return render_template("results.html", query=query, results=[])
        
        # Create a new search query record in the database
        new_search = SearchQuery(
            query_text=query,
            ip_address=request.remote_addr,
            user_id=current_user.id if current_user.is_authenticated else None,
            is_public=True  # Default to public searches
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
        # Get the most recent searches based on user login status
        if current_user.is_authenticated:
            # Show user's own searches
            recent_searches = SearchQuery.query.filter_by(
                user_id=current_user.id
            ).order_by(SearchQuery.timestamp.desc()).limit(20).all()
        else:
            # Show only public searches for anonymous users
            recent_searches = SearchQuery.query.filter_by(
                is_public=True
            ).order_by(SearchQuery.timestamp.desc()).limit(20).all()
            
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
        
        # Check access permissions:
        # 1. If user is logged in and is the owner of the search
        # 2. If search is public
        # 3. If user is an admin
        is_owner = current_user.is_authenticated and search.user_id == current_user.id
        is_public = search.is_public
        is_admin = current_user.is_authenticated and current_user.is_admin
        
        if not (is_owner or is_public or is_admin):
            flash("You don't have permission to view this search", "warning")
            return redirect(url_for("history"))
        
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
@admin_required
def view_feedback():
    """View all feedback for developers - admin only"""
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login route"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
        
        # Log in the user
        login_user(user, remember=form.remember_me.data)
        
        # Update last login time
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Redirect to requested page or index
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('index')
        
        flash(f'Welcome back, {user.username}!', 'success')
        return redirect(next_page)
    
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """User logout route"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route("/share/<int:result_id>")
def share_summary(result_id):
    """View a shared summary"""
    try:
        # Get the search result
        result = SearchResult.query.get_or_404(result_id)
        
        # Increment share count if accessed directly (not from search results page)
        referrer = request.referrer or ""
        if not referrer.endswith(f"/history/{result.search_query_id}") and not referrer.endswith("/results"):
            username = current_user.username if current_user.is_authenticated else None
            result.increment_share_count(username)
            db.session.commit()
        
        # Get related results from the same search
        related_results = SearchResult.query.filter(
            SearchResult.search_query_id == result.search_query_id,
            SearchResult.id != result.id
        ).order_by(SearchResult.rank).limit(5).all()
        
        return render_template(
            "share_summary.html", 
            result=result, 
            related_results=related_results
        )
    
    except Exception as e:
        logging.error(f"Error retrieving shared summary: {str(e)}")
        flash("Unable to retrieve the requested summary", "warning")
        return redirect(url_for("index"))

@app.route("/api/share/<int:result_id>", methods=["POST"])
@login_required
def api_share_summary(result_id):
    """API endpoint for sharing a summary"""
    try:
        # Get the search result
        result = SearchResult.query.get_or_404(result_id)
        
        # Increment share count
        result.increment_share_count(current_user.username)
        db.session.commit()
        
        # Generate share URL
        share_url = url_for('share_summary', result_id=result.id, _external=True)
        
        return jsonify({
            "success": True,
            "share_url": share_url,
            "share_count": result.share_count
        })
    
    except Exception as e:
        logging.error(f"Error sharing summary: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

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

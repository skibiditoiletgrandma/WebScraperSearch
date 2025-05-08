import logging
import traceback
import time
import os
import uuid
import io
from datetime import datetime, timedelta
from flask import render_template, request, jsonify, flash, redirect, url_for, current_app, session, send_file
from werkzeug.exceptions import HTTPException, NotFound, InternalServerError  # For error handling
from flask_login import login_user, logout_user, current_user, login_required
from exporters import export_to_pdf, export_to_markdown, export_to_notion
from functools import wraps
from app import app, db
from scraper import search_google, scrape_website
from summarizer import summarize_text
from suggestions import get_suggestions_for_ui
from models import SearchQuery, SearchResult, SummaryFeedback, User, AnonymousSearchLimit, Citation
from forms import LoginForm, RegistrationForm, CitationForm, SettingsForm
from db_migrations import handle_db_error

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
        # Check if research mode is enabled
        research_mode = bool(request.form.get('research_mode'))
        
        # Determine number of results pages to fetch
        num_pages = 1  # Default is 1 page for anonymous users
        hide_wikipedia = False  # Default for anonymous users
        show_feedback = True  # Default for anonymous users
        
        # Summary settings defaults for anonymous users
        generate_summaries = True
        summary_depth = 3
        summary_complexity = 3
        
        if current_user.is_authenticated:
            # For logged-in users, use their preferences
            num_pages = current_user.search_pages_limit or 1
            hide_wikipedia = current_user.hide_wikipedia or False
            show_feedback = current_user.show_feedback_features if current_user.show_feedback_features is not None else False
            
            # Summary settings for logged-in users
            generate_summaries = current_user.generate_summaries if current_user.generate_summaries is not None else True
            summary_depth = current_user.summary_depth if current_user.summary_depth is not None else 3
            summary_complexity = current_user.summary_complexity if current_user.summary_complexity is not None else 3
        
        # Get search results from Google using SerpAPI
        search_results = search_google(
            query, 
            num_results=10*num_pages, 
            research_mode=research_mode, 
            hide_wikipedia=hide_wikipedia
        )
        
        # Check if any of the search results were from Wikipedia before filtering
        has_wikipedia_results = any(
            result.get('metadata', {}).get('is_wikipedia', False) 
            for result in search_results
        ) if hide_wikipedia else False
        
        if not search_results:
            flash("No search results found", "info")
            return render_template("results.html", query=query, results=[], 
                                  show_feedback=not show_feedback, 
                                  research_mode=research_mode,
                                  wikipedia_popup=False)
        
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
                
                # Generate a summary of the content if enabled, otherwise use the description
                if generate_summaries:
                    summary = summarize_text(
                        content, 
                        result["title"],
                        depth=summary_depth,
                        complexity=summary_complexity
                    )
                else:
                    # If summaries are disabled, use the description as the summary
                    summary = f"[Summary generation disabled] {result['description']}"
                
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
        
        return render_template("results.html", 
                              query=query, 
                              results=processed_results,
                              research_mode=research_mode,
                              show_feedback=not show_feedback,
                              wikipedia_popup=has_wikipedia_results,
                              generate_summaries=generate_summaries)
    
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
        
        # Determine user preferences based on authentication status
        show_feedback = True
        generate_summaries = True
        
        if current_user.is_authenticated:
            show_feedback = current_user.show_feedback_features if current_user.show_feedback_features is not None else False
            generate_summaries = current_user.generate_summaries if current_user.generate_summaries is not None else True
            
        return render_template("results.html", 
                              query=search.query_text, 
                              results=[{
                                  "id": r.id,
                                  "title": r.title,
                                  "link": r.link,
                                  "description": r.description,
                                  "summary": r.summary
                              } for r in results],
                              from_history=True,
                              show_feedback=not show_feedback,
                              generate_summaries=generate_summaries,
                              wikipedia_popup=False)
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
    
    # Try to handle database schema errors
    from sqlalchemy.exc import OperationalError, ProgrammingError
    if isinstance(e, (OperationalError, ProgrammingError)):
        # Try to fix database errors
        if handle_db_error(e):
            # If the error was successfully handled, redirect to the previous page
            logging.info("Database error was automatically fixed, redirecting...")
            flash("The system has been updated. Please try again.", "info")
            # Try to get the referrer URL
            referrer = request.referrer or url_for('index')
            return redirect(referrer)
    
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


@app.route("/citations", methods=["GET", "POST"])
def citations():
    """Citation generator page"""
    form = CitationForm()
    
    # Check if we have a previously stored citation in the session
    citation_result = session.get('citation_result', None)
    
    if form.validate_on_submit():
        try:
            # Create a Citation object from form data
            # Create a Citation object with data from the form
            # For each field, ensure it's not None before accessing
            title = form.title.data or ""
            authors = form.authors.data or ""
            formatted_authors = authors.replace("\r\n", ";").replace("\n", ";")
            source_type = form.source_type.data or ""
            citation_style = form.citation_style.data or ""
            
            citation = Citation(
                title=title,
                authors=formatted_authors,
                source_type=source_type,
                citation_style=citation_style,
                publisher=form.publisher.data or "",
                publication_date=form.publication_date.data or "",
                journal_name=form.journal_name.data or "",
                volume=form.volume.data or "",
                issue=form.issue.data or "",
                pages=form.pages.data or "",
                url=form.url.data or "",
                access_date=form.access_date.data or "",
                doi=form.doi.data or "",
                user_id=current_user.id if current_user.is_authenticated else None
            )
            
            # Generate the formatted citation based on selected style
            citation_result = citation.get_formatted_citation()
            
            # Store the citation in the session to persist it between page reloads
            session['citation_result'] = citation_result
            
            # Save to database if user is authenticated
            if current_user.is_authenticated:
                db.session.add(citation)
                db.session.commit()
                flash("Citation generated and saved to your account.", "success")
            else:
                flash("Citation generated. Create an account to save citations for future reference.", "info")
                
        except Exception as e:
            flash(f"Error generating citation: {str(e)}", "danger")
            logging.error(f"Citation generation error: {str(e)}")
    
    return render_template("citations.html", form=form, citation_result=citation_result)


@app.route("/clear-citation")
def clear_citation():
    """Clear the citation from the session"""
    if 'citation_result' in session:
        session.pop('citation_result')
        flash("Citation cleared.", "info")
    return redirect(url_for('citations'))


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """User settings page"""
    form = SettingsForm()
    
    # When form is submitted
    if form.validate_on_submit():
        try:
            # Update general settings
            current_user.search_pages_limit = form.search_pages_limit.data
            current_user.hide_wikipedia = form.hide_wikipedia.data
            current_user.show_feedback_features = form.show_feedback_features.data
            
            # Update summary settings
            current_user.generate_summaries = form.generate_summaries.data
            current_user.summary_depth = form.summary_depth.data
            current_user.summary_complexity = form.summary_complexity.data
            
            db.session.commit()
            flash("Settings updated successfully", "success")
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating settings: {str(e)}", "danger")
    
    # Pre-populate form with current settings
    if request.method == 'GET':
        # Ensure there are default values if fields are None
        # General settings
        form.search_pages_limit.data = current_user.search_pages_limit if current_user.search_pages_limit is not None else 1
        form.hide_wikipedia.data = current_user.hide_wikipedia if current_user.hide_wikipedia is not None else False
        form.show_feedback_features.data = current_user.show_feedback_features if current_user.show_feedback_features is not None else False
        
        # Summary settings
        form.generate_summaries.data = current_user.generate_summaries if current_user.generate_summaries is not None else True
        form.summary_depth.data = current_user.summary_depth if current_user.summary_depth is not None else 3
        form.summary_complexity.data = current_user.summary_complexity if current_user.summary_complexity is not None else 3
    
    return render_template('settings.html', form=form)


@app.route("/export/<int:search_id>/<format>")
def export_search(search_id, format):
    """Export search results in various formats (PDF, Markdown, Notion)"""
    try:
        # Get the search query
        search = SearchQuery.query.get_or_404(search_id)
        
        # Check access permissions
        is_owner = current_user.is_authenticated and search.user_id == current_user.id
        is_public = search.is_public
        is_admin = current_user.is_authenticated and current_user.is_admin
        
        if not (is_owner or is_public or is_admin):
            flash("You don't have permission to export this search", "warning")
            return redirect(url_for("history"))
        
        # Get the results for this search
        results = SearchResult.query.filter_by(search_query_id=search_id).order_by(SearchResult.rank).all()
        
        # Prepare results for export
        export_results = [{
            "title": r.title,
            "link": r.link,
            "description": r.description,
            "summary": r.summary
        } for r in results]
        
        # Check if we have any results to export
        if not export_results:
            flash("No results to export", "warning")
            return redirect(url_for("view_search", search_id=search_id))
        
        # Handle export based on requested format
        if format == "pdf":
            try:
                # Generate PDF content
                pdf_bytes = export_to_pdf(search.query_text, export_results)
                
                # Return as downloadable file
                buffer = io.BytesIO(pdf_bytes)
                buffer.seek(0)
                
                # Generate filename based on search query
                filename = f"search-{search.query_text[:30].replace(' ', '_')}.pdf"
                
                return send_file(
                    buffer,
                    download_name=filename,
                    as_attachment=True,
                    mimetype='application/pdf'
                )
            except Exception as e:
                logging.error(f"Error exporting to PDF: {str(e)}")
                flash("Error generating PDF export. Please try again later.", "danger")
                return redirect(url_for("view_search", search_id=search_id))
                
        elif format == "markdown":
            try:
                # Generate Markdown content
                md_content = export_to_markdown(search.query_text, export_results)
                
                # Return as downloadable file
                buffer = io.BytesIO(md_content.encode('utf-8'))
                buffer.seek(0)
                
                # Generate filename based on search query
                filename = f"search-{search.query_text[:30].replace(' ', '_')}.md"
                
                return send_file(
                    buffer,
                    download_name=filename,
                    as_attachment=True,
                    mimetype='text/markdown'
                )
            except Exception as e:
                logging.error(f"Error exporting to Markdown: {str(e)}")
                flash("Error generating Markdown export. Please try again later.", "danger")
                return redirect(url_for("view_search", search_id=search_id))
                
        elif format == "notion":
            # For Notion, we need to redirect to a form to get the Notion API token and database ID
            return redirect(url_for("export_to_notion_form", search_id=search_id))
            
        else:
            flash(f"Unsupported export format: {format}", "warning")
            return redirect(url_for("view_search", search_id=search_id))
            
    except Exception as e:
        logging.error(f"Error exporting search: {str(e)}")
        flash("Error exporting search. Please try again later.", "danger")
        return redirect(url_for("history"))


@app.route("/export/notion/<int:search_id>", methods=["GET", "POST"])
def export_to_notion_form(search_id):
    """Form to collect Notion API token and database ID for export"""
    try:
        # Make sure we have a valid search ID
        search = SearchQuery.query.get_or_404(search_id)
        
        # Check access permissions 
        is_owner = current_user.is_authenticated and search.user_id == current_user.id
        is_public = search.is_public
        is_admin = current_user.is_authenticated and current_user.is_admin
        
        if not (is_owner or is_public or is_admin):
            flash("You don't have permission to export this search", "warning")
            return redirect(url_for("history"))
            
        # Check if user submitted the form
        if request.method == "POST":
            notion_token = request.form.get("notion_token", "").strip()
            database_id = request.form.get("database_id", "").strip()
            
            # Basic validation
            if not notion_token or not database_id:
                flash("Both Notion API token and database ID are required.", "warning")
                return render_template("notion_export.html", search_id=search_id)
                
            # Get the results for this search
            results = SearchResult.query.filter_by(search_query_id=search_id).order_by(SearchResult.rank).all()
            
            # Prepare results for export
            export_results = [{
                "title": r.title,
                "link": r.link,
                "description": r.description,
                "summary": r.summary
            } for r in results]
            
            # Try to export to Notion
            try:
                # Check for environment variables first
                if os.environ.get("NOTION_INTEGRATION_SECRET") and notion_token == "[ENV]":
                    notion_token = os.environ.get("NOTION_INTEGRATION_SECRET")
                
                if os.environ.get("NOTION_DATABASE_ID") and database_id == "[ENV]":
                    database_id = os.environ.get("NOTION_DATABASE_ID")
                    
                # Check we have valid values
                if not notion_token or not database_id:
                    flash("Missing Notion API token or database ID.", "danger")
                    return render_template("notion_export.html", search_id=search_id)
                
                # Perform the export
                result = export_to_notion(search.query_text, export_results, notion_token, database_id)
                
                if result and result.get("success"):
                    flash(f"Successfully exported to Notion: {result.get('message')}", "success")
                    return redirect(url_for("view_search", search_id=search_id))
                else:
                    flash("Error exporting to Notion. Please check your API token and database ID.", "danger")
                    return render_template("notion_export.html", search_id=search_id)
                    
            except Exception as e:
                logging.error(f"Error exporting to Notion: {str(e)}")
                flash(f"Error exporting to Notion: {str(e)}", "danger")
                return render_template("notion_export.html", search_id=search_id)
        
        # Show form for GET requests
        return render_template("notion_export.html", search_id=search_id)
        
    except Exception as e:
        logging.error(f"Error with Notion export: {str(e)}")
        flash("An error occurred. Please try again later.", "danger")
        return redirect(url_for("history"))

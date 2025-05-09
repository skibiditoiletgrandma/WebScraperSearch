from datetime import datetime
from app import db, login_manager
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    """Model for user accounts"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    remember_token = Column(String(128), unique=True, index=True)
    search_count_today = Column(Integer, default=0)  # Number of searches used today
    search_count_reset_date = Column(DateTime, default=datetime.utcnow)  # When the daily search count was last reset
    # General settings
    search_pages_limit = Column(Integer, default=1)  # Number of Google search pages to fetch
    hide_wikipedia = Column(Boolean, default=False)  # Option to hide Wikipedia results
    show_feedback_features = Column(Boolean, default=False)  # Option to show feedback/rating features
    enable_suggestions = Column(Boolean, default=True)  # Option to enable/disable search query suggestions

    # Summary settings
    generate_summaries = Column(Boolean, default=True)  # Option to enable/disable summary generation
    summary_depth = Column(Integer, default=3)  # Depth of summary (1-5 scale)
    summary_complexity = Column(Integer, default=3)  # Complexity of summary (1-5 scale)

    def __init__(self, **kwargs):
        # Set default values for search count fields to ensure they're never None
        self.search_count_today = 0
        self.search_count_reset_date = datetime.utcnow()

        # Set other attributes from kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(str(self.password_hash), password)

    def __repr__(self):
        return f'<User {self.username}>'

    def check_search_limit(self):
        """Check if user has reached their daily search limit"""
        # Admin users are limited to 0 searches
        if self.is_admin:
            return False

        # Ensure we have valid values for the search count fields
        if self.search_count_today is None:
            self.search_count_today = 0

        if self.search_count_reset_date is None:
            self.search_count_reset_date = datetime.utcnow()

        # Check if we need to reset the daily counter (new day)
        current_date = datetime.utcnow().date()
        reset_date = self.search_count_reset_date.date() if self.search_count_reset_date else current_date

        if current_date > reset_date:
            # It's a new day, reset the counter
            self.search_count_today = 0
            self.search_count_reset_date = datetime.utcnow()
            return True  # User can search

        # Convert to int to be safe
        search_count = int(self.search_count_today) if self.search_count_today is not None else 0

        # Return True if user has searches remaining, False if limit reached
        return search_count < 15  # Daily limit is 15 searches

    def increment_search_count(self):
        """Increment the user's search count for today"""
        # First make sure the daily counter is current
        self.check_search_limit()

        # Ensure we have a valid search count
        if self.search_count_today is None:
            self.search_count_today = 0

        # Increment counter
        try:
            self.search_count_today = int(self.search_count_today) + 1
        except (ValueError, TypeError):
            # If there was a conversion error, reset counter to 1
            self.search_count_today = 1

        return self.search_count_today

    def remaining_searches(self):
        """Return the number of searches remaining for the user today"""
        # This will ensure all fields are properly set and the counter is current
        self.check_search_limit()

        # Get the current search count as a Python int
        try:
            current_count = int(self.search_count_today) if self.search_count_today is not None else 0
        except (ValueError, TypeError):
            # Handle any conversion errors by defaulting to 0
            current_count = 0

        # Calculate remaining searches
        remaining = 15 - current_count
        return max(0, remaining)  # Ensure we never return a negative number

class SearchQuery(db.Model):
    """Model for storing search queries"""
    __tablename__ = 'search_query'

    id = Column(Integer, primary_key=True)
    query_text = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45))  # IPv6 addresses can be up to 45 chars
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # Can be null for anonymous searches
    is_public = Column(Boolean, default=True)  # Whether this search is visible to other users

    # Relationships
    results = relationship('SearchResult', backref='search_query', lazy=True, cascade="all, delete-orphan")
    user = relationship('User', backref='searches', lazy=True)

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return f"<SearchQuery {self.query_text}>"

class SearchResult(db.Model):
    """Model for storing search results"""
    __tablename__ = 'search_result'

    id = Column(Integer, primary_key=True)
    search_query_id = Column(Integer, ForeignKey('search_query.id'), nullable=False)
    title = Column(String(255), nullable=False)
    link = Column(String(2048), nullable=False)  # URLs can be long
    description = Column(Text)
    summary = Column(Text)
    rank = Column(Integer)  # Position in search results
    timestamp = Column(DateTime, default=datetime.utcnow)
    share_count = Column(Integer, default=0)  # Track number of times shared
    last_shared = Column(DateTime)  # Last time this summary was shared
    shared_by = Column(String(64))  # Username of user who shared it (if applicable)

    # Relationship to feedback
    feedback = relationship('SummaryFeedback', backref='search_result', lazy=True, cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def increment_share_count(self, username=None):
        """Increment the share count and update last_shared timestamp"""
        # Ensure we have a valid share count
        if self.share_count is None:
            self.share_count = 0

        # Convert to integer safely
        try:
            current_count = int(self.share_count)
        except (ValueError, TypeError):
            current_count = 0

        # Increment the counter
        self.share_count = current_count + 1

        # Update timestamp and username
        self.last_shared = datetime.utcnow()
        if username:
            self.shared_by = username

    def __repr__(self):
        title_value = self.title
        if isinstance(title_value, str):
            return f"<SearchResult {title_value[:30]}...>"
        return f"<SearchResult [No Title]>"

class SummaryFeedback(db.Model):
    """Model for storing user feedback on summaries"""
    __tablename__ = 'summary_feedback'

    id = Column(Integer, primary_key=True)
    search_result_id = Column(Integer, ForeignKey('search_result.id'), nullable=False)
    rating = Column(Integer)  # Rating from 1 to 5 stars
    comment = Column(Text)  # Optional comment from user
    helpful = Column(Boolean, default=False)  # Was the summary helpful?
    accurate = Column(Boolean, default=False)  # Was the summary accurate?
    complete = Column(Boolean, default=False)  # Was the summary complete?
    ip_address = Column(String(45))  # To prevent duplicate ratings
    timestamp = Column(DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return f"<SummaryFeedback id={self.id} rating={self.rating}>"

class AnonymousSearchLimit(db.Model):
    """Model for tracking anonymous user search limits via session IDs"""
    __tablename__ = 'anonymous_search_limit'

    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    search_count = Column(Integer, default=0)  # Number of searches used by this anonymous session
    first_search_date = Column(DateTime, default=datetime.utcnow)
    last_search_date = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45))  # To help identify patterns or abuse

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return f"<AnonymousSearchLimit session_id={self.session_id} count={self.search_count}>"

    def increment_search_count(self):
        """Increment the search count for this anonymous session"""
        # Ensure we have valid search count
        if self.search_count is None:
            self.search_count = 0

        # Increment counter
        try:
            self.search_count = int(self.search_count) + 1
        except (ValueError, TypeError):
            # If there was a conversion error, reset counter to 1
            self.search_count = 1

        # Update last search date
        self.last_search_date = datetime.utcnow()

        return self.search_count

    def check_search_limit(self):
        """Check if anonymous user has reached their total search limit (3)"""
        # Ensure we have valid search count
        if self.search_count is None:
            self.search_count = 0

        # Get the current count as a Python int
        try:
            current_count = int(self.search_count)
        except (ValueError, TypeError):
            current_count = 0

        # Anonymous users have a lifetime limit of 3 searches
        return current_count < 3

    def remaining_searches(self):
        """Return the number of searches remaining for anonymous users"""
        # Ensure we have valid search count
        if self.search_count is None:
            self.search_count = 0

        # Get the current count as a Python int
        try:
            current_count = int(self.search_count)
        except (ValueError, TypeError):
            current_count = 0

        # Calculate remaining searches
        remaining = 3 - current_count
        return max(0, remaining)  # Ensure we never return a negative number


class Citation(db.Model):
    """Model for storing generated citations"""
    __tablename__ = 'citations'

    id = Column(Integer, primary_key=True)

    # Citation metadata
    title = Column(String(255), nullable=False)
    authors = Column(String(512), nullable=False)  # Semicolon-separated author names
    source_type = Column(String(50), nullable=False)  # book, journal, website, etc.
    citation_style = Column(String(20), nullable=False)  # APA, MLA, Chicago, etc.

    # Source-specific fields
    publisher = Column(String(255))
    publication_date = Column(String(50))  # Store as string for flexibility
    journal_name = Column(String(255))
    volume = Column(String(50))
    issue = Column(String(50))
    pages = Column(String(50))
    url = Column(String(1024))
    access_date = Column(String(50))
    doi = Column(String(100))

    # User relation (optional - for saving citations)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    user = relationship('User', backref='citations', lazy=True)

    # Generation metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super(Citation, self).__init__(**kwargs)

    def generate_apa_citation(self):
        """Generate APA style citation"""
        if self.source_type == 'journal':
            author_list = self.format_authors_apa()
            citation = f"{author_list} ({self.publication_date}). {self.title}. "
            if self.journal_name:
                citation += f"<em>{self.journal_name}</em>"
                if self.volume:
                    citation += f", {self.volume}"
                    if self.issue:
                        citation += f"({self.issue})"
                if self.pages:
                    citation += f", {self.pages}"
            if self.doi:
                citation += f". https://doi.org/{self.doi}"
            elif self.url:
                citation += f". Retrieved from {self.url}"
            return citation

        elif self.source_type == 'book':
            author_list = self.format_authors_apa()
            citation = f"{author_list} ({self.publication_date}). <em>{self.title}</em>. "
            if self.publisher:
                citation += f"{self.publisher}."
            return citation

        elif self.source_type == 'website':
            author_list = self.format_authors_apa()
            citation = f"{author_list} ({self.publication_date}). {self.title}. "
            if self.url:
                citation += f"Retrieved from {self.url}"
            return citation

        # Default format if source type is not recognized
        return f"{self.authors} ({self.publication_date}). {self.title}."

    def generate_mla_citation(self):
        """Generate MLA style citation"""
        if self.source_type == 'journal':
            author_list = self.format_authors_mla()
            citation = f"{author_list}. \"{self.title}.\" "
            if self.journal_name:
                citation += f"<em>{self.journal_name}</em>"
                if self.volume:
                    citation += f", vol. {self.volume}"
                    if self.issue:
                        citation += f", no. {self.issue}"
                if self.publication_date:
                    citation += f", {self.publication_date}"
                if self.pages:
                    citation += f", pp. {self.pages}"
            if self.doi:
                citation += f". DOI: {self.doi}"
            elif self.url:
                citation += f". {self.url}"
                if self.access_date:
                    citation += f". Accessed {self.access_date}"
            return citation

        elif self.source_type == 'book':
            author_list = self.format_authors_mla()
            citation = f"{author_list}. <em>{self.title}</em>. "
            if self.publisher:
                citation += f"{self.publisher}"
                if self.publication_date:
                    citation += f", {self.publication_date}"
            citation += "."
            return citation

        elif self.source_type == 'website':
            author_list = self.format_authors_mla()
            citation = f"{author_list}. \"{self.title}.\" "
            if self.url:
                citation += f"{self.url}"
                if self.access_date:
                    citation += f". Accessed {self.access_date}"
            citation += "."
            return citation

        # Default format if source type is not recognized
        return f"{self.authors}. \"{self.title}.\" {self.publication_date}."

    def generate_chicago_citation(self):
        """Generate Chicago style citation"""
        if self.source_type == 'journal':
            author_list = self.format_authors_chicago()
            citation = f"{author_list}. \"{self.title}.\" "
            if self.journal_name:
                citation += f"<em>{self.journal_name}</em>"
                if self.volume:
                    citation += f" {self.volume}"
                    if self.issue:
                        citation += f", no. {self.issue}"
                if self.publication_date:
                    citation += f" ({self.publication_date})"
                if self.pages:
                    citation += f": {self.pages}"
            citation += "."
            if self.doi:
                citation += f" https://doi.org/{self.doi}."
            elif self.url:
                citation += f" {self.url}."
            return citation

        elif self.source_type == 'book':
            author_list = self.format_authors_chicago()
            citation = f"{author_list}. <em>{self.title}</em>. "
            if self.publisher:
                citation += f"{self.publisher}"
                if self.publication_date:
                    citation += f", {self.publication_date}"
            citation += "."
            return citation

        elif self.source_type == 'website':
            author_list = self.format_authors_chicago()
            citation = f"{author_list}. \"{self.title}.\" "
            if self.publication_date:
                citation += f"{self.publication_date}. "
            if self.url:
                citation += f"{self.url}"
                if self.access_date:
                    citation += f" (accessed {self.access_date})"
            citation += "."
            return citation

        # Default format if source type is not recognized
        return f"{self.authors}. \"{self.title}.\" {self.publication_date}."

    def format_authors_apa(self):
        """Format author names for APA style"""
        if not self.authors:
            return ""

        author_list = self.authors.split(";")
        if len(author_list) == 1:
            # Single author: Last, F. M.
            return self._format_author_apa(author_list[0])
        elif len(author_list) == 2:
            # Two authors: Last, F. M., & Last, F. M.
            return f"{self._format_author_apa(author_list[0])}, & {self._format_author_apa(author_list[1])}"
        else:
            # Multiple authors: Last, F. M., Last, F. M., & Last, F. M.
            formatted_authors = ", ".join([self._format_author_apa(a) for a in author_list[:-1]])
            return f"{formatted_authors}, & {self._format_author_apa(author_list[-1])}"

    def _format_author_apa(self, author):
        """Helper to format a single author name for APA"""
        parts = author.strip().split()
        if len(parts) == 1:
            return parts[0]
        elif len(parts) == 2:
            last_name, first_name = parts[1], parts[0]
            return f"{last_name}, {first_name[0]}."
        else:
            # Assume first name, middle name, last name format
            first_name, middle_name, last_name = parts[0], parts[1], parts[2]
            return f"{last_name}, {first_name[0]}. {middle_name[0]}."

    def format_authors_mla(self):
        """Format author names for MLA style"""
        if not self.authors:
            return ""

        author_list = self.authors.split(";")
        if len(author_list) == 1:
            # Single author: Last, First
            return self._format_author_mla(author_list[0])
        elif len(author_list) == 2:
            # Two authors: Last, First, and First Last
            first_author = self._format_author_mla(author_list[0])
            parts = author_list[1].strip().split()
            if len(parts) == 1:
                second_author = parts[0]
            else:
                first_name = parts[0]
                last_name = " ".join(parts[1:])
                second_author = f"{first_name} {last_name}"
            return f"{first_author}, and {second_author}"
        else:
            # More than two authors: Last, First, et al.
            return f"{self._format_author_mla(author_list[0])}, et al."

    def _format_author_mla(self, author):
        """Helper to format a single author name for MLA"""
        parts = author.strip().split()
        if len(parts) == 1:
            return parts[0]
        elif len(parts) == 2:
            first_name, last_name = parts[0], parts[1]
            return f"{last_name}, {first_name}"
        else:
            # Assume first name, middle name, last name format
            first_name, middle_name, last_name = parts[0], parts[1], parts[2]
            return f"{last_name}, {first_name} {middle_name}"

    def format_authors_chicago(self):
        """Format author names for Chicago style"""
        if not self.authors:
            return ""

        author_list = self.authors.split(";")
        if len(author_list) == 1:
            # Single author: Last, First
            return self._format_author_chicago(author_list[0])
        elif len(author_list) <= 3:
            # Up to three authors: Last, First, First Last, and First Last
            formatted_authors = self._format_author_chicago(author_list[0])
            for i in range(1, len(author_list)-1):
                formatted_authors += f", {self._format_author_name_chicago(author_list[i])}"
            formatted_authors += f", and {self._format_author_name_chicago(author_list[-1])}"
            return formatted_authors
        else:
            # More than three authors: First author et al.
            return f"{self._format_author_chicago(author_list[0])} et al."

    def _format_author_chicago(self, author):
        """Helper to format first author name for Chicago"""
        parts = author.strip().split()
        if len(parts) == 1:
            return parts[0]
        elif len(parts) == 2:
            first_name, last_name = parts[0], parts[1]
            return f"{last_name}, {first_name}"
        else:
            # Assume first name, middle name, last name format
            first_name, middle_name, last_name = parts[0], parts[1], parts[2]
            return f"{last_name}, {first_name} {middle_name}"

    def _format_author_name_chicago(self, author):
        """Helper to format non-first author name for Chicago"""
        parts = author.strip().split()
        if len(parts) == 1:
            return parts[0]
        elif len(parts) == 2:
            first_name, last_name = parts[0], parts[1]
            return f"{first_name} {last_name}"
        else:
            # Assume first name, middle name, last name format
            first_name, middle_name, last_name = parts[0], parts[1], parts[2]
            return f"{first_name} {middle_name} {last_name}"

    def get_formatted_citation(self):
        """Return the citation formatted according to the selected style"""
        if self.citation_style == "APA":
            return self.generate_apa_citation()
        elif self.citation_style == "MLA":
            return self.generate_mla_citation()
        elif self.citation_style == "Chicago":
            return self.generate_chicago_citation()
        else:
            # Default to APA if style not recognized
            return self.generate_apa_citation()

    def __repr__(self):
        return f"<Citation {self.id}: {self.title}>"

class CookieSearchLimit(db.Model):
    """Model for tracking cookie-based search limits"""
    __tablename__ = 'cookie_search_limits'

    id = Column(Integer, primary_key=True)
    cookie_id = Column(String(64), unique=True, nullable=False, index=True)
    search_count_today = Column(Integer, default=0)
    last_reset_date = Column(DateTime, default=datetime.utcnow)

    def check_and_increment(self):
        """Check limit and increment if allowed"""
        current_date = datetime.utcnow().date()
        reset_date = self.last_reset_date.date() if self.last_reset_date else current_date

        # Reset counter if it's a new day
        if current_date > reset_date:
            self.search_count_today = 0
            self.last_reset_date = datetime.utcnow()

        # Check if under limit (15 searches per cookie per day)
        if self.search_count_today >= 15:
            return False

        self.search_count_today += 1
        return True
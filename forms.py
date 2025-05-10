from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField, DateField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, URL, Optional, NumberRange
from models import User

class LoginForm(FlaskForm):
    """Form for user login"""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Log In')

class RegistrationForm(FlaskForm):
    """Form for user registration"""
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=64, message='Username must be between 3 and 64 characters long.')
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email(),
        Length(max=120)
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long.')
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        """Check if username is already taken"""
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Username already taken. Please use a different username.')
    
    def validate_email(self, email):
        """Check if email is already registered"""
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Email already registered. Please use a different email address or login.')


class CitationForm(FlaskForm):
    """Form for generating citations"""
    # Common fields for all citation types
    title = StringField('Title', validators=[DataRequired(), Length(max=255)])
    authors = TextAreaField('Authors (one per line)', validators=[DataRequired()])
    source_type = SelectField('Source Type', 
        choices=[
            ('book', 'Book'), 
            ('journal', 'Journal Article'), 
            ('website', 'Website')
        ],
        validators=[DataRequired()]
    )
    citation_style = SelectField('Citation Style', 
        choices=[
            ('APA', 'APA (7th Edition)'), 
            ('MLA', 'MLA (9th Edition)'), 
            ('Chicago', 'Chicago (17th Edition)')
        ],
        validators=[DataRequired()]
    )
    
    # Book-specific fields
    publisher = StringField('Publisher', validators=[Optional(), Length(max=255)])
    publication_date = StringField('Publication Date (Year or YYYY-MM-DD)', validators=[Optional(), Length(max=50)])
    
    # Journal-specific fields
    journal_name = StringField('Journal Name', validators=[Optional(), Length(max=255)])
    volume = StringField('Volume', validators=[Optional(), Length(max=50)])
    issue = StringField('Issue', validators=[Optional(), Length(max=50)])
    pages = StringField('Pages (e.g., 125-148)', validators=[Optional(), Length(max=50)])
    doi = StringField('DOI', validators=[Optional(), Length(max=100)])
    
    # Website-specific fields
    url = StringField('URL', validators=[Optional(), URL(), Length(max=1024)])
    access_date = StringField('Access Date (YYYY-MM-DD)', validators=[Optional(), Length(max=50)])
    
    submit = SubmitField('Generate Citation')
    
class SettingsForm(FlaskForm):
    """Form for user settings"""
    # General settings
    
    search_pages_limit = IntegerField('Google Search Pages Limit', validators=[
        DataRequired(),
        NumberRange(min=1, max=10, message='Please select a value between 1 and 10 pages.')
    ], description='Number of Google search results pages to fetch per search (1-10)')

    hide_wikipedia = BooleanField('Hide Wikipedia Results', 
        description='When enabled, results from Wikipedia will be hidden from search results')
    
    show_feedback_features = BooleanField('Show Feedback/Rating Features', 
        description='When enabled, feedback and rating options will be shown in search results')
        
    enable_suggestions = BooleanField('Enable Search Suggestions', 
        description='When enabled, AI-powered suggestions for better search queries will be shown')
    
    # Summary settings
    generate_summaries = BooleanField('Generate Summaries', 
        description='When enabled, AI-powered summaries will be generated for search results')
    
    summary_depth = IntegerField('Summary Depth', validators=[
        NumberRange(min=1, max=5, message='Please select a value between 1 and 5.')
    ], description='Depth of generated summaries (1=very concise, 3=normal, 5=comprehensive & detailed): Controls how much information is included in the summary')
    
    summary_complexity = IntegerField('Summary Complexity', validators=[
        NumberRange(min=1, max=5, message='Please select a value between 1 and 5.')
    ], description='Complexity level of generated summaries (1=simple short sentences, 3=balanced, 5=advanced vocabulary & longer sentences): Controls the sentence structure and language difficulty')
    
    submit = SubmitField('Save Settings')
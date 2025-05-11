"""
Personalized Search Recommendation System
This module provides a comprehensive recommendation system for search queries:
1. Personalized recommendations based on user search history
2. Topic-based suggestions to explore related areas of interest
3. Advanced query formulation using NLP and semantic analysis
4. Trending topics and popular searches from community data
"""

import random
import re
from collections import Counter
from typing import List, Dict, Tuple

import nltk
from nltk.corpus import wordnet
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.tag import pos_tag

# Download necessary NLTK data
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

# Download required NLTK data
for package in ['punkt', 'wordnet', 'stopwords', 'averaged_perceptron_tagger', 'maxent_ne_chunker', 'words']:
    try:
        nltk.data.find(f'tokenizers/{package}')
    except LookupError:
        nltk.download(package, quiet=True)

# Load English stopwords
STOPWORDS = set(stopwords.words('english'))

# Common search operators and patterns
SEARCH_OPERATORS = {
    'site:': 'Search within a specific website (e.g., "site:example.com")',
    'filetype:': 'Search for specific file types (e.g., "filetype:pdf")',
    'intitle:': 'Search for pages with specific words in the title',
    'inurl:': 'Search for pages with specific words in the URL',
    'related:': 'Find websites related to a specified domain',
    'OR': 'Search for either one term or another (e.g., "cats OR dogs")',
    '"': 'Exact match (e.g., "exact phrase")',
    '-': 'Exclude terms (e.g., "cats -dogs")'
}

# Common search categories and example queries
SEARCH_CATEGORIES = {
    'how to': ['how to make', 'how to create', 'how to find', 'how to solve', 'how to build'],
    'what is': ['what is a', 'what is the definition of', 'what is the meaning of', 'what is the purpose of'],
    'best': ['best ways to', 'best tools for', 'best practices for', 'best examples of', 'best alternatives to'],
    'comparison': ['vs', 'versus', 'compared to', 'differences between', 'pros and cons of'],
    'reviews': ['review of', 'top rated', 'user reviews', 'pros and cons', 'ratings for'],
    'tutorial': ['tutorial on', 'guide to', 'step by step', 'learn', 'examples of'],
    'problems': ['fix', 'solve', 'troubleshoot', 'repair', 'issues with', 'solutions for'],
    'news': ['latest', 'recent', 'update on', 'breaking news', 'developments in'],
}


def clean_and_tokenize(query: str) -> List[str]:
    """
    Cleans a query and returns tokenized words (excluding stopwords)
    
    Args:
        query (str): The search query
        
    Returns:
        List[str]: List of meaningful tokenized words
    """
    # Convert to lowercase and remove non-alphanumeric characters
    query = re.sub(r'[^\w\s]', ' ', query.lower())
    
    # Tokenize and remove stopwords
    tokens = word_tokenize(query)
    return [word for word in tokens if word not in STOPWORDS and len(word) > 1]


def get_synonyms(word: str) -> List[str]:
    """
    Get synonyms for a word using WordNet
    
    Args:
        word (str): The word to find synonyms for
        
    Returns:
        List[str]: List of synonym words
    """
    synonyms = []
    for syn in wordnet.synsets(word):
        if syn and hasattr(syn, 'lemmas'):
            for lemma in syn.lemmas():
                if lemma and hasattr(lemma, 'name'):
                    synonym = lemma.name().replace('_', ' ')
                    if synonym not in synonyms and synonym != word:
                        synonyms.append(synonym)
    
    # Return up to 5 synonyms
    return synonyms[:5]


def get_related_terms(query: str) -> List[str]:
    """
    Identify related terms for query expansion
    
    Args:
        query (str): The original query
        
    Returns:
        List[str]: List of related terms
    """
    # Tokenize and get parts of speech
    tokens = clean_and_tokenize(query)
    tagged = pos_tag(tokens)
    
    # Extract nouns and verbs as they're most important for search
    key_terms = [word for word, tag in tagged if tag.startswith('NN') or tag.startswith('VB')]
    
    # Get related terms for these key terms
    related_terms = []
    for term in key_terms:
        synonyms = get_synonyms(term)
        related_terms.extend(synonyms)
    
    return related_terms[:8]  # Limit to 8 related terms


def identify_query_category(query: str) -> str:
    """
    Identify which search category the query most likely belongs to
    
    Args:
        query (str): The search query
        
    Returns:
        str: The identified category or empty string
    """
    query_lower = query.lower()
    
    for category, patterns in SEARCH_CATEGORIES.items():
        for pattern in patterns:
            if pattern in query_lower:
                return category
    
    return ""  # Return empty string instead of None


def suggest_query_improvements(query: str, past_queries: List[str] = []) -> Dict[str, List[str]]:
    """
    Suggest improvements for a search query
    
    Args:
        query (str): The original search query
        past_queries (List[str]): List of past successful queries from database
        
    Returns:
        Dict[str, List[str]]: Dictionary of suggestion categories and lists of suggested queries
    """
    if not query or len(query.strip()) == 0:
        return {
            "improved_queries": [],
            "expanded_queries": [],
            "operator_suggestions": []
        }
    
    # Initialize results
    results = {
        "improved_queries": [],
        "expanded_queries": [],
        "operator_suggestions": []
    }
    
    # Clean and tokenize the query
    tokens = clean_and_tokenize(query)
    if not tokens:
        return results
    
    # 1. Generate improved queries
    # Identify query category to give structure
    category = identify_query_category(query)
    
    if category:
        # Use category patterns to suggest better structured queries
        for pattern in SEARCH_CATEGORIES[category][:2]:  # Use top 2 patterns
            if pattern not in query.lower():
                # Avoid duplication if pattern is already in the query
                suggested_query = f"{pattern} {query}"
                results["improved_queries"].append(suggested_query)
    
    # 2. Add related terms for query expansion
    related_terms = get_related_terms(query)
    for term in related_terms:
        expanded_query = f"{query} {term}"
        results["expanded_queries"].append(expanded_query)
    
    # 3. Suggest search operators based on query content
    # Look for potential use cases for operators
    if len(tokens) >= 2 and "OR" not in query:
        # Suggest OR for potential comparisons
        results["operator_suggestions"].append(f"{tokens[0]} OR {tokens[1]}")
    
    # Check for domain names in the query
    domain_match = re.search(r'(\w+\.\w+)', query)
    if domain_match:
        # Suggest site: operator for domain-specific search
        domain = domain_match.group(1)
        results["operator_suggestions"].append(f"site:{domain} {query.replace(domain, '')}")
    
    # Suggest quotes for exact matching if query has 3+ words
    if len(tokens) >= 3 and '"' not in query:
        results["operator_suggestions"].append(f'"{query}"')
    
    # Use past successful queries if available
    if past_queries:
        # Find past queries with some overlap with current tokens
        for past_query in past_queries:
            past_tokens = clean_and_tokenize(past_query)
            # Check for term overlap but not exact match
            if set(tokens).intersection(set(past_tokens)) and query.lower() != past_query.lower():
                results["improved_queries"].append(past_query)
    
    # Deduplicate and limit results
    for key in results:
        results[key] = list(set(results[key]))[:5]  # Limit to top 5 suggestions per category
    
    return results


def get_personal_search_history(db, user_id=None, limit=5):
    """
    Get personalized search history for a specific user or general trending searches
    
    Args:
        db: Database connection
        user_id: Specific user ID to fetch history for (None for global trending)
        limit: Maximum number of history items to return
        
    Returns:
        List[Dict]: List of search history items with metadata
    """
    if not db:
        return []
        
    try:
        from models import SearchQuery, User
        from datetime import datetime, timedelta
        
        # Base query
        query = db.session.query(SearchQuery)
        
        # If user_id provided, filter by user
        if user_id:
            query = query.filter(SearchQuery.user_id == user_id)
            
            # Get user's 5 most recent searches
            recent_searches = query.order_by(
                SearchQuery.created_at.desc()
            ).limit(limit).all()
            
            return [{
                "query": search.query_text,
                "description": f"Searched on {search.created_at.strftime('%b %d')}",
                "type": "history",
                "icon": "fa-history"
            } for search in recent_searches if search.query_text]
        else:
            # Get trending searches from last 7 days
            one_week_ago = datetime.now() - timedelta(days=7)
            trending = query.filter(SearchQuery.created_at >= one_week_ago).all()
            
            # Count frequency of each search query
            query_counts = Counter([search.query_text for search in trending if search.query_text])
            
            # Get top trending searches
            top_trending = query_counts.most_common(limit)
            
            return [{
                "query": query_text,
                "description": f"Trending search ({count} searches)",
                "type": "trending",
                "icon": "fa-fire"
            } for query_text, count in top_trending]
            
    except Exception as e:
        print(f"Error accessing search history: {e}")
        return []


def get_topic_suggestions(query: str) -> List[Dict]:
    """
    Generate topic-based suggestions related to the current query
    
    Args:
        query (str): The current search query
        
    Returns:
        List[Dict]: List of topic suggestions
    """
    # Identify the query category
    category = identify_query_category(query)
    if not category:
        return []
        
    # Get related patterns from the category
    topic_suggestions = []
    patterns = SEARCH_CATEGORIES.get(category, [])
    
    tokens = clean_and_tokenize(query)
    if not tokens:
        return []
    
    # Use the most important term from the query
    main_term = tokens[0] if tokens else ""
    
    # Create topic suggestions using the patterns
    for pattern in patterns[:3]:
        # Avoid suggesting the exact same query
        suggested_query = f"{pattern} {main_term}"
        if suggested_query.lower() != query.lower():
            topic_suggestions.append({
                "query": suggested_query,
                "description": f"Related {category} topic",
                "type": "topic",
                "icon": "fa-tag"
            })
    
    return topic_suggestions


def get_suggestions_for_ui(query: str, db=None, user_id=None) -> List[Dict]:
    """
    Format suggestions for the UI display with helpful descriptions organized by sections
    
    Args:
        query (str): The original search query
        db: Database connection for fetching past successful queries
        user_id: Current user ID for personalized suggestions
        
    Returns:
        List[Dict]: Comprehensive suggestion data organized by sections
    """
    if not query or len(query.strip()) < 2:
        # For empty/short queries, only return personalized and trending suggestions
        personal_history = get_personal_search_history(db, user_id, limit=3)
        trending_searches = get_personal_search_history(db, user_id=None, limit=3)
        
        recommendations = {
            "personalized": personal_history,
            "trending": trending_searches,
            "query_improvements": [],
            "related_topics": []
        }
        
        # Flatten for backward compatibility with existing JavaScript
        flat_suggestions = []
        for section in recommendations.values():
            flat_suggestions.extend(section)
            
        return flat_suggestions[:8]
    
    # Get past successful queries from database if available
    past_queries = []
    if db:
        try:
            # Assuming a model with past successful queries exists
            from models import SearchQuery
            # Get most recent 50 searches to analyze
            recent_searches = db.session.query(SearchQuery).order_by(
                SearchQuery.id.desc()
            ).limit(50).all()
            
            # Extract query texts
            past_queries = [search.query_text for search in recent_searches if search.query_text]
        except Exception as e:
            print(f"Error accessing past queries: {e}")
    
    # Get raw suggestions
    suggestions_dict = suggest_query_improvements(query, past_queries)
    
    # Format for UI - organized by sections
    query_improvements = []
    
    # Add improved queries with descriptions
    for suggestion in suggestions_dict["improved_queries"]:
        query_improvements.append({
            "query": suggestion,
            "description": "Better structured search query",
            "type": "improved",
            "icon": "fa-lightbulb"
        })
    
    # Add expanded queries with descriptions
    for suggestion in suggestions_dict["expanded_queries"]:
        query_improvements.append({
            "query": suggestion,
            "description": "Expanded with related terms",
            "type": "expanded",
            "icon": "fa-plus-circle"
        })
    
    # Add operator suggestions with descriptions
    for suggestion in suggestions_dict["operator_suggestions"]:
        # Identify which operator is being used
        operator_desc = "Advanced search technique"
        operator_icon = "fa-code"
        for op, desc in SEARCH_OPERATORS.items():
            if op in suggestion and op not in query:
                operator_desc = desc
                break
        
        query_improvements.append({
            "query": suggestion,
            "description": operator_desc,
            "type": "operator",
            "icon": operator_icon
        })
    
    # Get topic-based suggestions
    topic_suggestions = get_topic_suggestions(query)
    
    # Get personalized history
    personal_history = get_personal_search_history(db, user_id, limit=3)
    
    # Get trending searches
    trending_searches = get_personal_search_history(db, user_id=None, limit=3)
    
    # Organize all suggestions by category
    recommendations = {
        "personalized": [{
            "query": x["query"],
            "description": x["description"],
            "type": "history",
            "icon": "fa-history"
        } for x in personal_history],
        "trending": [{
            "query": x["query"],
            "description": x["description"],
            "type": "trending",
            "icon": "fa-fire"
        } for x in trending_searches],
        "improved": [{
            "query": x,
            "description": "Better structured search query",
            "type": "improved",
            "icon": "fa-lightbulb"
        } for x in query_improvements[:5]],
        "topic": [{
            "query": x["query"],
            "description": x["description"],
            "type": "topic",
            "icon": "fa-tag"
        } for x in topic_suggestions],
        "expanded": [{
            "query": x,
            "description": "Expanded search query",
            "type": "expanded",
            "icon": "fa-plus-circle"
        } for x in suggestions_dict.get("expanded_queries", [])[:3]],
        "operator": [{
            "query": x,
            "description": "Advanced search operator",
            "type": "operator",
            "icon": "fa-code"
        } for x in suggestions_dict.get("operator_suggestions", [])[:2]]
    }
    
    # Flatten for backward compatibility with existing JavaScript
    flat_suggestions = []
    for section in recommendations.values():
        flat_suggestions.extend(section)
    
    # Deduplicate by query text
    seen_queries = set()
    unique_suggestions = []
    for suggestion in flat_suggestions:
        if suggestion["query"].lower() not in seen_queries:
            seen_queries.add(suggestion["query"].lower())
            unique_suggestions.append(suggestion)
            
    return unique_suggestions[:12]  # Return up to 12 suggestions for sidebar
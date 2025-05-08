import re
import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist
from nltk.tokenize import word_tokenize
import logging

# Download required NLTK resources
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

def clean_text(text):
    """
    Clean text by removing special characters, multiple spaces, etc.
    
    Args:
        text (str): The input text to clean
        
    Returns:
        str: Cleaned text
    """
    # Remove URLs
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    
    # Remove HTML tags
    text = re.sub(r'<.*?>', '', text)
    
    # Remove multiple spaces and newlines
    text = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text

def summarize_text(text, title="", max_sentences=5, min_sentences=2):
    """
    Generate a summary of the provided text using extractive summarization
    
    Args:
        text (str): The text to summarize
        title (str): The title of the text (optional)
        max_sentences (int): Maximum number of sentences in the summary
        min_sentences (int): Minimum number of sentences in the summary
        
    Returns:
        str: The generated summary
    """
    if not text or text.strip() == "":
        return "No content to summarize."
    
    try:
        # Clean the text
        cleaned_text = clean_text(text)
        
        # If the text is too short, return it as is
        if len(cleaned_text.split()) < 50:
            return cleaned_text[:500] + "..."
        
        # Tokenize the text into sentences
        sentences = sent_tokenize(cleaned_text)
        
        # If very few sentences, just return them
        if len(sentences) <= min_sentences:
            return " ".join(sentences)
        
        # Get English stopwords
        stop_words = set(stopwords.words('english'))
        
        # Tokenize words and remove stopwords
        words = [word.lower() for word in word_tokenize(cleaned_text) 
                if word.lower() not in stop_words and word.isalnum()]
        
        # Calculate word frequencies
        freq = FreqDist(words)
        
        # Calculate sentence scores based on word frequencies
        sentence_scores = {}
        for i, sentence in enumerate(sentences):
            words_in_sentence = [word.lower() for word in word_tokenize(sentence) 
                               if word.lower() not in stop_words and word.isalnum()]
            
            # Give higher scores to the first few sentences
            position_score = 1.0 if i < 3 else 0.5
            
            # Calculate score based on word frequency
            score = sum(freq[word] for word in words_in_sentence) * position_score
            
            # Give higher scores to sentences containing words from the title
            if title:
                title_words = [word.lower() for word in word_tokenize(title) 
                             if word.lower() not in stop_words and word.isalnum()]
                title_match = sum(1 for word in words_in_sentence if word in title_words)
                score += title_match * 2
            
            sentence_scores[i] = score
        
        # Get top-scoring sentences
        num_sentences = min(max_sentences, max(min_sentences, len(sentences) // 5))
        top_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)[:num_sentences]
        
        # Sort sentences by their original position
        top_sentences = sorted(top_sentences, key=lambda x: x[0])
        
        # Generate the summary
        summary = " ".join(sentences[i] for i, _ in top_sentences)
        
        # If summary is too short, add more sentences
        if len(summary.split()) < 30 and len(sentences) > num_sentences:
            additional = min(len(sentences) - num_sentences, 2)
            more_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)[num_sentences:num_sentences+additional]
            more_sentences = sorted(more_sentences, key=lambda x: x[0])
            for i, _ in more_sentences:
                summary += " " + sentences[i]
        
        return summary
    
    except Exception as e:
        logging.error(f"Error generating summary: {str(e)}")
        # Return a truncated version of the text if summarization fails
        return text[:500] + "..." if len(text) > 500 else text

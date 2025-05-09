import re
import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist
from nltk.tokenize import word_tokenize
import logging

# Download required NLTK resources
# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

try:
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('averaged_perceptron_tagger')

# Initialize the sentence tokenizer more simply
from nltk.tokenize import PunktSentenceTokenizer
sent_tokenizer = PunktSentenceTokenizer()

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

def summarize_text(text, title="", max_sentences=5, min_sentences=2, depth=3, complexity=3):
    """
    Generate a summary of the provided text using extractive summarization
    
    Args:
        text (str): The text to summarize
        title (str): The title of the text (optional)
        max_sentences (int): Maximum number of sentences in the summary
        min_sentences (int): Minimum number of sentences in the summary
        depth (int): The depth of the summary (1-5 scale, where 5 is most detailed)
        complexity (int): The complexity level of the summary (1-5 scale, where 5 is most complex)
        
    Returns:
        str: The generated summary
    """
    # Download required NLTK data if not already present
    try:
        nltk.download('punkt')
        nltk.download('stopwords')
    except Exception as e:
        logging.error(f"Error downloading NLTK data: {str(e)}")
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
        
        # Adjust max_sentences based on depth setting (1-5)
        base_sentences = max_sentences
        depth_factor = (depth - 1) / 4  # Normalize to 0-1 range
        depth_adjusted_max = max(2, min(15, int(base_sentences + (base_sentences * depth_factor * 2))))
        
        # Get top-scoring sentences with depth consideration
        num_sentences = min(depth_adjusted_max, max(min_sentences, int(len(sentences) * (0.1 + depth_factor * 0.3))))
        top_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)[:num_sentences]
        
        # Sort sentences by their original position
        top_sentences = sorted(top_sentences, key=lambda x: x[0])
        
        # Generate the summary
        summary = " ".join(sentences[i] for i, _ in top_sentences)
        
        # Adjust for complexity (1-5)
        complexity_factor = (complexity - 1) / 4  # Normalize to 0-1 range
        
        if complexity_factor < 0.4:  # Lower complexity (1-2)
            # Keep shorter, simpler sentences
            sentence_weights = [(i, s, len(s.split())) for i, s in enumerate(sentences)]
            simple_sentences = sorted(sentence_weights, key=lambda x: (x[2] < 30, x[2]))  # Prefer shorter sentences
            selected_indices = [x[0] for x in simple_sentences[:num_sentences]]
            selected_indices.sort()  # Maintain original order
            summary = " ".join(sentences[i] for i in selected_indices)
            
        elif complexity_factor > 0.6:  # Higher complexity (4-5)
            # Include more context and longer sentences
            additional_sentences = int(num_sentences * complexity_factor)
            complex_sentences = sorted(sentence_scores.items(), 
                                    key=lambda x: (x[1], len(sentences[x[0]].split())), 
                                    reverse=True)[:num_sentences + additional_sentences]
            complex_sentences = sorted(complex_sentences, key=lambda x: x[0])
            summary = " ".join(sentences[i] for i, _ in complex_sentences)
            
        else:  # Medium complexity (3)
            summary = " ".join(sentences[i] for i, _ in top_sentences)
        
        # If summary is still too short, add more sentences regardless of complexity
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

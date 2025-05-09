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
        # Amplify the depth effect by using a squared depth factor
        depth_factor = ((depth - 1) / 4) ** 0.8  # Normalize to 0-1 range with stronger curve
        
        # More dramatic scaling based on depth
        if depth == 1:  # Very concise
            depth_multiplier = 0.5
        elif depth == 2:
            depth_multiplier = 1.0
        elif depth == 3:
            depth_multiplier = 2.0
        elif depth == 4:
            depth_multiplier = 3.5
        else:  # depth == 5, very detailed
            depth_multiplier = 5.0
            
        depth_adjusted_max = max(2, min(20, int(base_sentences * depth_multiplier)))
        
        # Get top-scoring sentences with depth consideration - stronger effect
        num_sentences = min(depth_adjusted_max, max(min_sentences, int(len(sentences) * (0.05 + depth_factor * 0.5))))
        
        # For highest depth (5), include even more sentences
        if depth == 5 and len(sentences) > 10:
            num_sentences = min(len(sentences) // 2, num_sentences * 2)
            
        top_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)[:num_sentences]
        
        # Sort sentences by their original position
        top_sentences = sorted(top_sentences, key=lambda x: x[0])
        
        # Generate the summary
        summary = " ".join(sentences[i] for i, _ in top_sentences)
        
        # Adjust for complexity (1-5) - Make the effect much stronger
        # More dramatic complexity effect
        if complexity == 1:  # Very simple
            # Keep only the shortest, simplest sentences
            sentence_weights = [(i, s, len(s.split())) for i, s in enumerate(sentences)]
            # Sort by sentence length, prioritizing sentences under 15 words
            simple_sentences = sorted(sentence_weights, key=lambda x: (x[2] > 15, x[2]))
            selected_indices = [x[0] for x in simple_sentences[:max(2, num_sentences)]]
            selected_indices.sort()  # Maintain original order
            summary = " ".join(sentences[i] for i in selected_indices)
            
        elif complexity == 2:  # Somewhat simple
            # Prefer shorter sentences but include some informative ones
            sentence_weights = [(i, s, len(s.split())) for i, s in enumerate(sentences)]
            # Balance between importance and simplicity
            simple_sentences = sorted(sentence_weights, key=lambda x: (x[2] > 25, sentence_scores.get(x[0], 0) * -1))
            selected_indices = [x[0] for x in simple_sentences[:num_sentences]]
            selected_indices.sort()  # Maintain original order
            summary = " ".join(sentences[i] for i in selected_indices)
            
        elif complexity == 3:  # Medium complexity
            # Use the standard approach
            summary = " ".join(sentences[i] for i, _ in top_sentences)
            
        elif complexity == 4:  # Somewhat complex
            # Include more context and prioritize longer, more informative sentences
            additional_sentences = num_sentences // 2
            # Prioritize sentences with more information and slightly longer length
            complex_sentences = sorted(sentence_scores.items(), 
                                    key=lambda x: (x[1] * (1 + 0.2 * min(1, len(sentences[x[0]].split()) / 30))), 
                                    reverse=True)[:num_sentences + additional_sentences]
            complex_sentences = sorted(complex_sentences, key=lambda x: x[0])
            summary = " ".join(sentences[i] for i, _ in complex_sentences)
            
        else:  # complexity == 5, Very complex
            # Include significantly more context and prioritize complex sentences
            additional_sentences = num_sentences
            # Find sentences with technical terms or complex structure
            sentence_complexity = {}
            for i, sentence in enumerate(sentences):
                words = word_tokenize(sentence)
                # Calculate complexity based on sentence length, word length, and presence of rare words
                avg_word_length = sum(len(word) for word in words) / max(1, len(words))
                unusual_words = sum(1 for word in words if len(word) > 7 and word.lower() not in stop_words)
                sentence_complexity[i] = (len(words) * 0.4) + (avg_word_length * 0.3) + (unusual_words * 3)
            
            # Combine complexity score with importance score for final ranking
            combined_scores = {i: (sentence_scores.get(i, 0) * 0.6) + (sentence_complexity.get(i, 0) * 0.4) 
                              for i in range(len(sentences))}
            
            complex_sentences = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
            complex_sentences = complex_sentences[:num_sentences + additional_sentences]
            complex_sentences = sorted(complex_sentences, key=lambda x: x[0])  # Restore original order
            summary = " ".join(sentences[i] for i, _ in complex_sentences)
        
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

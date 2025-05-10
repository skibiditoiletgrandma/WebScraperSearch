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
    # Add download of punkt_tab to fix error
    nltk.data.find('tokenizers/punkt_tab/english')
except LookupError:
    try:
        nltk.download('punkt_tab')
    except:
        # If this fails, we have a fallback approach
        pass

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
        nltk.download('punkt_tab')
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
        
        # Tokenize the text into sentences - with fallback mechanism
        try:
            sentences = sent_tokenize(cleaned_text)
        except Exception as nltk_error:
            logging.error(f"Error with NLTK tokenization: {str(nltk_error)}")
            # Fallback tokenization - split by periods, exclamation points, question marks
            sentences = re.split(r'(?<=[.!?])\s+', cleaned_text)
        
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
        
        # Dynamic depth scaling based on text length and depth setting
        text_length = len(sentences)
        base_coverage = {
            1: 0.1,  # 10% of content
            2: 0.2,  # 20% of content
            3: 0.3,  # 30% of content
            4: 0.45, # 45% of content
            5: 0.6   # 60% of content
        }
        
        # Calculate target sentence count with smooth scaling
        base_count = max(2, int(text_length * base_coverage[depth]))
        length_factor = min(1.0, text_length / 20)  # Normalize for very short texts
        depth_multiplier = 1 + (depth - 3) * 0.5 * length_factor
        
        # Apply progressive scaling for longer texts
        if text_length > 20:
            depth_multiplier *= 1 + math.log(text_length / 20, 10) * 0.2
            
        depth_adjusted_max = max(2, min(int(base_count * depth_multiplier), text_length))
        num_sentences = depth_adjusted_max
        
        # Fine-tune for extremes
        if depth == 1:
            num_sentences = min(num_sentences, 3)  # Enforce strict limit for very concise
        elif depth == 5 and text_length > 15:
            # Progressive increase for detailed summaries
            num_sentences = min(text_length - 2, int(num_sentences * 1.2))
            
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
            # Enhanced complexity analysis
            sentence_complexity = {}
            vocab_frequency = FreqDist(words)  # Use previously calculated word frequencies
            
            for i, sentence in enumerate(sentences):
                words = word_tokenize(sentence)
                words_filtered = [w.lower() for w in words if w.lower() not in stop_words]
                
                # Multiple complexity factors
                avg_word_length = sum(len(word) for word in words_filtered) / max(1, len(words_filtered))
                syllable_count = sum(len(re.findall(r'[aeiouy]+', word.lower())) for word in words_filtered)
                avg_syllables = syllable_count / max(1, len(words_filtered))
                unusual_words = sum(1 for word in words_filtered if len(word) > 7)
                rare_words = sum(1 for word in words_filtered if vocab_frequency[word.lower()] <= 2)
                
                # Weighted complexity score
                sentence_complexity[i] = (
                    (len(words) * 0.2) +           # Length factor
                    (avg_word_length * 0.3) +      # Word length
                    (avg_syllables * 0.2) +        # Syllable complexity
                    (unusual_words * 2.0) +        # Long words
                    (rare_words * 2.5)             # Rare/technical terms
                )
            
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

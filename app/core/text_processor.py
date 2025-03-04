#app/core/text_processor.py

import logging
from typing import List

# Set up logging
logger = logging.getLogger(__name__)

def process_text(text: str) -> str:
    """Process transcribed text to improve formatting with proper capitalization and punctuation."""
    if not text:
        return text
        
    sentences = []
    current_sentence = []
    
    # Split by spaces to process word by word
    words = text.split()
    
    for word in words:
        current_sentence.append(word)
        
        # Check if this word ends with a sentence-ending punctuation
        if word.endswith(('.', '!', '?')):
            # Join the current sentence and add to sentences list
            sentences.append(' '.join(current_sentence))
            current_sentence = []
    
    # Add any remaining words as a sentence
    if current_sentence:
        sentences.append(' '.join(current_sentence))
    
    # Process each sentence for capitalization
    processed_sentences = []
    for sentence in sentences:
        if sentence:
            # Capitalize the first letter of each sentence
            processed_sentence = sentence[0].upper() + sentence[1:] if len(sentence) > 1 else sentence.upper()
            processed_sentences.append(processed_sentence)
    
    # Join all processed sentences with spaces
    return ' '.join(processed_sentences) 
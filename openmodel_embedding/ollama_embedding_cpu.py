import json
import os
import numpy as np
from typing import List, Dict, Any
import spacy
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from textblob import TextBlob
from transformers import pipeline
import warnings

from __init__ import path
path()

# Suppress warnings
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'  # Disable GPU

try:
    import ollama
except ImportError:
    print("Ollama library not found. Please install it using: pip install ollama")
    ollama = None

class NLPProcessor:
    def __init__(self):
        print("Initializing NLP Processor (CPU-only mode)")
        self.nlp = spacy.load("en_core_web_sm")
        try:
            self.summarizer = pipeline("summarization", model="facebook/bart-base", device=-1)  # Force CPU
            print("Summarization model loaded successfully")
        except Exception as e:
            print(f"Error loading summarization model: {e}")
            self.summarizer = None
        print("NLP Processor initialized successfully")

    def generate_embedding(self, text: str, model: str = "nomic-embed-text") -> List[float]:
        if ollama is None:
            print("Ollama library not available. Returning empty embedding.")
            return []
        try:
            response = ollama.embeddings(model=model, prompt=text)
            return response['embedding']
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return []

    def perform_ner(self, text: str) -> List[tuple]:
        doc = self.nlp(text)
        return [(ent.text, ent.label_) for ent in doc.ents]

    def topic_modeling(self, texts: List[str], num_topics: int = 2, num_words: int = 5) -> List[str]:
        if len(texts) < 2:
            return ["Not enough documents for topic modeling"]
        
        vectorizer = CountVectorizer(max_df=1.0, min_df=1, stop_words='english')
        try:
            doc_term_matrix = vectorizer.fit_transform(texts)
        except ValueError:
            return ["Unable to perform topic modeling due to document similarity"]
        
        lda = LatentDirichletAllocation(n_components=num_topics, random_state=42)
        lda.fit(doc_term_matrix)
        words = vectorizer.get_feature_names_out()
        topics = []
        for topic_idx, topic in enumerate(lda.components_):
            top_words = [words[i] for i in topic.argsort()[:-num_words - 1:-1]]
            topics.append(f"Topic {topic_idx + 1}: {', '.join(top_words)}")
        return topics

    def perform_sentiment_analysis(self, text: str) -> Dict[str, float]:
        blob = TextBlob(text)
        sentiment = blob.sentiment
        return {
            'polarity': sentiment.polarity,
            'subjectivity': sentiment.subjectivity
        }

    def summarize_text(self, text: str, max_length: int = 130, min_length: int = 30) -> str:
        if not text.strip():
            return "Empty text provided for summarization"
        if self.summarizer is None:
            return self.fallback_summarization(text, max_length)
        try:
            input_length = len(text.split())
            if input_length < max_length:
                max_length = max(min_length, input_length - 1)  # Ensure max_length is at least 1 less than input_length
            min_length = min(min_length, max_length - 1)  # Ensure min_length is less than max_length
            
            summary = self.summarizer(text[:1024], max_length=max_length, min_length=min_length, do_sample=False)
            return summary[0]['summary_text']
        except Exception as e:
            print(f"Error in text summarization: {e}")
            return self.fallback_summarization(text, max_length)

    def fallback_summarization(self, text: str, max_length: int = 130) -> str:
        sentences = self.nlp(text).sents
        summary = ""
        for sent in sentences:
            if len(summary) + len(sent.text) > max_length:
                break
            summary += sent.text + " "
        return summary.strip()

    def extract_keywords(self, text: str, top_n: int = 5) -> List[str]:
        try:
            doc = self.nlp(text)
            keywords = [token.lemma_ for token in doc if token.pos_ in ['NOUN', 'ADJ', 'VERB'] and not token.is_stop]
            return sorted(set(keywords), key=keywords.count, reverse=True)[:top_n]
        except Exception as e:
            print(f"Error in keyword extraction: {e}")
            return []

    def extract_text_from_json(self, data: Dict[str, Any]) -> str:
        if isinstance(data, dict):
            if 'llm_response' in data and isinstance(data['llm_response'], dict):
                topic = data['llm_response'].get('topic', '')
                key_points = ' '.join(data['llm_response'].get('key_points', []))
                return f"{topic} {key_points}"
            elif 'cleaned_html' in data:
                return data['cleaned_html']
            else:
                return ' '.join(str(value) for value in data.values() if isinstance(value, (str, int, float)))
        elif isinstance(data, list):
            return ' '.join(self.extract_text_from_json(item) for item in data if isinstance(item, dict))
        else:
            return str(data)

    def process_file(self, file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            text = self.extract_text_from_json(data)
            if not text.strip():
                raise ValueError("Empty or invalid text content in file")
            
            return {
                'original_content': text[:1000],  # Truncate for brevity
                'entities': self.perform_ner(text),
                'topics': self.topic_modeling([text]),
                'embedding': self.generate_embedding(text),
                'sentiment': self.perform_sentiment_analysis(text),
                'summary': self.summarize_text(text, max_length=150, min_length=50),  # Customized values
                'keywords': self.extract_keywords(text)
            }
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
            return {'error': str(e)}

    def process_directory(self, input_dir: str, output_dir: str):
        os.makedirs(output_dir, exist_ok=True)

        for filename in os.listdir(input_dir):
            if filename.endswith('.json'):
                input_path = os.path.join(input_dir, filename)
                output_path = os.path.join(output_dir, f"processed_{filename}")

                try:
                    processed_data = self.process_file(input_path)

                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(processed_data, f, ensure_ascii=False, indent=4)

                    print(f"Processed data saved to {output_path}")
                except Exception as e:
                    print(f"Error processing {filename}: {str(e)}")

def main():
    input_dir = os.path.join('data', 'raw', 'llama')  # Directory containing your JSON files
    output_dir = os.path.join('data', 'processed')  # Directory to save processed data

    processor = NLPProcessor()
    processor.process_directory(input_dir, output_dir)

if __name__ == "__main__":
    main()
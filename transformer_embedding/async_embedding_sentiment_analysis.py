import json
import os
import spacy
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import numpy as np
from sentence_transformers import SentenceTransformer
from textblob import TextBlob
from keybert import KeyBERT
from transformers import pipeline
import torch

from __init__ import path
path()

class NLPProcessor:
    def __init__(self):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Using device: {self.device}")
        
        self.nlp = spacy.load("en_core_web_sm")
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2', device=self.device)
        self.key_bert = KeyBERT(model=self.sentence_model)
        self.summarizer = pipeline("summarization", model="facebook/bart-large-cnn", device=0 if self.device == 'cuda' else -1)

    # ... [rest of the methods remain unchanged] ...
    def perform_ner(self, text):
        doc = self.nlp(text)
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        return entities

    def topic_modeling(self, texts, num_topics=5, num_words=10):
        vectorizer = CountVectorizer(max_df=1.0, min_df=1, stop_words='english')
        try:
            doc_term_matrix = vectorizer.fit_transform(texts)
        except ValueError:
            vectorizer = CountVectorizer(max_df=1.0, min_df=1, stop_words='english', max_features=1000)
            doc_term_matrix = vectorizer.fit_transform(texts)
        
        n_features = doc_term_matrix.shape[1]
        num_topics = min(num_topics, n_features)
        
        lda = LatentDirichletAllocation(n_components=num_topics, random_state=42)
        lda.fit(doc_term_matrix)
        
        words = vectorizer.get_feature_names_out()
        topics = []
        for topic_idx, topic in enumerate(lda.components_):
            top_words = [words[i] for i in topic.argsort()[:-num_words - 1:-1]]
            topics.append(f"Topic {topic_idx + 1}: {', '.join(top_words)}")
        return topics

    def generate_embeddings(self, texts):
        return self.sentence_model.encode(texts, device=self.device).tolist()

    def perform_sentiment_analysis(self, text):
        blob = TextBlob(text)
        sentiment = blob.sentiment
        return {
            'polarity': sentiment.polarity,
            'subjectivity': sentiment.subjectivity
        }

    def summarize_text(self, text, max_length=130, min_length=30):
        max_chunk_length = 1024  # BART model's maximum input length
        chunks = [text[i:i+max_chunk_length] for i in range(0, len(text), max_chunk_length)]
        
        summaries = []
        for chunk in chunks:
            summary = self.summarizer(chunk, max_length=max_length, min_length=min_length, do_sample=False)
            summaries.append(summary[0]['summary_text'])
        
        return ' '.join(summaries)

    def extract_keywords(self, text, top_n=5):
        keywords = self.key_bert.extract_keywords(text, top_n=top_n)
        return [keyword for keyword, _ in keywords]

    def process_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        text = data.get('cleaned_html', '')
        
        entities = self.perform_ner(text)
        topics = self.topic_modeling([text])
        embedding = self.generate_embeddings([text])[0]
        sentiment = self.perform_sentiment_analysis(text)
        summary = self.summarize_text(text)
        keywords = self.extract_keywords(text)
        
        data['nlp_processed'] = {
            'entities': entities,
            'topics': topics,
            'embedding': embedding,
            'sentiment': sentiment,
            'summary': summary,
            'keywords': keywords
        }
        
        return data

    def process_directory(self, input_dir, output_dir):
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
    input_dir = os.path.join('data', 'raw', 'async')  # Directory containing your JSON files
    output_dir = os.path.join('data', 'processed')  # Directory to save processed data

    processor = NLPProcessor()
    processor.process_directory(input_dir, output_dir)

if __name__ == "__main__":
    main()
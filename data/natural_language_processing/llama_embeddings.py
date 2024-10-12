import json
import os
import spacy
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# Initialize TF-IDF vectorizer
tfidf_vectorizer = TfidfVectorizer(max_features=300)

def perform_ner(text):
    doc = nlp(text)
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    return entities

def topic_modeling(texts, num_topics=5, num_words=10):
    if len(texts) < 2:
        return ["Not enough documents for topic modeling"]
    
    # Start with very permissive parameters
    vectorizer = CountVectorizer(max_df=1.0, min_df=1, stop_words='english')
    try:
        doc_term_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return ["Unable to perform topic modeling due to document similarity"]
    
    # Check if we have enough features for LDA
    n_features = doc_term_matrix.shape[1]
    if n_features < num_topics:
        num_topics = max(2, n_features - 1)  # Ensure at least 2 topics if possible
    
    lda = LatentDirichletAllocation(n_components=num_topics, random_state=42)
    lda.fit(doc_term_matrix)
    
    words = vectorizer.get_feature_names_out()
    topics = []
    for topic_idx, topic in enumerate(lda.components_):
        top_words = [words[i] for i in topic.argsort()[:-num_words - 1:-1]]
        topics.append(f"Topic {topic_idx + 1}: {', '.join(top_words)}")
    
    return topics

# Modify the process_file function to handle potential errors
def process_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    all_texts = []
    processed_data = []

    # Check if data is a list or a single item
    if isinstance(data, list):
        items = data
    else:
        items = [data]
    
    for item in items:
        # Check if item is a string (entire content) or a dictionary
        if isinstance(item, str):
            text = item
        elif isinstance(item, dict):
            if 'llm_response' in item and isinstance(item['llm_response'], dict):
                text = ' '.join(item['llm_response'].get('key_points', []))
            else:
                # If structure is different, try to extract text from known fields
                text = item.get('content', '') or item.get('text', '') or str(item)
        else:
            text = str(item)
        
        all_texts.append(text)
        processed_item = {'original_content': text}
        processed_data.append(processed_item)
    
    # Perform NLP processing
    try:
        topics = topic_modeling(all_texts)
    except Exception as e:
        topics = [f"Topic modeling failed: {str(e)}"]
    
    try:
        embeddings = generate_embeddings(all_texts)
    except Exception as e:
        embeddings = [f"Embedding generation failed: {str(e)}"] * len(all_texts)
    
    for i, processed_item in enumerate(processed_data):
        text = processed_item['original_content']
        processed_item['entities'] = perform_ner(text)
        processed_item['topic'] = topics[0] if len(topics) > 0 else "No topic available"
        processed_item['embedding'] = embeddings[i] if i < len(embeddings) else "No embedding available"
    
    return processed_data

# Process all files
input_dir = '../raw/llama'
output_dir = '../processed'
os.makedirs(output_dir, exist_ok=True)

for filename in os.listdir(input_dir):
    if filename.endswith('.json'):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, f"processed_{filename}")
        
        processed_data = process_file(input_path)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=4)
        
        print(f"Processed data saved to {output_path}")
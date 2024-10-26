from typing import List, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging
from utils.preprocessing import preprocess_query, expand_query

logger = logging.getLogger(__name__)

class QueryProcessor:
    def __init__(self):
        self.vectorizer = TfidfVectorizer()
    
    def is_query_relevant(self, query: str, keywords: List[str], threshold: float = 0.05) -> Tuple[bool, float]:
        texts = keywords + [query]
        
        try:
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            query_vec = tfidf_matrix[-1]
            keyword_vecs = tfidf_matrix[:-1]
            similarities = cosine_similarity(query_vec, keyword_vecs)
            
            max_similarity = np.max(similarities)
            is_relevant = max_similarity > threshold
            
            return bool(is_relevant), float(max_similarity)
        except Exception as e:
            logger.error(f"Error checking query relevance: {str(e)}")
            return False, 0.0

    def process_query(self, query: str, qdrant_service, ollama_service):
        try:
            # Handle greetings
            if query.lower() in ["hi", "hello", "hey"]:
                return {
                    "type": "ai",
                    "content": "Hello! How can I assist you with information about SRH Hochschule Heidelberg today?",
                    "is_from_knowledge_base": False,
                    "relevance_score": 0.0,
                    "search_results": []
                }

            # Handle knowledge base inquiries
            if query.lower() in ["what is in your knowledge base?", "what do you know?", "what information do you have?"]:
                summary = qdrant_service.get_knowledge_base_summary()
                return {
                    "type": "ai",
                    "content": summary,
                    "is_from_knowledge_base": True,
                    "relevance_score": 1.0,
                    "search_results": []
                }

            # Process regular queries
            preprocessed_query = preprocess_query(query)
            keywords = qdrant_service.get_keywords()
            is_relevant, relevance_score = self.is_query_relevant(preprocessed_query, keywords)

            if is_relevant:
                expanded_queries = expand_query(preprocessed_query)
                all_results = []
                
                for expanded_query in expanded_queries:
                    query_vector = ollama_service.get_embedding(expanded_query)
                    search_results = qdrant_service.search(query_vector)
                    all_results.extend(search_results)
                
                results = []
                for result in all_results[:5]:
                    results.append({
                        "content": result.payload.get('original_content', ''),
                        "score": result.score,
                        "category": result.payload.get('category'),
                        "source": result.payload.get('source')
                    })

                context = "\n\n".join([r["content"] for r in results])
                prompt = self.generate_prompt(query, context, is_relevant)
                ai_response = ollama_service.generate_response(prompt)

                return {
                    "type": "ai",
                    "content": ai_response,
                    "is_from_knowledge_base": True,
                    "relevance_score": relevance_score,
                    "search_results": results
                }
            else:
                prompt = self.generate_prompt(query, "", False)
                ai_response = ollama_service.generate_response(prompt)
                
                return {
                    "type": "ai",
                    "content": ai_response,
                    "is_from_knowledge_base": False,
                    "relevance_score": relevance_score,
                    "search_results": []
                }

        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                "type": "error",
                "content": "An error occurred while processing your request. Please try again."
            }

    def generate_prompt(self, query: str, context: str, is_relevant: bool) -> str:
        if is_relevant:
            return f"""Based on the following context from the knowledge base, answer the question:

Context:
{context}

Question: {query}

Answer:"""
        else:
            return f"""You are an AI assistant for SRH Hochschule Heidelberg. Please answer this question using your general knowledge:

Question: {query}

Answer:"""
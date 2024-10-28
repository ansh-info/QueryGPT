import re
from typing import List, Tuple, Dict, Any, Optional
import logging
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
try:
    import spacy
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False

logger = logging.getLogger(__name__)

class QueryProcessor:
    def __init__(self):
        self.vectorizer = TfidfVectorizer()
        self.common_keywords = {
            'srh', 'university', 'course', 'program', 'study', 
            'admission', 'faculty', 'research', 'campus', 'heidelberg',
            'computer', 'science', 'artificial', 'intelligence', 'data',
            'bachelor', 'master', 'degree', 'professor', 'student'
        }
        # Initialize spaCy if available
        if NLP_AVAILABLE:
            try:
                self.nlp = spacy.load('en_core_web_sm')
            except Exception as e:
                logger.warning(f"Could not load spaCy model: {e}")
                self.nlp = None
        else:
            self.nlp = None

    def process_query(self, query: str, qdrant_service, ollama_service) -> Dict[str, Any]:
        """Main query processing method"""
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
                    "content": summary['text'] if isinstance(summary, dict) else summary,
                    "is_from_knowledge_base": True,
                    "relevance_score": 1.0,
                    "search_results": [],
                    "metadata": {
                        "type": "summary",
                        "timestamp": datetime.now().isoformat(),
                        "summary_data": summary.get('data', {}) if isinstance(summary, dict) else {}
                    }
                }

            # Process regular queries
            query_analysis = self.analyze_query_complexity(query)
            preprocessed_query = self.preprocess_query(query)
            expanded_queries = self.expand_query(preprocessed_query)
            
            # Check relevance
            is_relevant, relevance_score = self.is_query_relevant(
                preprocessed_query, 
                qdrant_service.get_keywords()
            )

            if is_relevant:
                # Search across expanded queries
                all_results = []
                for expanded_query in expanded_queries:
                    query_vector = ollama_service.get_embedding(expanded_query)
                    if query_vector:
                        search_results = qdrant_service.search(
                            query_vector,
                            limit=5
                        )
                        all_results.extend(search_results)

                # Process and deduplicate results
                results = []
                seen_contents = set()
                for result in all_results:
                    content = result.payload.get('original_content', '')
                    if content and content not in seen_contents:
                        seen_contents.add(content)
                        results.append({
                            "content": content,
                            "score": result.score,
                            "category": result.payload.get('category'),
                            "source": result.payload.get('source'),
                            "metadata": result.payload.get('metadata', {}),
                            "timestamp": result.payload.get('timestamp')
                        })

                # Sort by relevance and limit
                results.sort(key=lambda x: x['score'], reverse=True)
                results = results[:5]

                # Generate response
                context = "\n\n".join([r["content"] for r in results])
                prompt = self.generate_enhanced_prompt(query, context, True, query_analysis)
                ai_response = ollama_service.generate_response(prompt)

                return {
                    "type": "ai",
                    "content": ai_response,
                    "is_from_knowledge_base": True,
                    "relevance_score": relevance_score,
                    "search_results": results,
                    "search_info": f"Found {len(results)} relevant results",
                    "metadata": {
                        "query_expansion": expanded_queries,
                        "query_analysis": query_analysis,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            else:
                # Handle non-relevant queries
                prompt = self.generate_enhanced_prompt(query, "", False, query_analysis)
                ai_response = ollama_service.generate_response(prompt)
                
                return {
                    "type": "ai",
                    "content": ai_response,
                    "is_from_knowledge_base": False,
                    "relevance_score": relevance_score,
                    "search_results": [],
                    "search_info": "No relevant results found in knowledge base",
                    "metadata": {
                        "query_analysis": query_analysis,
                        "timestamp": datetime.now().isoformat()
                    }
                }

        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                "type": "error",
                "content": "An error occurred while processing your request. Please try again."
            }

    def is_query_relevant(self, query: str, keywords: List[str], threshold: float = 0.05) -> Tuple[bool, float]:
        """Check if query is relevant to knowledge base"""
        try:
            if not keywords:
                return False, 0.0

            texts = keywords + [query]
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            
            query_vec = tfidf_matrix[-1]
            keyword_vecs = tfidf_matrix[:-1]
            similarities = cosine_similarity(query_vec, keyword_vecs)
            
            max_similarity = np.max(similarities)
            is_relevant = max_similarity > threshold
            
            logger.debug(f"Query relevance: {is_relevant}, Score: {max_similarity}")
            
            return bool(is_relevant), float(max_similarity)
        except Exception as e:
            logger.error(f"Error checking query relevance: {str(e)}")
            return False, 0.0

    def preprocess_query(self, query: str) -> str:
        """Enhanced query preprocessing"""
        try:
            # Basic preprocessing
            query = query.lower().strip()
            query = re.sub(r'\s+', ' ', query)  # Normalize whitespace
            query = re.sub(r'[^\w\s]', '', query)  # Remove special characters
            
            # Advanced preprocessing if spaCy is available
            if self.nlp:
                doc = self.nlp(query)
                # Remove stop words and lemmatize
                query = ' '.join([token.lemma_ for token in doc if not token.is_stop])
            
            return query
        except Exception as e:
            logger.error(f"Error preprocessing query: {str(e)}")
            return query

    def expand_query(self, query: str) -> List[str]:
        """Enhanced query expansion"""
        try:
            expanded = [query]
            
            # Handle abbreviations and variations
            replacements = {
                "srh": "srh hochschule heidelberg",
                "uni": "university",
                "cs": "computer science",
                "ai": "artificial intelligence",
                "ml": "machine learning",
                "db": "database",
                "prof": "professor",
                "dept": "department",
                "info": "information",
                "prog": "program"
            }
            
            # Replace abbreviations
            for old, new in replacements.items():
                if old in query:
                    expanded.append(query.replace(old, new))
            
            # Add common variations
            words = query.split()
            for i, word in enumerate(words):
                if word in replacements:
                    new_words = words.copy()
                    new_words[i] = replacements[word]
                    expanded.append(' '.join(new_words))
            
            return list(set(expanded))
        except Exception as e:
            logger.error(f"Error expanding query: {str(e)}")
            return [query]

    def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        try:
            if self.nlp:
                doc = self.nlp(text)
                keywords = [token.text.lower() for token in doc 
                          if not token.is_stop and token.is_alpha]
            else:
                words = text.lower().split()
                stop_words = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to'])
                keywords = [word for word in words if word not in stop_words]
            
            return keywords
        except Exception as e:
            logger.error(f"Error extracting keywords: {str(e)}")
            return text.split()

    def analyze_query_complexity(self, query: str) -> Dict[str, Any]:
        """Analyze query complexity for better processing"""
        try:
            words = query.split()
            keywords = self.extract_keywords(query)
            
            analysis = {
                'length': len(words),
                'is_complex': len(words) > 5,
                'has_keywords': any(keyword in query.lower() for keyword in self.common_keywords),
                'query_type': self.determine_query_type(query),
                'extracted_keywords': keywords
            }
            
            if self.nlp:
                doc = self.nlp(query)
                analysis.update({
                    'named_entities': [(ent.text, ent.label_) for ent in doc.ents],
                    'noun_phrases': [chunk.text for chunk in doc.noun_chunks]
                })
            
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing query complexity: {str(e)}")
            return {'error': str(e)}

    def determine_query_type(self, query: str) -> str:
        """Determine the type of query for specialized handling"""
        try:
            query_lower = query.lower()
            if any(word in query_lower for word in ['what', 'which', 'how']):
                return 'informational'
            elif any(word in query_lower for word in ['where', 'when']):
                return 'factual'
            elif any(word in query_lower for word in ['why', 'explain']):
                return 'explanatory'
            elif any(word in query_lower for word in ['compare', 'difference', 'versus', 'vs']):
                return 'comparative'
            elif any(word in query_lower for word in ['list', 'show', 'give']):
                return 'listing'
            return 'general'
        except Exception as e:
            logger.error(f"Error determining query type: {str(e)}")
            return 'general'

    def generate_enhanced_prompt(self, query: str, context: str, is_relevant: bool, query_analysis: Dict[str, Any]) -> str:
        """Generate enhanced prompt based on query analysis"""
        try:
            if is_relevant:
                prompt = f"""Based on the following context from the knowledge base, provide a detailed answer to the question.
If the context doesn't fully address the question, supplement with relevant general knowledge.

Context:
{context}

Question: {query}

Query Type: {query_analysis.get('query_type', 'general')}

Please provide:
1. A direct answer to the question
2. Any relevant additional information
3. Related topics or suggestions
4. Sources of information when available

Answer:"""
            else:
                prompt = f"""You are an AI assistant for SRH Hochschule Heidelberg. The following question was not found in our knowledge base.
Please provide a general answer while noting that for specific, up-to-date details, the user should consult official sources.

Question: {query}

Query Type: {query_analysis.get('query_type', 'general')}

Please provide:
1. A general answer based on available information
2. A note about consulting official sources for specific details
3. Any relevant suggestions or related topics

Answer:"""
            return prompt
        except Exception as e:
            logger.error(f"Error generating prompt: {str(e)}")
            return f"Question: {query}\n\nPlease provide a helpful response."
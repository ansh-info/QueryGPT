import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from qdrant_client.http import models

logger = logging.getLogger(__name__)

@dataclass
class SearchFilter:
    date_range: Optional[tuple] = None
    categories: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    min_score: float = 0.0
    max_results: int = 10

@dataclass
class SearchResult:
    content: str
    score: float
    metadata: Dict[str, Any]
    highlights: List[str]
    category: str
    source: str
    timestamp: datetime

class EnhancedSearchService:
    def __init__(self, qdrant_service, ollama_service):
        self.qdrant = qdrant_service
        self.ollama = ollama_service
        self.vectorizer = TfidfVectorizer()
        self.min_semantic_score = 0.6

    def search(self, query: str, filters: Optional[SearchFilter] = None) -> List[SearchResult]:
        """Main search method combining semantic search with filters"""
        try:
            # Get query embedding
            query_vector = self.ollama.get_embedding(query)
            if not query_vector:
                logger.error("Failed to generate query embedding")
                return []

            # Prepare filters for Qdrant
            qdrant_filter = self._convert_filters(filters)
            
            # Perform vector search with corrected parameter name
            raw_results = self.qdrant.search(
                query_vector=query_vector,
                filters=qdrant_filter,  # Changed from query_filter to filters
                limit=filters.max_results if filters else 10
            )

            # Process results
            enhanced_results = []
            for result in raw_results:
                if hasattr(result, 'score') and result.score < self.min_semantic_score:
                    continue

                # Generate result highlights
                highlights = self._generate_highlights(
                    query, 
                    result.payload.get('original_content', '')
                )

                try:
                    timestamp = datetime.fromisoformat(
                        result.payload.get('timestamp', datetime.now().isoformat())
                    )
                except (ValueError, TypeError):
                    timestamp = datetime.now()

                # Create structured result
                search_result = SearchResult(
                    content=result.payload.get('original_content', ''),
                    score=getattr(result, 'score', 0.0),
                    metadata=result.payload.get('metadata', {}),
                    highlights=highlights,
                    category=result.payload.get('category', 'Unknown'),
                    source=result.payload.get('source', 'Unknown'),
                    timestamp=timestamp
                )
                enhanced_results.append(search_result)

            return enhanced_results

        except Exception as e:
            logger.error(f"Error in search: {str(e)}")
            return []

    def _convert_filters(self, filters: Optional[SearchFilter]) -> Dict[str, Any]:
        """Convert SearchFilter to Qdrant filter format"""
        try:
            if not filters:
                return {}

            filter_dict = {}
            
            if filters.date_range:
                start_date, end_date = filters.date_range
                filter_dict['timestamp'] = {
                    'gte': start_date.isoformat(),
                    'lte': end_date.isoformat()
                }
            
            if filters.categories:
                filter_dict['category'] = {
                    'in': filters.categories
                }
                
            if filters.sources:
                filter_dict['source'] = {
                    'in': filters.sources
                }
                
            return filter_dict
        
        except Exception as e:
            logger.error(f"Error converting filters: {str(e)}")
            return {}

    def _generate_highlights(self, query: str, content: str, context_words: int = 5) -> List[str]:
        """Generate highlighted snippets from content"""
        try:
            # Tokenize query and content
            query_tokens = set(query.lower().split())
            content_tokens = content.split()
            
            highlights = []
            for i, token in enumerate(content_tokens):
                if token.lower() in query_tokens:
                    # Get context window
                    start = max(0, i - context_words)
                    end = min(len(content_tokens), i + context_words + 1)
                    
                    # Create highlight with context
                    highlight = ' '.join(content_tokens[start:end])
                    if start > 0:
                        highlight = f"...{highlight}"
                    if end < len(content_tokens):
                        highlight = f"{highlight}..."
                        
                    highlights.append(highlight)
            
            return highlights
        except Exception as e:
            logger.error(f"Error generating highlights: {str(e)}")
            return []

    def get_suggestions(self, partial_query: str, max_suggestions: int = 5) -> List[str]:
        """Get search suggestions based on partial query"""
        try:
            # Get recent successful queries from cache or database
            recent_queries = self.qdrant.get_recent_queries(limit=100)
            
            if not recent_queries:
                return []

            # Calculate similarity scores
            query_matrix = self.vectorizer.fit_transform([partial_query] + recent_queries)
            similarities = cosine_similarity(query_matrix[0:1], query_matrix[1:])[0]
            
            # Get top suggestions
            suggestions = []
            for score, query in sorted(zip(similarities, recent_queries), reverse=True):
                if score > 0.3 and len(suggestions) < max_suggestions:
                    suggestions.append(query)
                    
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {str(e)}")
            return []

    def get_facets(self, results: List[SearchResult]) -> Dict[str, Dict[str, int]]:
        """Generate facets from search results"""
        try:
            facets = {
                'categories': {},
                'sources': {},
                'year': {}
            }
            
            for result in results:
                # Category facets
                category = result.category
                facets['categories'][category] = facets['categories'].get(category, 0) + 1
                
                # Source facets
                source = result.source
                facets['sources'][source] = facets['sources'].get(source, 0) + 1
                
                # Year facets
                year = result.timestamp.year
                facets['year'][year] = facets['year'].get(year, 0) + 1
                
            return facets
        except Exception as e:
            logger.error(f"Error generating facets: {str(e)}")
            return {'categories': {}, 'sources': {}, 'year': {}}
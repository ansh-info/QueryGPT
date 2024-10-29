from qdrant_client import QdrantClient
from qdrant_client.http import models
from typing import List, Optional, Dict, Any, Tuple
from collections import Counter, defaultdict
import logging
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

class QdrantService:
    def __init__(self, host: str = "localhost", port: int = 6333):
        """Initialize QdrantService with connection parameters"""
        try:
            self.client = QdrantClient(host=host, port=port)
            self.collection_name = "knowledge_base"
            logger.info(f"Connected to Qdrant at {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {str(e)}")
            raise

    def search(self, query_vector: List[float], filters: Optional[dict] = None, limit: int = 5) -> List[Any]:
        """Perform vector search with filters"""
        try:
            filter_conditions = []
            if filters:
                for key, value in filters.items():
                    filter_conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        )
                    )
            
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=models.Filter(
                    must=filter_conditions
                ) if filter_conditions else None,
                limit=limit,
                with_payload=True,
                score_threshold=0.0
            )
            
            logger.debug(f"Search completed: {len(search_result)} results found")
            return search_result
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            return []

    def get_knowledge_base_summary(self) -> Dict[str, Any]:
        """Get comprehensive knowledge base summary"""
        try:
            entries = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                with_payload=True
            )[0]

            # Analyze entries
            categories = Counter()
            topics = Counter()
            sources = Counter()
            dates = []
            metadata_analysis = defaultdict(Counter)
            total_entries = len(entries)

            for entry in entries:
                payload = entry.payload
                # Category analysis
                categories[payload.get('category', 'Uncategorized')] += 1
                
                # Topic analysis
                if 'keywords' in payload:
                    topics.update(payload['keywords'])
                
                # Source analysis
                if 'source' in payload:
                    sources[payload['source']] += 1
                
                # Date analysis
                if 'timestamp' in payload:
                    dates.append(payload['timestamp'])
                
                # Metadata analysis
                for key, value in payload.items():
                    if key not in ['category', 'keywords', 'source', 'timestamp']:
                        metadata_analysis[key][str(value)] += 1

            stats = {
                'total_entries': total_entries,
                'categories': {
                    'count': len(categories),
                    'top': categories.most_common(5),
                    'distribution': {k: v/total_entries for k, v in categories.items()}
                },
                'topics': {
                    'count': len(topics),
                    'top': topics.most_common(10)
                },
                'sources': {
                    'count': len(sources),
                    'top': sources.most_common(5)
                },
                'temporal': {
                    'earliest': min(dates) if dates else None,
                    'latest': max(dates) if dates else None,
                    'date_range': (max(dates) - min(dates)).days if dates else 0
                },
                'metadata_stats': {
                    field: {
                        'unique_values': len(values),
                        'top_values': values.most_common(5)
                    }
                    for field, values in metadata_analysis.items()
                }
            }

            summary_text = (
                f"Knowledge base contains {total_entries} entries covering {len(categories)} "
                f"categories and {len(topics)} unique topics. "
                f"Main categories: {', '.join(f'{cat} ({count})' for cat, count in categories.most_common(3))}. "
                f"Key topics: {', '.join(topic for topic, _ in topics.most_common(5))}."
            )

            return {
                'text': summary_text,
                'stats': stats,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error generating knowledge base summary: {str(e)}")
            return {
                'text': "Unable to generate summary at the moment.",
                'stats': {},
                'timestamp': datetime.now().isoformat()
            }

    def get_keywords(self) -> List[str]:
        """Get all unique keywords from the knowledge base"""
        try:
            entries = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                with_payload=True
            )[0]

            all_keywords = set()
            for entry in entries:
                keywords = entry.payload.get('keywords', [])
                all_keywords.update(keywords)

            return list(all_keywords)
        except Exception as e:
            logger.error(f"Error getting keywords: {str(e)}")
            return []

    def add_entry(self, content: str, embedding: List[float], metadata: Dict[str, Any]) -> bool:
        """Add a new entry to the knowledge base"""
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=str(int(datetime.now().timestamp() * 1000)),
                        vector=embedding,
                        payload={
                            'original_content': content,
                            **metadata,
                            'timestamp': datetime.now().isoformat()
                        }
                    )
                ]
            )
            logger.info("Successfully added new entry to knowledge base")
            return True
        except Exception as e:
            logger.error(f"Error adding entry: {str(e)}")
            return False

    def get_similar_entries(self, entry_id: str, limit: int = 5) -> List[Dict]:
        """Get similar entries to a given entry"""
        try:
            entry = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[entry_id]
            )
            
            if not entry:
                return []
            
            similar = self.client.search(
                collection_name=self.collection_name,
                query_vector=entry[0].vector,
                limit=limit + 1
            )
            
            return [
                {
                    'content': r.payload.get('original_content', ''),
                    'score': r.score,
                    'metadata': {k: v for k, v in r.payload.items() 
                               if k not in ['original_content', 'timestamp']}
                }
                for r in similar
                if str(r.id) != entry_id
            ]
        except Exception as e:
            logger.error(f"Error getting similar entries: {str(e)}")
            return []

    def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry from the knowledge base"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[entry_id]
                )
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting entry: {str(e)}")
            return False

    def update_entry(self, entry_id: str, content: str, embedding: List[float], metadata: Dict[str, Any]) -> bool:
        """Update an existing entry"""
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=entry_id,
                        vector=embedding,
                        payload={
                            'original_content': content,
                            **metadata,
                            'updated_at': datetime.now().isoformat()
                        }
                    )
                ]
            )
            return True
        except Exception as e:
            logger.error(f"Error updating entry: {str(e)}")
            return False

    def health_check(self) -> Dict[str, Any]:
        """Check the health of the Qdrant service"""
        try:
            collections = self.client.get_collections()
            kb_collection = next(
                (c for c in collections.collections 
                 if c.name == self.collection_name), 
                None
            )
            
            return {
                'status': 'healthy',
                'collection_exists': bool(kb_collection),
                'vector_size': kb_collection.vector_size if kb_collection else None,
                'total_entries': kb_collection.points_count if kb_collection else 0,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get detailed statistics about the collection"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                'points_count': collection_info.points_count,
                'vectors_config': collection_info.config.params,
                'optimization': collection_info.optimization_config,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {}

    def clear_cache(self) -> bool:
        """Clear the collection's optimization cache"""
        try:
            self.client.update_collection(
                collection_name=self.collection_name,
                optimizer_config=models.OptimizersConfigDiff(
                    flush_interval_sec=1
                )
            )
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return False

    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific entry by ID"""
        try:
            results = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[entry_id]
            )
            if results:
                return {
                    'content': results[0].payload.get('original_content', ''),
                    'metadata': {k: v for k, v in results[0].payload.items() 
                               if k != 'original_content'},
                    'vector': results[0].vector
                }
            return None
        except Exception as e:
            logger.error(f"Error retrieving entry: {str(e)}")
            return None
        
    def get_categories(self) -> List[str]:
        """Get all unique categories from the knowledge base"""
        try:
            entries = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                with_payload=True
            )[0]
            
            categories = set()
            for entry in entries:
                if 'category' in entry.payload:
                    categories.add(entry.payload['category'])
                else:
                    categories.add('Uncategorized')  # Default category
            
            return sorted(list(categories))
        except Exception as e:
            logger.error(f"Error getting categories: {str(e)}")
            return ['General']  # Return default category on error

    def get_sources(self) -> List[str]:
        """Get all unique sources from the knowledge base"""
        try:
            entries = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                with_payload=True
            )[0]
            
            sources = set()
            for entry in entries:
                if 'source' in entry.payload:
                    sources.add(entry.payload['source'])
                else:
                    sources.add('Unknown')  # Default source
            
            return sorted(list(sources))
        except Exception as e:
            logger.error(f"Error getting sources: {str(e)}")
            return ['General']  # Return default source on error

    def get_recent_queries(self, limit: int = 100) -> List[str]:
        """Get recent successful queries"""
        try:
            # You might want to store queries in a separate collection
            # For now, we'll return an empty list or implement based on your needs
            return []
        except Exception as e:
            logger.error(f"Error getting recent queries: {str(e)}")
            return []
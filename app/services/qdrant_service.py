from qdrant_client import QdrantClient
from qdrant_client.http import models
from typing import List, Optional, Dict, Any
from collections import Counter
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class QdrantService:
    def __init__(self):
        self.client = QdrantClient("localhost", port=6333)
        self.collection_name = "knowledge_base"

    def search(self, query_vector: List[float], filters: Optional[dict] = None, limit: int = 5):
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
            return search_result
        except Exception as e:
            logger.error(f"Error searching Qdrant: {str(e)}")
            return []

    def get_knowledge_base_summary(self) -> Dict[str, Any]:
        """Get comprehensive knowledge base summary with statistics"""
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

            # Generate summary
            summary = {
                'total_entries': total_entries,
                'top_categories': categories.most_common(5),
                'top_topics': topics.most_common(10),
                'top_sources': sources.most_common(5),
                'date_range': {
                    'earliest': min(dates) if dates else None,
                    'latest': max(dates) if dates else None
                },
                'statistics': {
                    'categories_count': len(categories),
                    'topics_count': len(topics),
                    'sources_count': len(sources)
                }
            }

            # Generate readable summary text
            summary_text = f"Knowledge base contains {total_entries} entries. "
            summary_text += "Main categories: " + ", ".join(f"{cat} ({count})" for cat, count in categories.most_common(5)) + ". "
            summary_text += "Key topics: " + ", ".join(topic for topic, _ in topics.most_common(10)) + "."

            return {
                'text': summary_text,
                'data': summary
            }

        except Exception as e:
            logger.error(f"Error generating knowledge base summary: {str(e)}")
            return {
                'text': "Unable to generate summary at the moment.",
                'data': {}
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
                category = entry.payload.get('category')
                if category:
                    categories.add(category)

            return list(categories)
        except Exception as e:
            logger.error(f"Error getting categories: {str(e)}")
            return []

    def add_entry(self, content: str, metadata: Dict[str, Any], embedding: List[float]) -> bool:
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
            return True
        except Exception as e:
            logger.error(f"Error adding entry: {str(e)}")
            return False
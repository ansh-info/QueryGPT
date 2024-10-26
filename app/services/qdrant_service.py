from qdrant_client import QdrantClient
from qdrant_client.http import models
from typing import List, Optional
from collections import Counter
import logging

logger = logging.getLogger(__name__)

class QdrantService:
    def __init__(self):
        self.client = QdrantClient("localhost", port=6333)
    
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
                collection_name="knowledge_base",
                query_vector=query_vector,
                query_filter=models.Filter(
                    must=filter_conditions
                ) if filter_conditions else None,
                limit=limit
            )
            return search_result
        except Exception as e:
            logger.error(f"Error searching Qdrant: {str(e)}")
            return []
    
    def get_knowledge_base_summary(self):
        try:
            entries = self.client.scroll(
                collection_name="knowledge_base",
                limit=1000
            )[0]

            categories = Counter()
            all_keywords = Counter()
            entry_count = len(entries)
            
            for entry in entries:
                payload = entry.payload
                categories[payload.get('category', 'Uncategorized')] += 1
                keywords = payload.get('keywords', [])
                all_keywords.update(keywords)

            top_categories = categories.most_common(5)
            top_keywords = all_keywords.most_common(10)

            summary = f"Knowledge base contains {entry_count} entries. "
            summary += "Categories: " + ", ".join(f"{cat} ({count})" for cat, count in top_categories) + ". "
            summary += "Key topics: " + ", ".join(keyword for keyword, _ in top_keywords) + "."

            return summary
        except Exception as e:
            logger.error(f"Error generating knowledge base summary: {str(e)}")
            return "Unable to generate summary at the moment."

    def get_keywords(self) -> List[str]:
        entries = self.client.scroll(
            collection_name="knowledge_base",
            limit=1000
        )[0]

        all_keywords = []
        for entry in entries:
            keywords = entry.payload.get('keywords', [])
            all_keywords.extend(keywords)

        return list(set(all_keywords))
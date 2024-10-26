from datetime import datetime
from typing import List, Dict
from collections import Counter
import logging

logger = logging.getLogger(__name__)

class FeedbackAnalyzer:
    def __init__(self):
        self.feedback_data = []
    
    def store_feedback(self, response: str, feedback_type: str, timestamp: datetime):
        self.feedback_data.append({
            'response': response,
            'feedback': feedback_type,
            'timestamp': timestamp
        })
    
    def analyze_feedback(self) -> Dict:
        try:
            if not self.feedback_data:
                return {
                    'satisfaction_rate': 0,
                    'total_responses': 0,
                    'recent_feedback': []
                }
            
            positive_count = sum(1 for item in self.feedback_data 
                               if item['feedback'] == 'positive')
            total_count = len(self.feedback_data)
            
            # Get most recent feedback
            recent_feedback = sorted(
                self.feedback_data,
                key=lambda x: x['timestamp'],
                reverse=True
            )[:5]
            
            return {
                'satisfaction_rate': positive_count / total_count,
                'total_responses': total_count,
                'recent_feedback': recent_feedback
            }
        except Exception as e:
            logger.error(f"Error analyzing feedback: {str(e)}")
            return {
                'satisfaction_rate': 0,
                'total_responses': 0,
                'recent_feedback': []
            }

class QueryAnalyzer:
    def __init__(self):
        self.query_history = []
    
    def add_query(self, query: str, timestamp: datetime):
        self.query_history.append({
            'query': query,
            'timestamp': timestamp
        })
    
    def get_popular_queries(self, limit: int = 5) -> List[Dict]:
        query_counter = Counter(item['query'] for item in self.query_history)
        return query_counter.most_common(limit)
    
    def get_query_trends(self) -> Dict:
        if not self.query_history:
            return {'queries_per_hour': 0, 'total_queries': 0}
        
        total_queries = len(self.query_history)
        
        # Calculate queries per hour for the last 24 hours
        recent_queries = [q for q in self.query_history 
                         if (datetime.now() - q['timestamp']).total_seconds() < 86400]
        queries_per_hour = len(recent_queries) / 24
        
        return {
            'queries_per_hour': queries_per_hour,
            'total_queries': total_queries
        }
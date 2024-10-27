import logging
from datetime import datetime
from typing import Dict, List, Any
from collections import Counter

logger = logging.getLogger(__name__)

class FeedbackAnalyzer:
    def __init__(self):
        self.feedback_data = []
    
    def store_feedback(self, response: str, feedback_type: str, timestamp: datetime):
        """Store user feedback"""
        self.feedback_data.append({
            'response': response,
            'feedback': feedback_type,
            'timestamp': timestamp
        })
    
    def analyze_feedback(self) -> Dict[str, Any]:
        """Analyze feedback patterns"""
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

    def get_stats(self) -> Dict[str, Any]:
        """Get feedback statistics"""
        try:
            total_feedback = len(self.feedback_data)
            positive_feedback = sum(1 for f in self.feedback_data if f['feedback'] == 'positive')
            
            return {
                'total_feedback': total_feedback,
                'positive_feedback': positive_feedback,
                'satisfaction_rate': positive_feedback / total_feedback if total_feedback > 0 else 0,
                'recent_feedback': sorted(self.feedback_data, key=lambda x: x['timestamp'], reverse=True)[:5]
            }
        except Exception as e:
            logger.error(f"Error getting feedback stats: {str(e)}")
            return {}

    def clear_feedback(self):
        """Clear all feedback data"""
        self.feedback_data = []
        logger.info("Feedback data cleared")
import logging
from datetime import datetime
from typing import Dict, List, Any
from collections import Counter, defaultdict

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
        logger.info(f"Feedback stored: {feedback_type} at {timestamp}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get basic feedback statistics"""
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

    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed feedback statistics"""
        try:
            stats = self.get_stats()
            
            # Feedback by hour
            feedback_by_hour = defaultdict(int)
            for feedback in self.feedback_data:
                hour = feedback['timestamp'].strftime('%Y-%m-%d %H:00')
                feedback_by_hour[hour] += 1
            
            # Response analysis
            response_patterns = defaultdict(int)
            for feedback in self.feedback_data:
                words = len(feedback['response'].split())
                response_patterns['short' if words < 50 else 'medium' if words < 150 else 'long'] += 1
            
            stats.update({
                'feedback_by_hour': dict(feedback_by_hour),
                'response_patterns': dict(response_patterns),
                'feedback_trends': self._analyze_trends()
            })
            
            return stats
        except Exception as e:
            logger.error(f"Error getting detailed stats: {str(e)}")
            return {}

    def _analyze_trends(self) -> Dict[str, Any]:
        """Analyze feedback trends"""
        try:
            if not self.feedback_data:
                return {}
            
            # Group feedback by day
            daily_feedback = defaultdict(lambda: {'positive': 0, 'negative': 0})
            for feedback in self.feedback_data:
                day = feedback['timestamp'].strftime('%Y-%m-%d')
                daily_feedback[day][feedback['feedback']] += 1
            
            # Calculate daily satisfaction rates
            trends = {
                day: {
                    'total': data['positive'] + data['negative'],
                    'satisfaction_rate': data['positive'] / (data['positive'] + data['negative'])
                    if (data['positive'] + data['negative']) > 0 else 0
                }
                for day, data in daily_feedback.items()
            }
            
            return trends
        except Exception as e:
            logger.error(f"Error analyzing trends: {str(e)}")
            return {}

    def clear_feedback(self):
        """Clear all feedback data"""
        self.feedback_data = []
        logger.info("Feedback data cleared")

    def export_feedback(self) -> List[Dict[str, Any]]:
        """Export feedback data"""
        return [
            {
                'response': f['response'],
                'feedback': f['feedback'],
                'timestamp': f['timestamp'].isoformat()
            }
            for f in self.feedback_data
        ]
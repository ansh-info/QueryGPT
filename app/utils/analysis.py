import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)

class FeedbackAnalyzer:
    def __init__(self):
        self.feedback_data = []
        self.last_analysis_time = None

    def store_feedback(self, response: str, feedback_type: str, timestamp: datetime, metadata: Dict = None):
        """Store user feedback with optional metadata"""
        feedback_entry = {
            'response': response,
            'feedback': feedback_type,
            'timestamp': timestamp,
            'metadata': metadata or {}
        }
        self.feedback_data.append(feedback_entry)
        logger.info(f"Feedback stored: {feedback_type} at {timestamp}")

    def get_stats(self) -> Dict[str, Any]:
        """Get basic feedback statistics"""
        try:
            total_feedback = len(self.feedback_data)
            positive_feedback = sum(1 for f in self.feedback_data if f['feedback'] == 'positive')
            
            stats = {
                'total_feedback': total_feedback,
                'positive_feedback': positive_feedback,
                'negative_feedback': total_feedback - positive_feedback,
                'satisfaction_rate': positive_feedback / total_feedback if total_feedback > 0 else 0,
                'recent_feedback': sorted(self.feedback_data, key=lambda x: x['timestamp'], reverse=True)[:5],
                'last_updated': datetime.now()
            }
            
            self.last_analysis_time = datetime.now()
            return stats
        except Exception as e:
            logger.error(f"Error getting feedback stats: {str(e)}")
            return {}

    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed feedback statistics with temporal analysis"""
        try:
            stats = self.get_stats()
            current_time = datetime.now()
            
            # Feedback by hour
            feedback_by_hour = defaultdict(lambda: {'positive': 0, 'negative': 0, 'total': 0})
            for feedback in self.feedback_data:
                hour = feedback['timestamp'].strftime('%Y-%m-%d %H:00')
                feedback_type = feedback['feedback']
                feedback_by_hour[hour][feedback_type] += 1
                feedback_by_hour[hour]['total'] += 1

            # Response length analysis
            response_patterns = defaultdict(int)
            for feedback in self.feedback_data:
                words = len(feedback['response'].split())
                if words < 50:
                    category = 'short'
                elif words < 150:
                    category = 'medium'
                else:
                    category = 'long'
                response_patterns[category] += 1

            # Time-based analysis
            last_24h = current_time - timedelta(hours=24)
            last_7d = current_time - timedelta(days=7)
            
            recent_stats = {
                'last_24h': {
                    'total': sum(1 for f in self.feedback_data if f['timestamp'] > last_24h),
                    'positive': sum(1 for f in self.feedback_data 
                                  if f['timestamp'] > last_24h and f['feedback'] == 'positive')
                },
                'last_7d': {
                    'total': sum(1 for f in self.feedback_data if f['timestamp'] > last_7d),
                    'positive': sum(1 for f in self.feedback_data 
                                  if f['timestamp'] > last_7d and f['feedback'] == 'positive')
                }
            }

            # Calculate satisfaction rates for recent periods
            for period in recent_stats:
                if recent_stats[period]['total'] > 0:
                    recent_stats[period]['satisfaction_rate'] = (
                        recent_stats[period]['positive'] / recent_stats[period]['total']
                    )
                else:
                    recent_stats[period]['satisfaction_rate'] = 0

            stats.update({
                'feedback_by_hour': dict(feedback_by_hour),
                'response_patterns': dict(response_patterns),
                'recent_stats': recent_stats,
                'feedback_trends': self._analyze_trends(),
                'hourly_activity': self._get_hourly_activity(),
                'metadata_analysis': self._analyze_metadata()
            })
            
            return stats
        except Exception as e:
            logger.error(f"Error getting detailed stats: {str(e)}")
            return {}

    def _analyze_trends(self) -> Dict[str, Any]:
        """Analyze feedback trends over time"""
        try:
            if not self.feedback_data:
                return {}
            
            # Group feedback by day
            daily_feedback = defaultdict(lambda: {'positive': 0, 'negative': 0})
            for feedback in self.feedback_data:
                day = feedback['timestamp'].strftime('%Y-%m-%d')
                daily_feedback[day][feedback['feedback']] += 1
            
            # Calculate daily satisfaction rates
            trends = {}
            for day, data in daily_feedback.items():
                total = data['positive'] + data['negative']
                trends[day] = {
                    'total': total,
                    'positive': data['positive'],
                    'negative': data['negative'],
                    'satisfaction_rate': data['positive'] / total if total > 0 else 0
                }
            
            return trends
        except Exception as e:
            logger.error(f"Error analyzing trends: {str(e)}")
            return {}

    def _get_hourly_activity(self) -> Dict[str, int]:
        """Get activity patterns by hour of day"""
        hourly_activity = defaultdict(int)
        for feedback in self.feedback_data:
            hour = feedback['timestamp'].strftime('%H')
            hourly_activity[hour] += 1
        return dict(sorted(hourly_activity.items()))

    def _analyze_metadata(self) -> Dict[str, Any]:
        """Analyze metadata patterns in feedback"""
        metadata_analysis = defaultdict(lambda: defaultdict(int))
        for feedback in self.feedback_data:
            if 'metadata' in feedback:
                for key, value in feedback['metadata'].items():
                    metadata_analysis[key][str(value)] += 1
        return {k: dict(v) for k, v in metadata_analysis.items()}

    def get_feedback_by_period(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get feedback within a specific time period"""
        return [
            feedback for feedback in self.feedback_data
            if start_date <= feedback['timestamp'] <= end_date
        ]

    def get_satisfaction_trend(self, days: int = 7) -> Dict[str, float]:
        """Get satisfaction rate trend over specified number of days"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        daily_rates = {}
        current_date = start_date
        
        while current_date <= end_date:
            day_feedback = [
                f for f in self.feedback_data
                if f['timestamp'].date() == current_date.date()
            ]
            
            if day_feedback:
                positive = sum(1 for f in day_feedback if f['feedback'] == 'positive')
                daily_rates[current_date.strftime('%Y-%m-%d')] = positive / len(day_feedback)
            else:
                daily_rates[current_date.strftime('%Y-%m-%d')] = 0
            
            current_date += timedelta(days=1)
        
        return daily_rates

    def clear_feedback(self):
        """Clear all feedback data"""
        self.feedback_data = []
        self.last_analysis_time = None
        logger.info("Feedback data cleared")

    def export_feedback(self, format: str = 'dict') -> Any:
        """Export feedback data in specified format"""
        if format == 'dict':
            return [
                {
                    'response': f['response'],
                    'feedback': f['feedback'],
                    'timestamp': f['timestamp'].isoformat(),
                    'metadata': f.get('metadata', {})
                }
                for f in self.feedback_data
            ]
        elif format == 'csv':
            import csv
            import io
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=['response', 'feedback', 'timestamp', 'metadata'])
            writer.writeheader()
            for f in self.feedback_data:
                writer.writerow({
                    'response': f['response'],
                    'feedback': f['feedback'],
                    'timestamp': f['timestamp'].isoformat(),
                    'metadata': str(f.get('metadata', {}))
                })
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def save_to_file(self, filepath: str):
        """Save feedback data to a file"""
        import json
        with open(filepath, 'w') as f:
            json.dump(self.export_feedback(), f, indent=2)

    def load_from_file(self, filepath: str):
        """Load feedback data from a file"""
        import json
        with open(filepath, 'r') as f:
            data = json.load(f)
            self.feedback_data = [
                {
                    'response': item['response'],
                    'feedback': item['feedback'],
                    'timestamp': datetime.fromisoformat(item['timestamp']),
                    'metadata': item.get('metadata', {})
                }
                for item in data
            ]
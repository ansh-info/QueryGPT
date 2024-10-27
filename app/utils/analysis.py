import logging
from datetime import datetime
from typing import Dict, List, Any
from collections import Counter

logger = logging.getLogger(__name__)

class AnalyticsManager:
    def __init__(self):
        self.queries = []
        self.feedback = []
        self.search_results = []
        self.session_data = []

    def track_query(self, query: str, user_id: str = None):
        """Track a new query"""
        self.queries.append({
            'query': query,
            'timestamp': datetime.now(),
            'user_id': user_id
        })

    def track_feedback(self, query: str, response: str, feedback_type: str, user_id: str = None):
        """Track user feedback"""
        self.feedback.append({
            'query': query,
            'response': response,
            'feedback_type': feedback_type,
            'timestamp': datetime.now(),
            'user_id': user_id
        })

    def track_search_result(self, query: str, results: List[Dict], user_id: str = None):
        """Track search results"""
        self.search_results.append({
            'query': query,
            'results_count': len(results),
            'average_score': sum(r['score'] for r in results) / len(results) if results else 0,
            'timestamp': datetime.now(),
            'user_id': user_id
        })

    def get_analytics(self) -> Dict[str, Any]:
        """Get comprehensive analytics"""
        try:
            return {
                'query_stats': self._analyze_queries(),
                'feedback_stats': self._analyze_feedback(),
                'search_stats': self._analyze_search_results(),
                'overall_stats': self._get_overall_stats()
            }
        except Exception as e:
            logger.error(f"Error generating analytics: {str(e)}")
            return {}

    def _analyze_queries(self) -> Dict[str, Any]:
        """Analyze query patterns"""
        if not self.queries:
            return {}

        query_texts = [q['query'] for q in self.queries]
        return {
            'total_queries': len(self.queries),
            'unique_queries': len(set(query_texts)),
            'popular_queries': Counter(query_texts).most_common(5),
            'queries_by_hour': self._group_by_hour(self.queries)
        }

    def _analyze_feedback(self) -> Dict[str, Any]:
        """Analyze feedback patterns"""
        if not self.feedback:
            return {}

        positive_feedback = sum(1 for f in self.feedback if f['feedback_type'] == 'positive')
        total_feedback = len(self.feedback)

        return {
            'total_feedback': total_feedback,
            'satisfaction_rate': positive_feedback / total_feedback if total_feedback > 0 else 0,
            'feedback_by_hour': self._group_by_hour(self.feedback),
            'recent_feedback': sorted(self.feedback, key=lambda x: x['timestamp'], reverse=True)[:5]
        }

    def _analyze_search_results(self) -> Dict[str, Any]:
        """Analyze search result patterns"""
        if not self.search_results:
            return {}

        return {
            'total_searches': len(self.search_results),
            'average_results': sum(r['results_count'] for r in self.search_results) / len(self.search_results),
            'average_score': sum(r['average_score'] for r in self.search_results) / len(self.search_results)
        }

    def _get_overall_stats(self) -> Dict[str, Any]:
        """Get overall system statistics"""
        return {
            'total_interactions': len(self.queries),
            'total_feedback': len(self.feedback),
            'total_searches': len(self.search_results),
            'start_date': min((q['timestamp'] for q in self.queries), default=datetime.now()),
            'last_interaction': max((q['timestamp'] for q in self.queries), default=datetime.now())
        }

    def _group_by_hour(self, items: List[Dict]) -> Dict[str, int]:
        """Group items by hour"""
        hours = {}
        for item in items:
            hour = item['timestamp'].strftime('%Y-%m-%d %H:00')
            hours[hour] = hours.get(hour, 0) + 1
        return dict(sorted(hours.items())[-24:])  # Last 24 hours

class SessionManager:
    def __init__(self):
        self.active_sessions = {}
        self.session_history = []

    def create_session(self, user_id: str):
        """Create a new session"""
        session_id = f"{user_id}_{datetime.now().timestamp()}"
        self.active_sessions[session_id] = {
            'user_id': user_id,
            'start_time': datetime.now(),
            'queries': [],
            'feedback': []
        }
        return session_id

    def end_session(self, session_id: str):
        """End a session and store its history"""
        if session_id in self.active_sessions:
            session = self.active_sessions.pop(session_id)
            session['end_time'] = datetime.now()
            self.session_history.append(session)

    def add_query_to_session(self, session_id: str, query: str, response: str):
        """Add a query to an active session"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['queries'].append({
                'query': query,
                'response': response,
                'timestamp': datetime.now()
            })

    def add_feedback_to_session(self, session_id: str, feedback_type: str):
        """Add feedback to an active session"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['feedback'].append({
                'type': feedback_type,
                'timestamp': datetime.now()
            })

    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        return {
            'active_sessions': len(self.active_sessions),
            'total_sessions': len(self.session_history),
            'average_session_duration': self._calculate_average_duration()
        }

    def _calculate_average_duration(self) -> float:
        """Calculate average session duration"""
        if not self.session_history:
            return 0
        
        durations = [
            (session['end_time'] - session['start_time']).total_seconds()
            for session in self.session_history
        ]
        return sum(durations) / len(durations)
import React, { useState, useRef } from 'react';
import axios from 'axios';
import { Search, X, Copy, Share2, ThumbsUp, ThumbsDown, ChevronUp, ChevronDown, Send } from 'lucide-react';

export default function App() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [conversation, setConversation] = useState([]);
  const [followUpQuery, setFollowUpQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [expandedResults, setExpandedResults] = useState({});
  const searchInputRef = useRef(null);
  const followUpInputRef = useRef(null);

  const handleSearch = async (e, isFollowUp = false) => {
    e.preventDefault();
    setIsLoading(true);
    const currentQuery = isFollowUp ? followUpQuery : query;
    try {
      const response = await axios.post('http://localhost:8000/search', { 
        text: currentQuery,
        conversation_history: conversation
      });
      setResults(response.data.search_results);
      const newResponse = response.data.ai_response;
      setConversation(prev => [...prev, { type: 'user', content: currentQuery }, { type: 'ai', content: newResponse }]);
      setExpandedResults({});
      if (isFollowUp) {
        setFollowUpQuery('');
      } else {
        setQuery('');
      }
    } catch (error) {
      console.error('Error during search:', error);
      setConversation(prev => [...prev, { type: 'error', content: 'An error occurred while processing your request. Please try again.' }]);
    }
    setIsLoading(false);
  };

  const clearSearch = () => {
    setQuery('');
    searchInputRef.current.focus();
  };

  const clearFollowUp = () => {
    setFollowUpQuery('');
    followUpInputRef.current.focus();
  };

  const toggleResultExpansion = (index) => {
    setExpandedResults(prev => ({ ...prev, [index]: !prev[index] }));
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    // You could add a toast notification here
  };

  const shareResult = (result) => {
    // Implement sharing functionality (e.g., open a share dialog)
    console.log('Sharing result:', result);
  };

  const provideFeedback = (isPositive) => {
    // Implement feedback functionality
    console.log('Feedback:', isPositive ? 'positive' : 'negative');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-100 to-indigo-200 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-5xl font-extrabold text-center text-indigo-700 mb-12">Knowledge Base Search</h1>
        <form onSubmit={(e) => handleSearch(e, false)} className="mb-12">
          <div className="relative flex items-center">
            <input
              ref={searchInputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your search query"
              className="w-full px-5 py-4 pr-12 text-lg rounded-full shadow-md focus:outline-none focus:ring-2 focus:ring-indigo-400 transition-all duration-300"
            />
            {query && (
              <button
                type="button"
                onClick={clearSearch}
                className="absolute right-14 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <X size={20} />
              </button>
            )}
            <button 
              type="submit" 
              className="absolute right-2 top-1/2 transform -translate-y-1/2 bg-indigo-500 hover:bg-indigo-600 text-white p-3 rounded-full transition-colors duration-200"
              disabled={isLoading}
            >
              {isLoading ? <div className="w-6 h-6 border-t-2 border-white border-solid rounded-full animate-spin"></div> : <Search size={24} />}
            </button>
          </div>
        </form>
        
        {conversation.length > 0 && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
            <h2 className="text-2xl font-bold mb-4 text-indigo-600">Conversation:</h2>
            {conversation.map((message, index) => (
              <div key={index} className={`mb-4 ${message.type === 'user' ? 'text-right' : ''}`}>
                <p className={`inline-block p-3 rounded-lg ${message.type === 'user' ? 'bg-indigo-100 text-indigo-800' : message.type === 'ai' ? 'bg-gray-100 text-gray-800' : 'bg-red-100 text-red-800'}`}>
                  {message.content}
                </p>
                {message.type === 'ai' && (
                  <div className="flex justify-end space-x-2 mt-2">
                    <button onClick={() => provideFeedback(true)} className="text-green-500 hover:text-green-600"><ThumbsUp size={20} /></button>
                    <button onClick={() => provideFeedback(false)} className="text-red-500 hover:text-red-600"><ThumbsDown size={20} /></button>
                  </div>
                )}
              </div>
            ))}
            <form onSubmit={(e) => handleSearch(e, true)} className="mt-6">
              <div className="relative flex items-center">
                <input
                  ref={followUpInputRef}
                  type="text"
                  value={followUpQuery}
                  onChange={(e) => setFollowUpQuery(e.target.value)}
                  placeholder="Ask a follow-up question"
                  className="w-full px-5 py-3 pr-12 text-lg rounded-full shadow-md focus:outline-none focus:ring-2 focus:ring-indigo-400 transition-all duration-300"
                />
                {followUpQuery && (
                  <button
                    type="button"
                    onClick={clearFollowUp}
                    className="absolute right-14 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    <X size={20} />
                  </button>
                )}
                <button 
                  type="submit" 
                  className="absolute right-2 top-1/2 transform -translate-y-1/2 bg-indigo-500 hover:bg-indigo-600 text-white p-2 rounded-full transition-colors duration-200"
                  disabled={isLoading}
                >
                  {isLoading ? <div className="w-5 h-5 border-t-2 border-white border-solid rounded-full animate-spin"></div> : <Send size={20} />}
                </button>
              </div>
            </form>
          </div>
        )}

        {results.length > 0 && (
          <div>
            <h2 className="text-2xl font-bold mb-6 text-indigo-600">Search Results:</h2>
            {results.map((result, index) => (
              <div key={index} className="bg-white rounded-lg shadow-md p-6 mb-6">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-bold text-xl text-indigo-500">Result {index + 1}</h3>
                  <div className="flex space-x-2">
                    <button onClick={() => copyToClipboard(result.content)} className="text-gray-500 hover:text-gray-700">
                      <Copy size={20} />
                    </button>
                    <button onClick={() => shareResult(result)} className="text-gray-500 hover:text-gray-700">
                      <Share2 size={20} />
                    </button>
                    <button onClick={() => toggleResultExpansion(index)} className="text-gray-500 hover:text-gray-700">
                      {expandedResults[index] ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                    </button>
                  </div>
                </div>
                <p className={`text-gray-700 ${expandedResults[index] ? '' : 'line-clamp-3'}`}>{result.content}</p>
                <p className="text-sm text-indigo-400 mt-2">Relevance Score: {result.score.toFixed(4)}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
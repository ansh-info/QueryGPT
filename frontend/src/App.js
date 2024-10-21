import React, { useState } from 'react';
import axios from 'axios';
import { Search, Loader } from 'lucide-react';

export default function App() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [aiResponse, setAiResponse] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSearch = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const response = await axios.post('http://localhost:8000/search', { text: query });
      setResults(response.data.search_results);
      setAiResponse(response.data.ai_response);
    } catch (error) {
      console.error('Error during search:', error);
      setAiResponse('An error occurred while processing your request. Please try again.');
    }
    setIsLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-100 to-indigo-200 py-12 px-4 sm:px-6 lg:px-8 font-sans">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-5xl font-extrabold text-center text-indigo-700 mb-12">Knowledge Base Search</h1>
        <form onSubmit={handleSearch} className="mb-12">
          <div className="relative flex items-center">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your search query"
              className="w-full px-5 py-4 pr-12 text-lg rounded-full shadow-md focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
            <button 
              type="submit" 
              className="absolute right-2 top-1/2 transform -translate-y-1/2 bg-indigo-500 hover:bg-indigo-600 text-white p-3 rounded-full transition-colors duration-200"
              disabled={isLoading}
            >
              {isLoading ? <Loader className="animate-spin" /> : <Search />}
            </button>
          </div>
        </form>
        
        {aiResponse && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-8 transform transition-all duration-300 ease-in-out hover:scale-102">
            <h2 className="text-2xl font-bold mb-4 text-indigo-600">AI Response:</h2>
            <p className="text-gray-700 text-lg leading-relaxed">{aiResponse}</p>
          </div>
        )}

        {results.length > 0 && (
          <div>
            <h2 className="text-2xl font-bold mb-6 text-indigo-600">Search Results:</h2>
            {results.map((result, index) => (
              <div key={index} className="bg-indigo-50 rounded-lg shadow-md p-6 mb-6 border border-indigo-100 transform transition-all duration-300 ease-in-out hover:scale-102">
                <h3 className="font-bold mb-3 text-xl text-indigo-500">Result {index + 1}</h3>
                <p className="text-gray-700 mb-4 text-lg">{result.content}</p>
                <p className="text-sm text-indigo-400">Relevance Score: {result.score.toFixed(4)}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
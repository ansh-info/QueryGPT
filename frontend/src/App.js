import React, { useState } from 'react';
import axios from 'axios';
import { Search, Loader, AlertCircle } from 'lucide-react';

export default function App() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [aiResponse, setAiResponse] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    try {
      const response = await axios.post('http://localhost:8000/search', { text: query });
      setResults(response.data.search_results);
      setAiResponse(response.data.ai_response);
    } catch (error) {
      console.error('Error during search:', error);
      setError('An error occurred while processing your request. Please try again.');
    }
    setIsLoading(false);
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto p-4">
        <h1 className="text-4xl font-bold mb-8 text-center text-blue-600">Knowledge Base Search</h1>
        <form onSubmit={handleSearch} className="mb-8">
          <div className="flex items-center border-b-2 border-blue-500 py-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your search query"
              className="appearance-none bg-transparent border-none w-full text-gray-700 mr-3 py-1 px-2 leading-tight focus:outline-none"
            />
            <button 
              type="submit" 
              className="flex-shrink-0 bg-blue-500 hover:bg-blue-700 border-blue-500 hover:border-blue-700 text-sm border-4 text-white py-1 px-2 rounded"
              disabled={isLoading}
            >
              {isLoading ? <Loader className="animate-spin" /> : <Search />}
            </button>
          </div>
        </form>
        
        {error && (
          <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded flex items-center">
            <AlertCircle className="mr-2" />
            <span>{error}</span>
          </div>
        )}

        {aiResponse && (
          <div className="mb-8">
            <h2 className="text-2xl font-bold mb-4 text-blue-600">AI Response:</h2>
            <div className="bg-white p-6 rounded-lg shadow-md">
              <p className="text-gray-800">{aiResponse}</p>
            </div>
          </div>
        )}

        {results.length > 0 && (
          <div>
            <h2 className="text-2xl font-bold mb-4 text-blue-600">Search Results:</h2>
            {results.map((result, index) => (
              <div key={index} className="mb-6 bg-white p-6 rounded-lg shadow-md">
                <h3 className="font-bold mb-2 text-lg text-blue-500">Result {index + 1}</h3>
                <p className="whitespace-pre-wrap text-gray-700">{result.content}</p>
                <p className="text-sm text-gray-500 mt-4">Relevance Score: {result.score.toFixed(4)}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
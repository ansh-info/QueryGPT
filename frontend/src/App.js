import React, { useState } from 'react';
import axios from 'axios';

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
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-4">Knowledge Base Search</h1>
      <form onSubmit={handleSearch} className="mb-4">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter your search query"
          className="w-full p-2 border rounded"
        />
        <button 
          type="submit" 
          className="mt-2 bg-blue-500 text-white p-2 rounded hover:bg-blue-600"
          disabled={isLoading}
        >
          {isLoading ? 'Searching...' : 'Search'}
        </button>
      </form>
      {aiResponse && (
        <div className="mb-4">
          <h2 className="text-2xl font-bold mb-2">AI Response:</h2>
          <p className="p-4 border rounded shadow">{aiResponse}</p>
        </div>
      )}
      {results.length > 0 && (
        <div className="mb-4">
          <h2 className="text-2xl font-bold mb-2">Search Results:</h2>
          {results.map((result, index) => (
            <div key={index} className="mb-4 p-4 border rounded shadow">
              <h3 className="font-bold mb-2">Result {index + 1}</h3>
              <p className="whitespace-pre-wrap">{result.content}</p>
              <p className="text-sm text-gray-500 mt-2">Score: {result.score.toFixed(4)}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
import React, { useState, useRef } from 'react';
import { Search, Send, Menu, X, Copy, Share2, ThumbsUp, ThumbsDown, ChevronDown, ChevronUp } from 'lucide-react';

export default function App() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [conversation, setConversation] = useState([]);
  const [chats, setChats] = useState([]);
  const [currentChatId, setCurrentChatId] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [expandedResults, setExpandedResults] = useState({});
  const searchInputRef = useRef(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      // Simulating API call
      const response = await new Promise(resolve => setTimeout(() => resolve({
        search_results: [
          { content: "SRH Hochschule Heidelberg: A private university with campuses in Heidelberg and Bad Homburg, Germany, offering a wide range of undergraduate and graduate degree programs in business, media, and social sciences. Located in the heart of Heidelberg, one of Germany's most beautiful cities Wide range of undergraduate and graduate degree programs.", score: 0.8586 },
          { content: "Another sample search result about SRH Hochschule Heidelberg.", score: 0.7524 }
        ],
        ai_response: "Based on the search results, here's what I can tell you about SRH Hochschule Heidelberg:\n\n1. It's a private university located in Germany.\n2. It has campuses in Heidelberg and Bad Homburg.\n3. The university offers a wide range of undergraduate and graduate degree programs.\n4. The main focus areas are business, media, and social sciences.\n5. It's situated in the heart of Heidelberg, which is considered one of Germany's most beautiful cities.\n\nThe university seems to provide a diverse educational experience in a picturesque setting. Is there anything specific you'd like to know more about, such as admission processes, specific programs, or student life?"
      }), 1000));
      
      setResults(response.search_results);
      const newResponse = response.ai_response;
      setConversation(prev => [...prev, { type: 'user', content: query }, { type: 'ai', content: newResponse }]);
      setExpandedResults({});
      setQuery('');

      if (!currentChatId) {
        const newChatId = Date.now();
        setCurrentChatId(newChatId);
        setChats(prev => [...prev, { id: newChatId, title: query }]);
      }
    } catch (error) {
      console.error('Error during search:', error);
      setConversation(prev => [...prev, { type: 'error', content: 'An error occurred while processing your request. Please try again.' }]);
    }
    setIsLoading(false);
  };

  const startNewChat = () => {
    setCurrentChatId(null);
    setConversation([]);
    setResults([]);
    setQuery('');
  };

  const selectChat = (chatId) => {
    setCurrentChatId(chatId);
    // Here you would load the conversation for the selected chat
    // This would typically involve a backend call to retrieve the chat history
    setConversation([]); // Placeholder: replace with actual chat loading logic
    setResults([]);
  };

  const toggleResultExpansion = (index) => {
    setExpandedResults(prev => ({ ...prev, [index]: !prev[index] }));
  };

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-50 w-64 bg-indigo-700 text-white transform ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'} transition-transform duration-300 ease-in-out md:relative md:translate-x-0`}>
        <div className="flex items-center justify-between p-4 border-b border-indigo-600">
          <h2 className="text-xl font-semibold">Chats</h2>
          <button onClick={() => setIsSidebarOpen(false)} className="md:hidden">
            <X size={24} />
          </button>
        </div>
        <div className="p-4">
          <button onClick={startNewChat} className="w-full px-4 py-2 text-indigo-700 bg-white rounded-md hover:bg-indigo-100 transition-colors duration-200">
            New Chat
          </button>
        </div>
        <div className="overflow-y-auto">
          {chats.map(chat => (
            <button
              key={chat.id}
              onClick={() => selectChat(chat.id)}
              className={`w-full p-4 text-left hover:bg-indigo-600 ${currentChatId === chat.id ? 'bg-indigo-600' : ''}`}
            >
              {chat.title}
            </button>
          ))}
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-white shadow-md p-4 flex items-center">
          <button onClick={() => setIsSidebarOpen(true)} className="mr-4 md:hidden">
            <Menu size={24} />
          </button>
          <h1 className="text-2xl font-bold text-indigo-700">Knowledge Base Search</h1>
        </header>

        <main className="flex-1 overflow-x-hidden overflow-y-auto bg-gray-50 p-4">
          {/* Conversation */}
          <div className="max-w-3xl mx-auto mb-8">
            {conversation.map((message, index) => (
              <div key={index} className={`mb-4 ${message.type === 'user' ? 'text-right' : ''}`}>
                <div className={`inline-block max-w-md p-4 rounded-lg ${
                  message.type === 'user' ? 'bg-indigo-100 text-indigo-800' : 
                  message.type === 'ai' ? 'bg-white text-gray-800 shadow' : 
                  'bg-red-100 text-red-800'
                }`}>
                  <p className="whitespace-pre-wrap">{message.content}</p>
                </div>
                {message.type === 'ai' && (
                  <div className="flex justify-end space-x-2 mt-2">
                    <button className="text-green-500 hover:text-green-600"><ThumbsUp size={20} /></button>
                    <button className="text-red-500 hover:text-red-600"><ThumbsDown size={20} /></button>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Search Results */}
          {results.length > 0 && (
            <div className="max-w-3xl mx-auto mb-8">
              <h2 className="text-xl font-semibold mb-4 text-indigo-700">Search Results:</h2>
              {results.map((result, index) => (
                <div key={index} className="bg-white rounded-lg shadow-md p-4 mb-4">
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-semibold text-lg text-indigo-600">Result {index + 1}</h3>
                    <div className="flex space-x-2">
                      <button className="text-gray-500 hover:text-gray-700"><Copy size={18} /></button>
                      <button className="text-gray-500 hover:text-gray-700"><Share2 size={18} /></button>
                      <button onClick={() => toggleResultExpansion(index)} className="text-gray-500 hover:text-gray-700">
                        {expandedResults[index] ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                      </button>
                    </div>
                  </div>
                  <p className={`text-gray-700 ${expandedResults[index] ? '' : 'line-clamp-3'}`}>{result.content}</p>
                  <p className="text-sm text-indigo-400 mt-2">Relevance Score: {result.score.toFixed(4)}</p>
                </div>
              ))}
            </div>
          )}
        </main>

        {/* Search Input */}
        <div className="bg-white border-t border-gray-200 p-4">
          <form onSubmit={handleSearch} className="max-w-3xl mx-auto">
            <div className="relative flex items-center">
              <input
                ref={searchInputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask a question..."
                className="w-full px-4 py-2 pr-10 text-gray-700 bg-gray-100 rounded-full focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:bg-white transition-all duration-300"
              />
              <button 
                type="submit" 
                className="absolute right-1 top-1/2 transform -translate-y-1/2 bg-indigo-600 text-white p-2 rounded-full hover:bg-indigo-700 transition-colors duration-200"
                disabled={isLoading}
              >
                {isLoading ? (
                  <div className="w-5 h-5 border-t-2 border-white border-solid rounded-full animate-spin"></div>
                ) : (
                  <Send size={20} />
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
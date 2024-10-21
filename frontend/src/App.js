import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Search, Send, Menu, X, Copy, Share2, ThumbsUp, ThumbsDown, ChevronDown, ChevronUp, Database, Globe } from 'lucide-react';

export default function App() {
  const [query, setQuery] = useState('');
  const [conversation, setConversation] = useState([]);
  const [chats, setChats] = useState([]);
  const [currentChatId, setCurrentChatId] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [expandedResults, setExpandedResults] = useState({});
  const searchInputRef = useRef(null);
  const chatContainerRef = useRef(null);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [conversation]);

  const handleSearch = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const response = await axios.post('http://localhost:8000/search', { text: query });
      const newMessage = {
        type: 'user',
        content: query,
      };
      const aiResponse = {
        type: 'ai',
        content: response.data.ai_response,
        isFromKnowledgeBase: response.data.is_from_knowledge_base,
        relevanceScore: response.data.relevance_score,
        searchResults: response.data.search_results,
      };
      setConversation(prev => [...prev, newMessage, aiResponse]);
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
    setQuery('');
  };

  const selectChat = (chatId) => {
    setCurrentChatId(chatId);
    // Here you would load the conversation for the selected chat
    // This would typically involve a backend call to retrieve the chat history
    setConversation([]); // Placeholder: replace with actual chat loading logic
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

        <main className="flex-1 overflow-x-hidden overflow-y-auto bg-gray-50 p-4" ref={chatContainerRef}>
          {/* Conversation */}
          <div className="max-w-3xl mx-auto space-y-4">
            {conversation.map((message, index) => (
              <div key={index} className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-md p-4 rounded-lg ${
                  message.type === 'user' ? 'bg-indigo-100 text-indigo-800' : 
                  message.type === 'ai' ? 'bg-white text-gray-800 shadow' : 
                  'bg-red-100 text-red-800'
                }`}>
                  {message.type === 'ai' && (
                    <div className="flex items-center mb-2">
                      {message.isFromKnowledgeBase ? <Database size={16} className="text-indigo-500 mr-2" /> : <Globe size={16} className="text-green-500 mr-2" />}
                      <span className="text-xs text-gray-500">
                        {message.isFromKnowledgeBase ? `Knowledge Base (Relevance: ${(message.relevanceScore * 100).toFixed(2)}%)` : 'General Knowledge'}
                      </span>
                    </div>
                  )}
                  <p className="whitespace-pre-wrap">{message.content}</p>
                  {message.type === 'ai' && message.searchResults && message.searchResults.length > 0 && (
                    <div className="mt-4">
                      <h4 className="font-semibold text-sm text-indigo-600 mb-2">Related Information:</h4>
                      {message.searchResults.map((result, idx) => (
                        <div key={idx} className="bg-gray-50 p-2 rounded mb-2">
                          <div className="flex justify-between items-start">
                            <p className="text-sm text-gray-600 line-clamp-2">{result.content}</p>
                            <button onClick={() => toggleResultExpansion(idx)} className="text-indigo-500 hover:text-indigo-600 ml-2">
                              {expandedResults[idx] ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                            </button>
                          </div>
                          {expandedResults[idx] && (
                            <div className="mt-2">
                              <p className="text-xs text-gray-500">Score: {result.score.toFixed(4)}</p>
                              {result.category && <p className="text-xs text-gray-500">Category: {result.category}</p>}
                              {result.source && <p className="text-xs text-gray-500">Source: {result.source}</p>}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                  {message.type === 'ai' && (
                    <div className="flex justify-end space-x-2 mt-2">
                      <button className="text-green-500 hover:text-green-600"><ThumbsUp size={16} /></button>
                      <button className="text-red-500 hover:text-red-600"><ThumbsDown size={16} /></button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
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
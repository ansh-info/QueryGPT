class QueryProcessor:
    def __init__(self):
        self.vectorizer = TfidfVectorizer()
    
    def process_query(self, query: str, qdrant_service, ollama_service):
        try:
            # Handle greetings (from original implementation)
            if query.lower() in ["hi", "hello", "hey"]:
                return {
                    "type": "ai",
                    "content": "Hello! How can I assist you with information about SRH Hochschule Heidelberg today?",
                    "is_from_knowledge_base": False,
                    "relevance_score": 0.0,
                    "search_results": []
                }

            # Handle knowledge base inquiries
            if query.lower() in ["what is in your knowledge base?", "what do you know?", "what information do you have?"]:
                summary = qdrant_service.get_knowledge_base_summary()
                return {
                    "type": "ai",
                    "content": summary,
                    "is_from_knowledge_base": True,
                    "relevance_score": 1.0,
                    "search_results": [],
                    "metadata": {
                        "type": "summary",
                        "timestamp": datetime.now().isoformat()
                    }
                }

            # Process regular queries with enhanced preprocessing
            preprocessed_query = self.preprocess_query(query)
            expanded_queries = self.expand_query(preprocessed_query)
            
            # Check query relevance
            is_relevant, relevance_score = self.is_query_relevant(
                preprocessed_query, 
                qdrant_service.get_keywords()
            )

            if is_relevant:
                all_results = []
                for expanded_query in expanded_queries:
                    query_vector = ollama_service.get_embedding(expanded_query)
                    if query_vector:
                        search_results = qdrant_service.search(
                            query_vector,
                            limit=5  # Original limit
                        )
                        all_results.extend(search_results)

                # Process and deduplicate results
                results = []
                seen_contents = set()
                for result in all_results:
                    content = result.payload.get('original_content', '')
                    if content and content not in seen_contents:
                        seen_contents.add(content)
                        results.append({
                            "content": content,
                            "score": result.score,
                            "category": result.payload.get('category'),
                            "source": result.payload.get('source'),
                            "metadata": result.payload.get('metadata', {}),
                            "timestamp": result.payload.get('timestamp')
                        })

                # Sort by relevance and limit
                results.sort(key=lambda x: x['score'], reverse=True)
                results = results[:5]

                # Generate context-aware response
                context = "\n\n".join([r["content"] for r in results])
                prompt = self.generate_enhanced_prompt(query, context, True)
                ai_response = ollama_service.generate_response(prompt)

                return {
                    "type": "ai",
                    "content": ai_response,
                    "is_from_knowledge_base": True,
                    "relevance_score": relevance_score,
                    "search_results": results,
                    "search_info": f"Found {len(results)} relevant results",
                    "metadata": {
                        "query_expansion": expanded_queries,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            else:
                # Handle non-relevant queries
                prompt = self.generate_enhanced_prompt(query, "", False)
                ai_response = ollama_service.generate_response(prompt)
                
                return {
                    "type": "ai",
                    "content": ai_response,
                    "is_from_knowledge_base": False,
                    "relevance_score": relevance_score,
                    "search_results": [],
                    "search_info": "No relevant results found in knowledge base",
                    "metadata": {
                        "timestamp": datetime.now().isoformat()
                    }
                }

        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                "type": "error",
                "content": "An error occurred while processing your request. Please try again."
            }

    def preprocess_query(self, query: str) -> str:
        """Enhanced query preprocessing"""
        query = query.lower().strip()
        query = re.sub(r'\s+', ' ', query)  # Normalize whitespace
        query = re.sub(r'[^\w\s]', '', query)  # Remove special characters
        return query

    def expand_query(self, query: str) -> List[str]:
        """Enhanced query expansion"""
        expanded = [query]
        
        # Handle abbreviations and variations
        replacements = {
            "srh": "srh hochschule heidelberg",
            "uni": "university",
            "cs": "computer science",
            "ai": "artificial intelligence",
            "ml": "machine learning",
            "db": "database"
        }
        
        for old, new in replacements.items():
            if old in query:
                expanded.append(query.replace(old, new))
        
        return list(set(expanded))

    def generate_enhanced_prompt(self, query: str, context: str, is_relevant: bool) -> str:
        if is_relevant:
            return f"""Based on the following context from the knowledge base, provide a detailed answer to the question.
If the context doesn't fully address the question, supplement with relevant general knowledge.

Context:
{context}

Question: {query}

Please provide:
1. A direct answer to the question
2. Any relevant additional information
3. Related topics or suggestions
4. Sources of information when available

Answer:"""
        else:
            return f"""You are an AI assistant for SRH Hochschule Heidelberg. The following question was not found in our knowledge base.
Please provide a general answer while noting that for specific, up-to-date details, the user should consult official sources.

Question: {query}

Please provide:
1. A general answer based on available information
2. A note about consulting official sources for specific details
3. Any relevant suggestions or related topics

Answer:"""
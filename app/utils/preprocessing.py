from typing import List
import re

def preprocess_query(query: str) -> str:
    """Clean and normalize the query text"""
    # Convert to lowercase
    query = query.lower()
    
    # Remove extra whitespace
    query = re.sub(r'\s+', ' ', query).strip()
    
    # Remove special characters
    query = re.sub(r'[^\w\s]', '', query)
    
    return query

def expand_query(query: str) -> List[str]:
    """Generate variations of the query for better search results"""
    expanded = [query]
    
    # Handle common abbreviations
    if "srh" in query:
        expanded.append(query.replace("srh", "srh hochschule heidelberg"))
    
    # Add common variations
    if "uni" in query:
        expanded.append(query.replace("uni", "university"))
    if "cs" in query:
        expanded.append(query.replace("cs", "computer science"))
    
    return expanded

def clean_text(text: str) -> str:
    """Clean and normalize any text content"""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove special characters
    text = re.sub(r'[^\w\s.,!?-]', '', text)
    
    return text
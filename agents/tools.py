# tools.py
from langchain_core.tools import tool
from db.vector_store import DatabaseManager
from integrations.web_search import TavilyWebSearch
from typing import List, Optional, Dict # Make sure Dict is imported

db_manager = DatabaseManager()

try:
    web_searcher = TavilyWebSearch()
    WEB_SEARCH_AVAILABLE = True
except ValueError as e:
    print(f"--- [WEB SEARCH TOOL ERROR] ---")
    print(f"Description: The web search tool could not be initialized.")
    print(f"Error: {e}")
    print(f"Troubleshooting: Please ensure the TAVILY_API_KEY is set in your .env file.")
    print(f"---------------------------------")
    web_searcher = None
    WEB_SEARCH_AVAILABLE = False

@tool
async def search_knowledge_base(query: str, agent_type: Optional[str] = None, k: int = 5) -> List[dict]:
    """Search the knowledge base for cybersecurity information.
    
    Args:
        query: The search query
        agent_type: Optional agent type to filter results (incident_response, threat_intelligence, prevention)
        k: Number of results to return (default: 5)
    """
    results = await db_manager.asearch(query, agent_type=agent_type, k=k)
    return results

@tool
async def web_search(query: str, agent_type: Optional[str] = None) -> List[Dict]:
    """Perform a web search for cybersecurity information. Returns a list of result dictionaries."""
    if not WEB_SEARCH_AVAILABLE or not web_searcher:
        return [{"error": "Web search is not available. Check TAVILY_API_KEY."}]
    
    try:
        print("DEBUG - Performing web search with query:", query)
        result = await web_searcher.search(query, agent_type)
        print(f"DEBUG - Web Search found {len(result)} results.")
        return result
    except Exception as e:
        import traceback
        error_details = f"Web search tool failed: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_details)
        return [{"error": f"Web search tool failed: {str(e)}"}]
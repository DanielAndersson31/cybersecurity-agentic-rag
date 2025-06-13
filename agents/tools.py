# tools.py
from langchain_core.tools import tool
from db.vector_store import DatabaseManager
from integrations.web_search import TavilyWebSearch
from typing import List, Optional

db_manager = DatabaseManager()

try:
    web_searcher = TavilyWebSearch()
    WEB_SEARCH_AVAILABLE = True
except ValueError as e:
    print(f"Web search tool initialization failed: {e}")
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
async def web_search(query: str, agent_type: Optional[str] = None) -> str:
    """Perform a web search for cybersecurity information.
    
    Args:
        query: The search query
        agent_type: Optional agent type to enhance the query (incident_response, threat_intelligence, prevention)
    """
    if not WEB_SEARCH_AVAILABLE or not web_searcher:
        return "Web search is not available. Please check your TAVILY_API_KEY environment variable."
    
    try:
        # Directly call the async search method
        result = await web_searcher.search(query, agent_type)
        return result
    except Exception as e:
        import traceback
        error_details = f"Web search failed: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_details)  # Log the full error for debugging
        return f"Web search failed: {str(e)}"
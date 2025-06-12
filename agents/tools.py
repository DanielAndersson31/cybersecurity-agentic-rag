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
async def search_incident_response_knowledge(query:str, k:int=5) -> List[dict]:
    """Search for incident response related documents."""
    results = await db_manager.asearch(query, agent_type="incident_response", k=k) # Assuming db_manager has asearch
    return results

@tool
async def search_threat_intelligence_knowledge(query: str, k: int = 5) -> List[dict]:
    """Search for threat intelligence related documents."""
    results = await db_manager.asearch(query, agent_type="threat_intelligence", k=k) # Assuming db_manager has asearch
    return results

@tool
async def search_prevention_knowledge(query: str, k: int = 5) -> List[dict]:
    """Search for prevention related documents."""
    results = await db_manager.asearch(query, agent_type="prevention", k=k) # Assuming db_manager has asearch
    return results

@tool
async def search_all_knowledge(query: str, k: int = 5) -> List[dict]:
    """Search for all knowledge documents across all agent types."""
    results = await db_manager.asearch(query, k=k) # Assuming db_manager has asearch
    return results

# Optional: If you use web search, ensure it's also async
@tool
async def web_search(query: str) -> str:
    """Perform a web search."""
    if WEB_SEARCH_AVAILABLE and web_searcher:
        return await web_searcher.ainvoke({"query": query})
    return "Web search is not available."
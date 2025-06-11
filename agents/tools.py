from langchain_core.tools import tool
from database.vector_store import DatabaseManager
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
def search_incident_response_knowledge(query:str, k:int=5) -> List[dict]:
    """Search for incident response related documents."""
    results = db_manager.search(query, agent_type="incident_response", k=k)
    return results

@tool
def search_threat_intelligence_knowledge(query: str, k: int = 5) -> List[dict]:
    """Search for threat intelligence related documents."""
    results = db_manager.search(query, agent_type="threat_intelligence", k=k)
    return results

@tool
def search_prevention_knowledge(query: str, k: int = 5) -> List[dict]:
    """Search for prevention related documents."""
    results = db_manager.search(query, agent_type="prevention", k=k)
    return results

@tool
def search_all_knowledge(query: str, k: int = 5) -> List[dict]:
    """Search for all knowledge documents across all agent types."""
    results = db_manager.search(query, k=k)
    return results
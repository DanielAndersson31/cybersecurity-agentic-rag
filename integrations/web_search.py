from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from typing import List, Dict, Optional
import os

class TavilyWebSearch:
    def __init__(self):
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        
        if not self.tavily_api_key:
            raise ValueError("TAVILY_API_KEY environment variable is not set.")
        
        self._basic_tool = self._create_search_tool(advanced=False)
        self._advanced_tool = self._create_search_tool(advanced=True)
        
    
    def search(self, query: str, agent_type: Optional[str] = None, advanced: bool = False) -> str:
        """Search the web using Tavily and return formatted results."""
        
        enhanced_query = self._enchaned_query(query, agent_type)
        tool = self._advanced_tool if advanced else self._basic_tool
        
        try:
            return tool.invoke({"query": enhanced_query})
        except Exception as e:
            return f"Web search failed: {str(e)}"
        
    def should_search(self, confidence: float, num_docs: int) -> bool:
        """Determine whether to perform a web search based on confidence and number of documents."""
        return confidence < 0.6 or num_docs < 3
    
    def _create_search_tool(self, advanced: bool) -> TavilySearch:
        """Create a configred tavily search tool"""
        return TavilySearch(
            max_results= 8 if advanced else 4,
            search_depth = "advanced" if advanced else "basic",
            include_answer=True, 
            include_raw_content= advanced,
            include_domains=[
                "nist.gov", "cisa.gov", "sans.org", "mitre.org",
                "owasp.org", "cisecurity.org", "us-cert.gov",
                "nvd.nist.gov", "attack.mitre.org"
            ] + (["schneier.com", "krebsonsecurity.com"] if advanced else [])
        )
    def _enchance_query(self, query:str , agent_type: Optional[str]) -> str:
        """Enhance the query based on the agent type."""
        enhancements = {
            "incident_response": "cybersecurity incident response",
            "threat_intelligence": "threat intelligence IOC analysis", 
            "prevention": "cybersecurity framework prevention",
        }
        prefix = enhancements.get(agent_type, "cybersecurity")
        return f"{prefix} {query}"
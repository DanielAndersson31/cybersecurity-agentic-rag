from langchain_tavily import TavilySearch
from typing import Optional, List, Dict # Make sure List and Dict are imported
from dotenv import load_dotenv
import os

load_dotenv()

class TavilyWebSearch:
    def __init__(self):
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not self.tavily_api_key:
            raise ValueError("TAVILY_API_KEY environment variable is not set.")
        
        self.search_tool = TavilySearch(
            api_key=self.tavily_api_key,
            include_answer=True,
            include_raw_content=True,
            max_results=5 # Increased to 5 to match the original slicing
        )
        
        self.trusted_domains = [
            "nist.gov", "cisa.gov", "sans.org", "mitre.org",
            "owasp.org", "cisecurity.org", "us-cert.gov",
            "nvd.nist.gov", "attack.mitre.org", "schneier.com",
            "krebsonsecurity.com"
        ]
        
    # web_search.py

# ... (imports and class definition are the same)

    # web_search.py -> The final, corrected search method

    async def search(self, query: str, agent_type: Optional[str] = None) -> List[Dict]:
        """Search the web using Tavily and return a list of structured results."""
        try:
            search_params = {"query": query, "search_depth": "advanced"}
            
            # This returns a dictionary, e.g., {'query': ..., 'results': [...]}
            response_dict = await self.search_tool.ainvoke(search_params)
            
            # --- START OF THE FINAL FIX ---
            # Extract the list of documents from the 'results' key.
            search_documents = response_dict.get('results', [])
            # --- END OF THE FINAL FIX ---

            if not search_documents:
                return []
            
            # Now, process the 'search_documents' list as intended.
            processed_results = []
            for result in search_documents:
                if isinstance(result, dict):
                    is_trusted = any(domain in result.get('url', '') for domain in self.trusted_domains)
                    result['is_trusted'] = is_trusted
                    result['source'] = 'web_search'
                    processed_results.append(result)
            
            processed_results.sort(key=lambda r: r.get('is_trusted', False), reverse=True)
            
            return processed_results
            
        except Exception as e:
            import traceback
            print(f"CRITICAL ERROR during Tavily search: {e}\n{traceback.format_exc()}")
            return []

    def _is_security_query(self, query: str) -> bool:
        """Check if query is security-related."""
        security_keywords = [
            "vulnerability", "exploit", "malware", "cybersecurity", "threat",
            "incident", "breach", "attack", "security", "CVE", "IOC",
            "ransomware", "phishing", "firewall", "encryption", "authentication",
            "penetration", "pentest", "red team", "blue team", "soc", "siem"
        ]
        return any(keyword in query.lower() for keyword in security_keywords)
        
    def _trim_messages(self, messages: list, max_tokens: int = 100000) -> list:
        """Trim messages to stay within token limits."""
        total_chars = sum(len(str(msg.content)) for msg in messages)
        estimated_tokens = total_chars // 4
        
        if estimated_tokens <= max_tokens:
            return messages
        
        if len(messages) <= 2:
            return messages
        
        trimmed = [messages[0]]
        
        recent_chars = 0
        target_chars = max_tokens * 4 * 0.8
        
        for msg in reversed(messages[1:]):
            msg_chars = len(str(msg.content))
            if recent_chars + msg_chars < target_chars:
                recent_chars += msg_chars
                trimmed.insert(1, msg)
            else:
                break
        
        return trimmed
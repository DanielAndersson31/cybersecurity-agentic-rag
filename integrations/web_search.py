from langchain_tavily import TavilySearch
from typing import Optional
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

class TavilyWebSearch:
    def __init__(self):
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not self.tavily_api_key:
            raise ValueError("TAVILY_API_KEY environment variable is not set.")
        
        # Initialize the search tool once
        self.search_tool = TavilySearch(
            api_key=self.tavily_api_key,
            include_answer=True,
            include_raw_content=True, # Always get raw content for RAG
            max_results=7 # A good default number of results
        )
        
        self.trusted_domains = [
            "nist.gov", "cisa.gov", "sans.org", "mitre.org",
            "owasp.org", "cisecurity.org", "us-cert.gov",
            "nvd.nist.gov", "attack.mitre.org", "schneier.com",
            "krebsonsecurity.com"
        ]
        
    async def search(self, query: str, agent_type: Optional[str] = None) -> str:
        """Search the web using Tavily and return formatted results with raw content."""
        enhanced_query = self._enhanced_query(query, agent_type)
        
        try:
            # Prepare search parameters
            search_params = {
                "query": enhanced_query,
                "search_depth": "advanced" # Advanced is better for in-depth answers
            }
            
            # Add trusted domains for security queries
            if self._is_security_query(query):
                search_params["include_domains"] = self.trusted_domains
            
            # Perform the search
            results = await self.search_tool.ainvoke(search_params)
            
            if not results or not results.get('results'):
                return "No relevant results found."

            # Format the results using the included raw content
            return self._format_results(results['results'])
            
        except Exception as e:
            return f"Web search failed: {str(e)}"
    
    def _format_results(self, results: list) -> str:
        """Format search results, prioritizing raw_content and marking trusted sources."""
        if not results:
            return "No results found."
        
        formatted_parts = []
        
        # Limit to first 3 results to reduce token usage
        limited_results = results[:3]
        
        # Reorder results to prioritize trusted domains first
        limited_results.sort(key=lambda r: any(domain in r.get('url', '') for domain in self.trusted_domains), reverse=True)
        
        for i, result in enumerate(limited_results, 1):
            title = result.get('title', 'No Title')
            url = result.get('url', '')
            # Limit content to first 500 characters to reduce tokens
            content = result.get('raw_content', result.get('content', 'No content available.'))
            content = content[:500] + "..." if len(content) > 500 else content
            
            is_trusted = any(domain in url for domain in self.trusted_domains)
            trust_mark = "🔐 " if is_trusted else ""
            
            formatted_parts.append(f"**{trust_mark}Result {i}: {title}**")
            formatted_parts.append(f"Source: {url}")
            formatted_parts.append(content)
            formatted_parts.append("-" * 20)
        
        return "\n".join(formatted_parts)
    
    def _is_security_query(self, query: str) -> bool:
        """Check if query is security-related."""
        security_keywords = [
            "vulnerability", "exploit", "malware", "cybersecurity", "threat",
            "incident", "breach", "attack", "security", "CVE", "IOC"
        ]
        return any(keyword in query.lower() for keyword in security_keywords)
    
    def _enhanced_query(self, query: str, agent_type: Optional[str] = None) -> str:
        """Enhance the query based on the agent type."""
        enhancements = {
            "incident_response": "cybersecurity incident response",
            "threat_intelligence": "threat intelligence IOC analysis",
            "prevention": "cybersecurity framework prevention",
        }
        
        prefix = enhancements.get(agent_type, "cybersecurity")
        # Avoid adding prefix if query is already specific
        if "cybersecurity" in query.lower() or "cve" in query.lower():
            return query
            
        return f"{prefix} {query}"
    def _trim_messages(self, messages: list, max_tokens: int = 100000) -> list:
        """Trim messages to stay within token limits."""
        # Rough estimation: 1 token ≈ 4 characters
        total_chars = sum(len(str(msg.content)) for msg in messages)
        estimated_tokens = total_chars // 4
        
        if estimated_tokens <= max_tokens:
            return messages
        
        # Keep system message (first) and recent messages
        if len(messages) <= 2:
            return messages
        
        # Keep first message (system) and trim from the middle
        trimmed = [messages[0]]  # Keep system message
        
        # Calculate how many recent messages to keep
        recent_chars = 0
        target_chars = max_tokens * 4 * 0.8  # Use 80% of limit
        
        for msg in reversed(messages[1:]):
            msg_chars = len(str(msg.content))
            if recent_chars + msg_chars < target_chars:
                recent_chars += msg_chars
                trimmed.insert(1, msg)  # Insert after system message
            else:
                break
        
        return trimmed
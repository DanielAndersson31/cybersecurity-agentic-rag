import pytest
import os
import asyncio
from dotenv import load_dotenv

# Make sure the root of the project is in the python path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from integrations.web_search import TavilyWebSearch

# Load environment variables from .env file
load_dotenv()

@pytest.fixture(scope="module")
def web_search_tool():
    """Fixture to create a TavilyWebSearch instance."""
    if not os.getenv("TAVILY_API_KEY"):
        pytest.skip("TAVILY_API_KEY is not set, skipping web search tests.")
    return TavilyWebSearch()

@pytest.mark.asyncio
async def test_general_query(web_search_tool):
    """Test a general, non-cybersecurity query."""
    print("\n--- Testing General Query ---")
    query = "what is the current time in New York"
    print(f"Query: {query}")
    
    results = await web_search_tool.search(query)
    
    print("Results:")
    print(results)
    
    assert results is not None
    assert isinstance(results, str)
    assert "No relevant results found" not in results
    assert "Web search failed" not in results
    # General queries should not have the trusted source lock icon
    assert "🔐" not in results

@pytest.mark.asyncio
async def test_cybersecurity_query(web_search_tool):
    """Test a cybersecurity-specific query."""
    print("\n--- Testing Cybersecurity Query ---")
    query = "latest vulnerability in Apache Struts"
    print(f"Query: {query}")
    
    results = await web_search_tool.search(query, agent_type="vulnerability_analyst")
    
    print("Results:")
    print(results)
    
    assert results is not None
    assert isinstance(results, str)
    assert "No relevant results found" not in results
    assert "Web search failed" not in results
    # We expect some results to come from trusted sources, but it's not guaranteed
    # for every query. A soft check is to see if the formatting is present.
    assert "Source:" in results

@pytest.mark.asyncio
async def test_security_query_detection(web_search_tool):
    """Test that security queries are properly detected and use trusted domains."""
    print("\n--- Testing Security Query Detection ---")
    query = "CVE-2023-12345 vulnerability details"
    print(f"Query: {query}")
    
    # Test the internal method
    is_security = web_search_tool._is_security_query(query)
    assert is_security == True
    
    results = await web_search_tool.search(query)
    
    print("Results:")
    print(results)
    
    assert results is not None
    assert isinstance(results, str)
    assert "No relevant results found" not in results
    assert "Web search failed" not in results

@pytest.mark.asyncio
async def test_query_enhancement(web_search_tool):
    """Test query enhancement for different agent types."""
    print("\n--- Testing Query Enhancement ---")
    
    # Test with incident response agent
    enhanced = web_search_tool._enhanced_query("malware analysis", "incident_response")
    print(f"Enhanced query for incident_response: {enhanced}")
    assert "cybersecurity incident response" in enhanced
    
    # Test with general query (should not add cybersecurity prefix if already present)
    enhanced = web_search_tool._enhanced_query("cybersecurity best practices", "prevention")
    print(f"Enhanced query with existing cybersecurity: {enhanced}")
    assert enhanced == "cybersecurity best practices"  # Should not double-prefix

@pytest.mark.asyncio
async def test_no_api_key():
    """Test that the tool raises an error if the API key is missing."""
    # Temporarily unset the API key
    original_key = os.environ.pop("TAVILY_API_KEY", None)
    
    with pytest.raises(ValueError, match="TAVILY_API_KEY environment variable is not set"):
        TavilyWebSearch()
        
    # Restore the API key
    if original_key:
        os.environ["TAVILY_API_KEY"] = original_key

# To run this test:
# 1. Make sure you have pytest and pytest-asyncio installed:
#    pip install pytest pytest-asyncio
# 2. Make sure your .env file has TAVILY_API_KEY set.
# 3. Run from the root directory:
#    pytest tests/test_web_search.py -s -v 
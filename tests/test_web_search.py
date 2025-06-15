import asyncio
import json
from agents.workflow import CybersecurityRAGWorkflow
from langchain_core.messages import HumanMessage

async def test_web_search_integration():
    """Test the web search integration with various queries."""
    
    workflow = CybersecurityRAGWorkflow(llm_choice="openai_mini")
    await workflow.initialize()
    
    test_queries = [
        {
            "query": "What is the latest CVE-2024 vulnerability?",
            "expected_behavior": "Cybersecurity query + needs web search for latest info",
            "expected_cyber": True,
            "expected_web_search": True,
            "expected_kb_search": True
        },
        {
            "query": "What is SQL injection?",
            "expected_behavior": "Cybersecurity query but doesn't need web search (general concept)",
            "expected_cyber": True,
            "expected_web_search": False,
            "expected_kb_search": True
        },
        {
            "query": "What time is it in London?",
            "expected_behavior": "Non-cyber query that needs web search",
            "expected_cyber": False,
            "expected_web_search": True,
            "expected_kb_search": False
        },
        {
            "query": "How do I make a paper airplane?",
            "expected_behavior": "Non-cyber query that doesn't need web search",
            "expected_cyber": False,
            "expected_web_search": False,
            "expected_kb_search": False
        },
        {
            "query": "Recent ransomware attacks in 2024",
            "expected_behavior": "Cybersecurity query needing current info",
            "expected_cyber": True,
            "expected_web_search": True,
            "expected_kb_search": True
        },
        {
            "query": "Explain the principle of least privilege",
            "expected_behavior": "Cybersecurity concept that doesn't need current info",
            "expected_cyber": True,
            "expected_web_search": False,
            "expected_kb_search": True
        },
        {
            "query": "What's the current weather in New York?",
            "expected_behavior": "Non-cyber query needing current info",
            "expected_cyber": False,
            "expected_web_search": True,
            "expected_kb_search": False
        },
        {
            "query": "Latest zero-day exploits",
            "expected_behavior": "Cybersecurity query about recent threats",
            "expected_cyber": True,
            "expected_web_search": True,
            "expected_kb_search": True
        }
    ]
    
    for test_case in test_queries:
        print("\n" + "="*80)
        print(f"Testing Query: {test_case['query']}")
        print(f"Expected Behavior: {test_case['expected_behavior']}")
        print(f"Expected - Cyber: {test_case['expected_cyber']}, Web Search: {test_case['expected_web_search']}, KB Search: {test_case['expected_kb_search']}")
        print("="*80)
        
        try:
            result = await workflow.process_query_async(
                test_case['query'],
                client_config={"preferred_llm_choice": "openai_mini"}
            )
            
            print("\n--- RESULTS ---")
            print(f"Agent Type: {result.get('agent_type')}")
            print(f"Confidence Score: {result.get('confidence_score')}")
            print(f"Number of Docs Retrieved: {result.get('num_docs_retrieved')}")
            
            print("\n--- ANALYSIS ---")
            
            response_text = result.get('response', '')
            web_indicators = ["http", "www", "Source:", "Web Source:", "according to", "🔐"]
            kb_indicators = ["knowledge base", "based on established", "according to best practices"]
            
            web_search_used = any(indicator in response_text for indicator in web_indicators)
            kb_search_likely = result.get('num_docs_retrieved', 0) > 0 and not all(indicator in response_text for indicator in web_indicators)
            
            is_cyber_response = any(term in response_text.lower() for term in ["security", "vulnerability", "attack", "threat", "cyber", "exploit"])
            
            print(f"Appears to be cyber-related response: {is_cyber_response}")
            print(f"Web search indicators found: {web_search_used}")
            print(f"KB search likely used: {kb_search_likely}")
            
            print("\n--- VALIDATION ---")
            cyber_match = is_cyber_response == test_case['expected_cyber']
            web_match = web_search_used == test_case['expected_web_search']
            
            print(f"Cyber classification: {'✓ PASS' if cyber_match else '✗ FAIL'}")
            print(f"Web search usage: {'✓ PASS' if web_match else '✗ FAIL'}")
            
            if not cyber_match or not web_match:
                print("\n⚠️  WARNING: Behavior doesn't match expectations!")
            
            response_snippet = response_text[:300]
            print(f"\nResponse Snippet:\n{response_snippet}...")
            
        except Exception as e:
            print(f"\nERROR: {str(e)}")
            import traceback
            traceback.print_exc()
    
    await workflow.close()
    print("\n\nDebug test completed!")

async def inspect_state_details():
    """Deep inspection of state to see how the query flows through the system."""
    workflow = CybersecurityRAGWorkflow(llm_choice="openai_mini")
    await workflow.initialize()
    
    test_queries = [
        "What are the latest cybersecurity threats in 2024?",
        "What time is it in Tokyo?",
        "Explain firewall rules"
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Deep State Inspection for: {query}")
        print("="*80)
        
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "agent_type": None,
            "retrieved_docs": [],
            "confidence_score": 0.0,
            "needs_routing": True,
            "thread_id": f"debug-thread-{query[:20]}",
            "is_follow_up": False,
            "preferred_agent": None,
            "llm_choice": "openai_mini",
            "collaboration_mode": "single_agent",
            "consulting_agents": [],
            "agent_responses": {},
            "needs_collaboration": False,
            "primary_agent": None,
            "collaboration_confidence": None,
            "thought_process": [],
            "needs_web_search": False,
            "conversation_summary": ""
        }
        
        config = {
            "configurable": {"thread_id": initial_state["thread_id"]},
            "preferred_llm_choice": "openai_mini"
        }
        
        await workflow.app.ainvoke(initial_state, config=config)
        
        final_state = await workflow.app.aget_state(config)
        state_values = final_state.values
        
        print("\n--- THOUGHT PROCESS ---")
        for thought in state_values.get("thought_process", []):
            print(f"  • {thought}")
        
        print("\n--- RETRIEVED DOCUMENTS ---")
        web_docs = [d for d in state_values.get("retrieved_docs", []) if d.get("source") == "web_search"]
        kb_docs = [d for d in state_values.get("retrieved_docs", []) if d.get("source") != "web_search"]
        
        print(f"Web Search Documents: {len(web_docs)}")
        print(f"Knowledge Base Documents: {len(kb_docs)}")
        
        if web_docs:
            print("\nWeb Sources:")
            for doc in web_docs[:3]:
                print(f"  - {doc.get('title', 'No title')} ({doc.get('url', 'No URL')})")
                
        if kb_docs:
            print("\nKB Sources:")
            for doc in kb_docs[:3]:
                print(f"  - {doc.get('content', 'No content')[:100]}...")
    
    await workflow.close()

if __name__ == "__main__":
    print("Starting Web Search Integration Tests...")
    asyncio.run(test_web_search_integration())
    # asyncio.run(inspect_state_details())
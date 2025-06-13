# agents/specialized_agents.py
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.memory import ConversationSummaryBufferMemory
from .state import AgentState
from .tools import search_knowledge_base, web_search

class BaseAgent:
    """Base class for specialized cybersecurity agents."""

    def __init__(self, agent_type: str, system_prompt: str):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        self.tools = [search_knowledge_base, web_search]
        self.agent_type = agent_type
        self.system_prompt = system_prompt
        
        # Add memory management
        self.memory = ConversationSummaryBufferMemory(
            llm=self.llm,
            max_token_limit=80000,  # Leave room for other content
            return_messages=True,
            summary_prompt=f"Summarize this cybersecurity conversation, focusing on {agent_type} context and key decisions."
        )
        
        # Keywords that should trigger web search regardless of confidence
        self.web_search_keywords = {
            "incident_response": [
                "latest", "recent", "new", "emerging", "current", "today", "now",
                "zero-day", "zero day", "0day", "exploit", "vulnerability", "cve",
                "ransomware", "malware", "breach", "attack", "incident", "alert"
            ],
            "threat_intelligence": [
                "latest", "recent", "new", "emerging", "current", "today", "now",
                "apt", "threat actor", "group", "campaign", "ioc", "ttp", "tactic",
                "technique", "procedure", "malware", "ransomware", "exploit"
            ],
            "prevention": [
                "latest", "recent", "new", "emerging", "current", "today", "now",
                "framework", "standard", "compliance", "regulation", "policy",
                "best practice", "guideline", "recommendation", "security control"
            ]
        }

    async def process_async(self, state: AgentState) -> AgentState:
        """Processes a query and updates the agent state."""
        current_user_query = ""
        
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                current_user_query = msg.content
                break
        
        # First try knowledge base search
        all_docs = await search_knowledge_base.ainvoke({
            "query": current_user_query,
            "agent_type": self.agent_type
        })
        
        # Let the LLM determine if we need web search
        search_decision_prompt = f"""You are an expert at determining if a query requires real-time information from a web search.
Analyze the user's query and decide if it's necessary to perform a web search to provide an accurate and up-to-date answer.
**User Query:** "{current_user_query}"
**Knowledge Base Results:** Found {len(all_docs)} documents.
Based on this analysis, does the query require a web search for real-time, current, or external information? Respond with only 'YES' or 'NO'."""
        search_decision = await self.llm.ainvoke([HumanMessage(content=search_decision_prompt)])
        needs_web_search = search_decision.content.strip().upper() == 'YES'
        
        final_response = None
        
        if needs_web_search:
            print("✅ Decision: Web search is required. Executing search...")
            web_results = await web_search.ainvoke({
                "query": current_user_query,
                "agent_type": self.agent_type,
                "advanced": True
            })

            if web_results and "Web search failed" not in web_results:
                print("📝 Extracting key information from web results...")
                # Step 1: Extract and summarize the key information from the web results
                # This forces the LLM to process the real-time data before anything else.
                extract_prompt = f"""You are a data extractor. Your job is to read the following text and extract the key facts and information that directly answer the user's query. Present the information clearly and concisely.

User Query: "{current_user_query}"

Web Search Results:
---
{web_results}
---
Key Information:"""
                extracted_info_msg = await self.llm.ainvoke([HumanMessage(content=extract_prompt)])
                extracted_info = extracted_info_msg.content

                print("�� Synthesizing final answer...")
                # Step 2: Synthesize the extracted info with the knowledge base
                kb_context = ""
                if all_docs:
                    kb_docs = [f"*[Confidence: {score:.2f}]* {doc.page_content}" if isinstance(doc, tuple) else doc.page_content for doc, score in all_docs[:3]]
                    kb_context = "\n\n".join(kb_docs)

                synthesis_prompt = f"""You are a helpful assistant. Your task is to synthesize information to provide a comprehensive answer to the user's original query.

**User's Original Query:** "{current_user_query}"

You have two pieces of information:
1.  **Key Information (from a real-time web search):**
    ---
    {extracted_info}
    ---
2.  **Background Context (from our knowledge base):**
    ---
    {kb_context or "No relevant background context was found."}
    ---

**Instructions:**
- Use the "Key Information" as the primary source to answer the query.
- Use the "Background Context" to add relevant details or explanations if needed.
- Cite your sources clearly (e.g., "According to a web search...", "Our knowledge base adds...").
- If the "Key Information" directly answers the query, present it clearly.

**Final Answer:**"""
                final_response_msg = await self.llm.ainvoke([HumanMessage(content=synthesis_prompt)])
                final_response = final_response_msg.content
            else:
                print("❌ Web search failed or returned no results.")
                final_response = "I was unable to retrieve real-time information from the web. Please try again later."

        # If web search was not needed, generate response from knowledge base
        if final_response is None:
            print("❌ Decision: Web search not required. Using knowledge base only.")
            kb_context = ""
            if all_docs:
                kb_docs = [f"*[Confidence: {score:.2f}]* {doc.page_content}" if isinstance(doc, tuple) else doc.page_content for doc, score in all_docs[:3]]
                kb_context = "\n\n".join(kb_docs)
            
            kb_prompt = f"""You are a helpful assistant. Use the following knowledge base information to answer the user's query.
If the information is insufficient, state that you do not have the information in your knowledge base.
User Query: "{current_user_query}"
Knowledge Base Context:
---
{kb_context or "No information found in the knowledge base."}
---
Answer:"""
            final_response_msg = await self.llm.ainvoke([HumanMessage(content=kb_prompt)])
            final_response = final_response_msg.content
            
        state["messages"].append(AIMessage(content=final_response))
        state["agent_type"] = self.agent_type
        return state
    
    def _should_trigger_web_search(self, query: str, confidence: float, num_docs: int) -> bool:
        """Determine if web search should be triggered based on keywords and confidence."""
        # Always trigger if confidence is low or few documents found
        if confidence < 0.6 or num_docs < 3:
            return True
            
        # Check for keywords specific to this agent type
        query_lower = query.lower()
        keywords = self.web_search_keywords.get(self.agent_type, [])
        
        # Check for any keyword matches
        return any(keyword in query_lower for keyword in keywords)

class IncidentResponseAgent(BaseAgent):
    """An agent specializing in incident response."""
    def __init__(self):
        system_prompt = """You are an expert cybersecurity incident response specialist. 
        Based on the provided context, give detailed, actionable incident response guidance.
        Focus on immediate containment, investigation steps, and recovery procedures.
        Be specific about tools, commands, and methodologies. Format your response using markdown for clarity."""
        super().__init__(
            agent_type="incident_response",
            system_prompt=system_prompt,
        )


class ThreatIntelligenceAgent(BaseAgent):
    """An agent specializing in threat intelligence."""
    def __init__(self):
        system_prompt = """You are an expert threat intelligence analyst. 
        Based on the provided context, provide detailed threat intelligence analysis.
        Include IOCs (Indicators of Compromise), TTPs (Tactics, Techniques, Procedures),
        attribution information, and defensive recommendations. Format your response using markdown for clarity."""
        super().__init__(
            agent_type="threat_intelligence",
            system_prompt=system_prompt,
        )


class PreventionAgent(BaseAgent):
    """An agent specializing in cybersecurity prevention."""
    def __init__(self):
        system_prompt = """You are an expert cybersecurity architect and prevention specialist.
        Based on the provided context, provide comprehensive security frameworks, 
        preventive measures, best practices, and implementation guidance.
        Focus on proactive security measures and risk mitigation strategies. Format your response using markdown for clarity."""
        super().__init__(
            agent_type="prevention",
            system_prompt=system_prompt,
        )

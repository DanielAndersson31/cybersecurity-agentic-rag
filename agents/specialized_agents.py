# agents/specialized_agents.py
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from .state import AgentState
from .tools import search_knowledge_base, web_search
from typing import Dict, List, Optional

class BaseAgent:
    """Base class for specialized cybersecurity agents."""

    def __init__(self, agent_type: str, system_prompt: str, llm_map: Dict[str, BaseChatModel]):
        self.llm_map = llm_map
        self.tools = [search_knowledge_base, web_search]
        self.agent_type = agent_type
        self.system_prompt = system_prompt

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
                "framework", "standard", "policy", "guideline", "best practice",
                "security control", "architecture", "design", "mitigation"
            ]
        }
        
    async def process_async(self, state: AgentState) -> AgentState:
        """Processes a query using the agent's specific LLM and tools."""
        print(f"\n⚙️ {self.agent_type.replace('_', ' ').title()} Agent Processing:")
        print("-" * 40)

        current_query = state["messages"][-1].content
        llm_choice = state.get("llm_choice", "openai_mini")
        self.llm = self.llm_map.get(llm_choice, self.llm_map["openai_mini"])

        state["thought_process"].append(f"{self.agent_type} received query: {current_query}")

        needs_web_search = self._check_web_search_trigger(current_query)
        state["needs_web_search"] = needs_web_search

        if needs_web_search:
            print(f"  - Web search triggered by keywords for {self.agent_type}.")
            web_search_results = await web_search.ainvoke({"query": current_query, "agent_type": self.agent_type})
            state["retrieved_docs"].append({"source": "web_search", "content": web_search_results})
            print("  - Web search complete.")
            state["thought_process"].append("Performed web search due to keywords.")

        knowledge_base_results = await search_knowledge_base.ainvoke({"query": current_query, "agent_type": self.agent_type})
        if knowledge_base_results:
            state["retrieved_docs"].extend(knowledge_base_results)
            print(f"  - Retrieved {len(knowledge_base_results)} docs from knowledge base.")
            state["thought_process"].append(f"Retrieved {len(knowledge_base_results)} docs from knowledge base.")
        else:
            print("  - No relevant documents found in knowledge base.")
            state["thought_process"].append("No relevant docs found in knowledge base.")

        context = "\n\n".join([doc.get("content", "") for doc in state["retrieved_docs"] if doc.get("content")])
        if not context and not needs_web_search:
            context = "No specific context found. Provide a general answer based on your expertise."

        prompt_messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"Context: {context}\n\nUser Query: {current_query}")
        ]

        print(f"  - Invoking LLM ({llm_choice}) for final response...")
        response = await self.llm.ainvoke(prompt_messages)
        final_answer = response.content

        state["messages"].append(AIMessage(content=final_answer))
        state["agent_type"] = self.agent_type
        state["confidence_score"] = self._calculate_confidence(final_answer, state["retrieved_docs"])
        
        print(f"  - Agent response generated. Confidence: {state['confidence_score']:.2f}")
        print("-" * 40)
        return state

    def _calculate_confidence(self, response: str, docs: List[dict]) -> float:
        """Calculates a confidence score based on the response and retrieved documents."""
        score = 0.0
        if docs:
            score += 0.5
            for doc in docs:
                if doc.get("content") and doc["content"][:50].lower() in response.lower()[:50]:
                    score += 0.2
            
            if any(d.get("source") == "web_search" for d in docs) and not any(d.get("content") and d["content"][:50].lower() in response.lower()[:50] for d in docs):
                 score -= 0.1

        score = max(0.0, min(1.0, score + 0.3))
        return score

    def _check_web_search_trigger(self, query: str) -> bool:
        """Checks if the query contains keywords that should trigger a web search."""
        query_lower = query.lower()
        agent_keywords = self.web_search_keywords.get(self.agent_type, [])
        return any(keyword in query_lower for keyword in agent_keywords)


class IncidentResponseAgent(BaseAgent):
    """An agent specializing in incident response."""
    def __init__(self, llm_map: Dict[str, BaseChatModel]):
        system_prompt = """You are an expert incident response specialist. 
        Based on the provided context, offer clear, actionable guidance for cybersecurity incident response.
        Focus on detection, containment, eradication, recovery, and post-incident analysis.
        Format your response using markdown for better readability. Use headings, lists, and bold text where appropriate."""
        super().__init__(
            agent_type="incident_response",
            system_prompt=system_prompt,
            llm_map=llm_map
        )


class ThreatIntelligenceAgent(BaseAgent):
    """An agent specializing in threat intelligence."""
    def __init__(self, llm_map: Dict[str, BaseChatModel]):
        system_prompt = """You are an expert threat intelligence analyst. 
        Based on the provided context, provide detailed threat intelligence analysis.
        Include IOCs (Indicators of Compromise), TTPs (Tactics, Techniques, Procedures),
        attribution information, and defensive recommendations. Format your response using markdown for clarity."""
        super().__init__(
            agent_type="threat_intelligence",
            system_prompt=system_prompt,
            llm_map=llm_map
        )


class PreventionAgent(BaseAgent):
    """An agent specializing in cybersecurity prevention."""
    def __init__(self, llm_map: Dict[str, BaseChatModel]):
        system_prompt = """You are an expert cybersecurity architect and prevention specialist.
        Based on the provided context, provide comprehensive security frameworks, 
        preventive measures, best practices, and implementation guidance.
        Focus on proactive security measures and risk mitigation strategies. Format your response using markdown for clarity."""
        super().__init__(
            agent_type="prevention",
            system_prompt=system_prompt,
            llm_map=llm_map
        )
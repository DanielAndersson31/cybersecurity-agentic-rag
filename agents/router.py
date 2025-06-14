from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage, AIMessage
from langchain_core.language_models.chat_models import BaseChatModel
from .state import AgentState
import json
from typing import Dict

class RouterAgent:
    def __init__(self, llm_map: Dict[str, BaseChatModel], router_llm_key: str = "openai_mini"):
        self.llm = llm_map.get(router_llm_key, llm_map["openai_mini"])

    async def router_query(self, state: AgentState) -> AgentState:
        """Determine which specialist agent should handle the query."""
        current_query_message = state["messages"][-1]
        query_content = current_query_message.content if isinstance(current_query_message, HumanMessage) else ""

        print("\n🤔 Router Analysis:")
        print("-" * 40)

        collaboration_info = await self._detect_collaboration_need(query_content)
        state["collaboration_mode"] = collaboration_info.get("mode")
        state["needs_collaboration"] = collaboration_info.get("needs_collaboration")

        print("Collaboration Detection:")
        print(f"  - Mode: {collaboration_info.get('mode')}")
        print(f"  - Needs Collaboration: {collaboration_info.get('needs_collaboration')}")

        all_messages = state["messages"]
        is_follow_up = await self._detect_follow_up(query_content, all_messages[:-1])
        state["is_follow_up"] = is_follow_up

        print(f"Follow-up Detection: {is_follow_up}")

        preferred_agent_type = state.get("preferred_agent")
        if preferred_agent_type and not state.get("is_follow_up"):
            print(f"  - Preferred Agent (from state): {preferred_agent_type}")
            state["agent_type"] = preferred_agent_type
            return state

        routing_prompt = SystemMessage(
            content="""You are a cybersecurity routing agent. Your task is to determine which specialist agent 
            (incident_response, threat_intelligence, prevention) is best suited to answer the user's query.
            Consider the intent and keywords of the query carefully.
            
            Return ONLY the name of the agent (e.g., "incident_response", "threat_intelligence", "prevention").
            Do NOT include any other text or explanation."""
        )

        user_query_message = HumanMessage(content=query_content)
        
        response = await self.llm.ainvoke([routing_prompt, user_query_message])
        routed_agent_type = response.content.strip().lower()

        valid_agents = ["incident_response", "threat_intelligence", "prevention"]
        if routed_agent_type not in valid_agents:
            print(f"  - Invalid agent type routed by LLM: {routed_agent_type}. Defaulting to incident_response.")
            routed_agent_type = "incident_response"

        state["agent_type"] = routed_agent_type
        print(f"  - LLM Routed Agent: {routed_agent_type}")
        print("-" * 40)
        return state

    async def _detect_follow_up(self, current_query: str, chat_history: list[BaseMessage]) -> bool:
        """Detects if the current query is a follow-up to previous conversation."""
        if not chat_history:
            return False

        if len(chat_history) > 0 and len(current_query.split()) < 7:
            follow_up_phrases = ["what about", "and", "tell me more", "how about", "it", "that", "this"]
            if any(phrase in current_query.lower() for phrase in follow_up_phrases):
                return True

        follow_up_prompt = SystemMessage(
            content=f"""Analyze the following conversation history and the new query.
            Determine if the new query is a direct follow-up or continuation of the previous conversation.
            Return ONLY "yes" or "no".

            Conversation History:
            {json.dumps([msg.dict() for msg in chat_history])}

            New Query: {current_query}
            """
        )
        response = await self.llm.ainvoke([follow_up_prompt])
        return response.content.strip().lower() == "yes"

    async def _detect_collaboration_need(self, query: str) -> Dict[str, any]:
        """
        Detects if the query requires collaboration between multiple agents.
        Returns a dictionary with 'mode' (single_agent, consultation, multi_perspective) and 'needs_collaboration' (bool).
        """
        query_lower = query.lower()

        agent_type_indicators = {
            "incident_response": ["incident", "breach", "attack", "compromise", "response", "remediation", "containment", "recovery"],
            "threat_intelligence": ["threat", "actor", "campaign", "ioc", "ttp", "vulnerability", "exploit", "malware", "ransomware", "advisory", "report"],
            "prevention": ["prevent", "security", "framework", "policy", "best practice", "control", "guideline", "architecture", "design", "mitigation"]
        }

        mentioned_types = sum(
            1 for indicators in agent_type_indicators.values()
            if any(indicator in query_lower for indicator in indicators)
        )

        if mentioned_types > 1:
            return {"mode": "multi_perspective", "needs_collaboration": True}

        high_stakes_indicators = [
            "critical", "severe", "serious", "major", "significant",
            "important", "crucial", "vital", "essential", "key",
            "sensitive", "confidential", "private", "restricted",
            "emergency", "urgent", "immediate", "priority", "high-priority",
            "high-risk", "high-value", "high-impact", "high-stakes"
        ]

        if any(word in query_lower for word in high_stakes_indicators):
            return {"mode": "consultation", "needs_collaboration": True}

        return {"mode": "single_agent", "needs_collaboration": False}
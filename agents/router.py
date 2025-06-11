from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage, AIMessage
from .state import AgentState
import json

class RouterAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        
    def router_query(self, state: AgentState) -> AgentState:
        """"Determine which speciliast agent should handle the query."""
        current_query_message = state["messages"][-1]
        query_content = current_query_message.content if isinstance(current_query_message, HumanMessage) else ""
        
        all_messages = state["messages"]
        is_follow_up = self._detect_follow_up(query_content, all_messages[:-1])
        state["is_follow_up"] = is_follow_up
        
        if state.get("agent_type") and not state.get("needs_routing", True) and not is_follow_up:
            return state
        
        
        system_prompt = """You are a cybersecurity query router. Analyze the user's query and determine which specialist should handle it.

        Available specialists:
        - incident_response: For active security incidents, breaches, malware infections, ransomware, containment, investigation, forensics
        - threat_intelligence: For IOCs, threat actors, TTPs, vulnerability analysis, threat hunting, attribution
        - prevention: For security frameworks, policies, best practices, risk assessment, compliance, proactive security measures

        Respond with only a JSON object in this format:
        {
            "agent_type": "incident_response|threat_intelligence|prevention",
            "confidence": 0.8,
            "reasoning": "Brief explanation"
        }"""
        
        router_messages = [SystemMessage(content=system_prompt)]
        if is_follow_up:
            recent_context_messages = [
                m for m in all_messages if isinstance(m, (HumanMessage, AIMessage))
            ][-4:]
            router_messages.extend(recent_context_messages)
            
        router_messages.append(HumanMessage(content=f"Current Query: {query_content}"))
        
        response = self.llm.invoke(router_messages)
        
        try:
            routing_decision = json.loads(response.content)
            state["agent_type"] = routing_decision.get("agent_type")
            state["confidence_score"] = routing_decision.get("confidence")
            state["needs_routing"] = False
        except (json.JSONDecodeError, KeyError):
            state["agent_type"] = "prevention"  # Default to prevention for unclear queries
            state["confidence_score"] = 0.3
            state["needs_routing"] = False
        return state
    
    def _detect_follow_up(self, query: str, conversation_history: list[BaseMessage]) -> bool:
        """Detect if the current query is a follow-up based on conversation history."""
        if len(conversation_history) <= 1:
            return False
        
        follow_up_indicators = [
            "this", "that", "it", "also", "what about", "how about",
            "tell me more", "expand", "clarify", "explain", "additionally",
            "furthermore", "regarding", "concerning", "about that"
        ]
        
        query_lower = query.lower()

        has_follow_up_phrase = any(indicator in query_lower for indicator in follow_up_indicators)

        is_short_question = len(query.split()) <= 8

        has_recent_context = len(conversation_history) > 1

        return has_follow_up_phrase or (is_short_question and has_recent_context)
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from .state import AgentState
import json

class RouterAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        
    def router_query(self, state: AgentState) -> AgentState:
        """"Determine which speciliast agent should handle the query."""
        query = state["query"]
        
        if state.get("agent_type") and not state.get("needs_routing", True):
            # If already routed, skip routing
            return state

        system_prompt = """You are a cybersecurity query router. Analyze the user's query and determine which specialist should handle it.

        Available specialists:
        - incident_response: For active security incidents, breaches, malware infections, ransomware, containment, investigation, forensics
        - threat_intelligence: For IOCs, threat actors, TTPs, vulnerability analysis, threat hunting, attribution
        - prevention: For security frameworks, policies, best practices, risk assessment, compliance, proactive security measures
        - shared: For general cybersecurity questions that don't fit the above categories

        Respond with only a JSON object in this format:
        {
            "agent_type": "incident_response|threat_intelligence|prevention|shared",
            "confidence": 0.8,
            "reasoning": "Brief explanation"
        }"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Query: {query}")
        ]
        response = self.llm.invoke(messages)
        
        try:
            routing_decision = json.loads(response.content)
            state["agent_type"] = routing_decision.get("agent_type")
            state["confidence_score"] = routing_decision.get("confidence")
            state["needs_routing"] = False
        except (json.JSONDecodeError, KeyError):
            state["agent_type"] = "shared"
            state["confidence_score"] = 0.5
            state["needs_routing"] = False
        return state
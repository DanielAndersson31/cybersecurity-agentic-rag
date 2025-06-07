# agents/specialized_agents.py
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from .state import AgentState
from .tools import (
    search_incident_response_knowledge,
    search_threat_intelligence_knowledge,
    search_prevention_knowledge,
    search_shared_knowledge
)

class IncidentResponseAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        self.tools = [search_incident_response_knowledge, search_shared_knowledge]
        
    def process(self, state: AgentState) -> AgentState:
        """Process incident response queries."""
        query = state["query"]
        
        # Retrieve relevant documents
        ir_docs = search_incident_response_knowledge.invoke({"query": query})
        shared_docs = search_shared_knowledge.invoke({"query": query})
        
        all_docs = ir_docs + shared_docs
        context = "\n\n".join(all_docs[:5])  # Limit context
        
        system_prompt = """You are an expert cybersecurity incident response specialist. 
        Based on the provided context, give detailed, actionable incident response guidance.
        Focus on immediate containment, investigation steps, and recovery procedures.
        Be specific about tools, commands, and methodologies."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Context:\n{context}\n\nQuery: {query}")
        ]
        
        response = self.llm.invoke(messages)
        
        state["retrieved_docs"] = all_docs
        state["context"] = context
        state["response"] = response.content
        state["agent_type"] = "incident_response"
        state["confidence_score"] = 0.9 if len(all_docs) > 0 else 0.3
        
        return state

class ThreatIntelligenceAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        self.tools = [search_threat_intelligence_knowledge, search_shared_knowledge]
        
    def process(self, state: AgentState) -> AgentState:
        """Process threat intelligence queries."""
        query = state["query"]
        
        # Retrieve relevant documents
        ti_docs = search_threat_intelligence_knowledge.invoke({"query": query})
        shared_docs = search_shared_knowledge.invoke({"query": query})
        
        all_docs = ti_docs + shared_docs
        context = "\n\n".join(all_docs[:5])
        
        system_prompt = """You are an expert threat intelligence analyst. 
        Based on the provided context, provide detailed threat intelligence analysis.
        Include IOCs (Indicators of Compromise), TTPs (Tactics, Techniques, Procedures),
        attribution information, and defensive recommendations."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Context:\n{context}\n\nQuery: {query}")
        ]
        
        response = self.llm.invoke(messages)
        
        state["retrieved_docs"] = all_docs
        state["context"] = context
        state["response"] = response.content
        state["agent_type"] = "threat_intelligence"
        state["confidence_score"] = 0.9 if len(all_docs) > 0 else 0.3
        
        return state

class PreventionAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        self.tools = [search_prevention_knowledge, search_shared_knowledge]
        
    def process(self, state: AgentState) -> AgentState:
        """Process cybersecurity prevention and framework queries."""
        query = state["query"]
        
        # Retrieve relevant documents
        prev_docs = search_prevention_knowledge.invoke({"query": query})
        shared_docs = search_shared_knowledge.invoke({"query": query})
        
        all_docs = prev_docs + shared_docs
        context = "\n\n".join(all_docs[:5])
        
        system_prompt = """You are an expert cybersecurity architect and prevention specialist.
        Based on the provided context, provide comprehensive security frameworks, 
        preventive measures, best practices, and implementation guidance.
        Focus on proactive security measures and risk mitigation strategies."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Context:\n{context}\n\nQuery: {query}")
        ]
        
        response = self.llm.invoke(messages)
        
        state["retrieved_docs"] = all_docs
        state["context"] = context
        state["response"] = response.content
        state["agent_type"] = "prevention"
        state["confidence_score"] = 0.9 if len(all_docs) > 0 else 0.3
        
        return state
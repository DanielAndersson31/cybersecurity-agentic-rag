# agents/specialized_agents.py
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from .state import AgentState
from .tools import (
    search_incident_response_knowledge,
    search_threat_intelligence_knowledge,
    search_prevention_knowledge
)

class BaseAgent:
    """Base class for specialized cybersecurity agents."""

    def __init__(self, agent_type: str, search_tool, system_prompt: str):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        self.tools = [search_tool]
        self.agent_type = agent_type
        self.search_tool = search_tool
        self.system_prompt = system_prompt

    def process(self, state: AgentState) -> AgentState:
        """Processes a query and updates the agent state."""
        current_user_query = ""
        
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                current_user_query = msg.content
                break
        
        all_docs = self.search_tool.invoke({"query": current_user_query})
        doc_contents = []
        for result in all_docs[:5]:
            if isinstance(result, tuple):
                doc, score = result
                doc_contents.append(doc.page_content)
            else:
                doc_contents.append(result.page_content)
        context = "\n\n".join(doc_contents)
      
        agent_messages = [SystemMessage(content=self.system_prompt)]
        agent_messages.append(HumanMessage(content=f"Context from knowledge base:\n{context}"))

        relevant_history = []
        for message in state["messages"]:
            if isinstance(message, (HumanMessage, AIMessage)):
                relevant_history.append(message)
        
        agent_messages.extend(relevant_history)
        
        response = self.llm.invoke(agent_messages)
        state["messages"].append(response)
        state["agent_type"] = self.agent_type
        state["confidence_score"] = 0.9 if len(all_docs) > 0 else 0.3
        state["retrieved_docs"] = all_docs
        
        return state

    async def process_async(self, state: AgentState) -> AgentState:
        """Async version of process method."""
        current_user_query = ""
        
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                current_user_query = msg.content
                break
        
        # Make search async
        all_docs = await self.search_tool.ainvoke({"query": current_user_query})
        doc_contents = []
        for result in all_docs[:5]:
            if isinstance(result, tuple):
                doc, score = result
                doc_contents.append(doc.page_content)
            else:
                doc_contents.append(result.page_content)
        context = "\n\n".join(doc_contents)
      
        agent_messages = [SystemMessage(content=self.system_prompt)]
        agent_messages.append(HumanMessage(content=f"Context from knowledge base:\n{context}"))

        relevant_history = []
        for message in state["messages"]:
            if isinstance(message, (HumanMessage, AIMessage)):
                relevant_history.append(message)
        
        agent_messages.extend(relevant_history)
        
        response = await self.llm.ainvoke(agent_messages)
        state["messages"].append(response)
        state["agent_type"] = self.agent_type
        state["confidence_score"] = 0.9 if len(all_docs) > 0 else 0.3
        state["retrieved_docs"] = all_docs

        return state

class IncidentResponseAgent(BaseAgent):
    """An agent specializing in incident response."""
    def __init__(self):
        system_prompt = """You are an expert cybersecurity incident response specialist. 
        Based on the provided context, give detailed, actionable incident response guidance.
        Focus on immediate containment, investigation steps, and recovery procedures.
        Be specific about tools, commands, and methodologies."""
        super().__init__(
            agent_type="incident_response",
            search_tool=search_incident_response_knowledge,
            system_prompt=system_prompt,
        )


class ThreatIntelligenceAgent(BaseAgent):
    """An agent specializing in threat intelligence."""
    def __init__(self):
        system_prompt = """You are an expert threat intelligence analyst. 
        Based on the provided context, provide detailed threat intelligence analysis.
        Include IOCs (Indicators of Compromise), TTPs (Tactics, Techniques, Procedures),
        attribution information, and defensive recommendations."""
        super().__init__(
            agent_type="threat_intelligence",
            search_tool=search_threat_intelligence_knowledge,
            system_prompt=system_prompt,
        )


class PreventionAgent(BaseAgent):
    """An agent specializing in cybersecurity prevention."""
    def __init__(self):
        system_prompt = """You are an expert cybersecurity architect and prevention specialist.
        Based on the provided context, provide comprehensive security frameworks, 
        preventive measures, best practices, and implementation guidance.
        Focus on proactive security measures and risk mitigation strategies."""
        super().__init__(
            agent_type="prevention",
            search_tool=search_prevention_knowledge,
            system_prompt=system_prompt,
        )

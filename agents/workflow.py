from langgraph.graph import StateGraph, END
from .state import AgentState
from .router import RouterAgent
from .specialized_agents import IncidentResponseAgent, ThreatIntelligenceAgent, PreventionAgent
from .tools import search_shared_knowledge
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

class CybersecurityRagWorkflow:
    def __init__(self) -> None:
        self.router = RouterAgent()
        self.ir_agent = IncidentResponseAgent()
        self.ti_agent = ThreatIntelligenceAgent()
        self.prevention_agent = PreventionAgent()
        
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()
        
    def _build_workflow(self) -> StateGraph:
        """Build the state graph for the RAG workflow."""
        workflow = StateGraph()
        
        # Add Nodes
        workflow.add_node("router",self.router_query)
        workflow.add_node("incident_response", self.ir_agent.process)
        workflow.add_node("threat_intelligence", self.ti_agent.process)
        workflow.add_node("prevention", self.prevention_agent.process)
        workflow.add_node("shared", self._handle_shared_query)
        
        # Set Entry Point
        workflow.set_entry("router")
        
        # Add conditional edges based on routing decision
        workflow.add_conditional_edge(
            "router",
            self._route_to_specialist,
            {
                "incident_response": "incident_response",
                "threat_intelligence": "threat_intelligence",
                "prevention": "prevention",
                "shared": "shared"
            }
        )
        workflow.add_edge("incident_response", END)
        workflow.add_edge("threat_intelligence", END)
        workflow.add_edge("prevention", END)
        workflow.add_edge("shared", END)
        return workflow
    
    def _route_to_specialist(self, state: AgentState) -> str:
        """Route to the appropriate specialist based on agent type."""
        return state["agent_type"]
    def _handle_shared_query(self, state: AgentState) -> AgentState:
        """Handle shared queries that don't fit any specialist category."""
        query = state["query"]
        
        # Retrieve shared knowledge documents
        shared_docs = search_shared_knowledge.invoke({"query": query})
        context = "\n\n".join(shared_docs[:5])
        
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        
        system_prompt = """You are a general cybersecurity expert. 
        Based on the provided context, provide comprehensive cybersecurity guidance.
        Cover relevant aspects of security that apply to the query."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Context:\n{context}\n\nQuery: {query}")
        ]
        
        response = llm.invoke(messages)
        
        state["retrieved_docs"] = shared_docs
        state["context"] = context
        state["response"] = response.content
        state["agent_type"] = "shared"
        state["confidence_score"] = 0.8 if len(shared_docs) > 0 else 0.4
        
        return state
    def process_query(self, query: str, agent_type: str = None) -> dict:
        """Process a cybersecurity query through the RAG workflow."""
        initial_state = {
            "messages": [],
            "query": query,
            "agent_type": agent_type,
            "retrieved_docs": [],
            "context": "",
            "response": "",
            "confidence_score": 0.0,
            "needs_routing": agent_type is None
        }
        
        # Run the workflow
        final_state = self.app.invoke(initial_state)
        
        return {
            "query": final_state["query"],
            "response": final_state["response"],
            "agent_type": final_state["agent_type"],
            "confidence_score": final_state["confidence_score"],
            "num_docs_retrieved": len(final_state["retrieved_docs"])
        }
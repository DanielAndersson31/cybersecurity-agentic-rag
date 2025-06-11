import uuid
import aiosqlite
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from typing import Optional
import os

from .state import AgentState, ConversationTurn
from .router import RouterAgent
from .specialized_agents import IncidentResponseAgent, ThreatIntelligenceAgent, PreventionAgent
from .collaboration import CollaborationSystem



class CybersecurityRAGWorkflow:
    def __init__(self) -> None:
        self.router = RouterAgent()
        self.ir_agent = IncidentResponseAgent()
        self.ti_agent = ThreatIntelligenceAgent()
        self.prevention_agent = PreventionAgent()
        self.db_path = os.path.join("data", "memory", "agent_rag_history.db")
        self.workflow = self._build_workflow()
        self.collaboration_system = CollaborationSystem(
            ir_agent=self.ir_agent,
            ti_agent=self.ti_agent,
            prevention_agent=self.prevention_agent
        )
        
    async def initialize(self):
        """Initialize the workflow with an async SQLite connection."""
        conn = await aiosqlite.connect(self.db_path)
        self.checkpointer = AsyncSqliteSaver(conn=conn)
        self.app = self.workflow.compile(checkpointer=self.checkpointer)
        
    def _build_workflow(self) -> StateGraph:
        """Build the state graph for the RAG workflow."""
        workflow = StateGraph(AgentState)
        
        # Add Nodes
        workflow.add_node("router", self.router.router_query)
        workflow.add_node("incident_response", self.ir_agent.process)
        workflow.add_node("threat_intelligence", self.ti_agent.process)
        workflow.add_node("prevention", self.prevention_agent.process)
        
        # Collaboration nodes
        workflow.add_node("team_collaboration", self.collaboration_system.multi_agent_consultation)        
        # Set Entry Point
        workflow.set_entry_point("router")
        
        # Add conditional edges based on routing decision
        workflow.add_conditional_edges(
            "router",
            self._enhanced_routing_logic,
            {
                "incident_response": "incident_response",
                "threat_intelligence": "threat_intelligence",
                "prevention": "prevention",
                "team_collaboration": "team_collaboration"
            }
        )
        workflow.add_edge("incident_response", END)
        workflow.add_edge("threat_intelligence", END)
        workflow.add_edge("prevention", END)
        return workflow
    
    def _route_to_specialist(self, state: AgentState) -> str:
        """Route to the appropriate specialist based on agent type."""
        return state["agent_type"]

    async def process_query(self, user_query: str, session_id: Optional[str] = None) -> dict:
        """Process a query through the enhanced workflow with collaboration support"""
        
        if session_id is None:
            session_id = str(uuid.uuid4())

        initial_messages = [HumanMessage(content=user_query)]
        initial_state = {
            "messages": initial_messages,
            "agent_type": None,
            "retrieved_docs": [],
            "confidence_score": 0.0,
            "needs_routing": True,
            "session_id": session_id,
            "is_follow_up": False,
            
            # Properly initialize collaboration fields to match your state definition
            "collaboration_mode": "single_agent",
            "consulting_agents": [],  # List[str] - must be list, not None
            "agent_responses": {},    # Dict[str, str] - must be dict, not None
            "needs_collaboration": False,  # bool - not Optional, so must be set
            "primary_agent": None,
            "collaboration_confidence": None
        }

        config = {"configurable": {"thread_id": session_id}}

        # Execute the workflow
        await self.app.ainvoke(initial_state, config=config)

        # Retrieve final state
        retrieved_full_state = await self.app.aget_state(config)
        retrieved_full_state = retrieved_full_state.values

        # Extract the last response
        last_response_content = ""
        for msg in reversed(retrieved_full_state["messages"]):
            if isinstance(msg, AIMessage):
                last_response_content = msg.content
                break

        # Build conversation history
        conversation_turns_for_output = []
        for i in range(0, len(retrieved_full_state["messages"]) - 1, 2):
            if i + 1 < len(retrieved_full_state["messages"]):
                user_msg = retrieved_full_state["messages"][i]
                agent_msg = retrieved_full_state["messages"][i+1]
                if isinstance(user_msg, HumanMessage) and isinstance(agent_msg, AIMessage):
                    conversation_turns_for_output.append(
                        ConversationTurn(
                            user_query=user_msg.content,
                            agent_response=agent_msg.content,
                            agent_type=retrieved_full_state.get("agent_type", "unknown"),
                            timestamp="N/A"
                        )
                    )

        # Enhanced return with collaboration info
        return {
            "session_id": session_id,
            "user_query": user_query,
            "response": last_response_content,
            "agent_type": retrieved_full_state.get("agent_type"),
            "primary_agent": retrieved_full_state.get("primary_agent"),
            "confidence_score": retrieved_full_state.get("confidence_score", 0.0),
            "collaboration_confidence": retrieved_full_state.get("collaboration_confidence"),
            "collaboration_mode": retrieved_full_state.get("collaboration_mode", "single_agent"),
            "consulting_agents": retrieved_full_state.get("consulting_agents", []),
            "num_docs_retrieved": len(retrieved_full_state.get("retrieved_docs", [])),
            "full_conversation_messages": retrieved_full_state["messages"],
            "conversation_history_summary": conversation_turns_for_output,
            
            # Collaboration metadata for debugging/display
            "agent_responses": retrieved_full_state.get("agent_responses", {}),
            "was_collaboration": retrieved_full_state.get("needs_collaboration", False)
        }
    def _enhanced_routing_logic(self, state: AgentState) -> str:
        """Enhanced routing that considers collaboration needs"""
        
        needs_collaboration = state.get("needs_collaboration", False)
        
        if needs_collaboration:
            return "team_collaboration"
        else:
            # Standard single-agent routing
            return state["agent_type"]
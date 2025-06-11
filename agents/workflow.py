import uuid
import aiosqlite
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from typing import Optional

from .state import AgentState, ConversationTurn
from .router import RouterAgent
from .specialized_agents import IncidentResponseAgent, ThreatIntelligenceAgent, PreventionAgent



class CybersecurityRAGWorkflow:
    def __init__(self) -> None:
        self.router = RouterAgent()
        self.ir_agent = IncidentResponseAgent()
        self.ti_agent = ThreatIntelligenceAgent()
        self.prevention_agent = PreventionAgent()
        self.db_path = "agent_rag_history.db"
        self.workflow = self._build_workflow()
        
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
        
        # Set Entry Point
        workflow.set_entry_point("router")
        
        # Add conditional edges based on routing decision
        workflow.add_conditional_edges(
            "router",
            self._route_to_specialist,
            {
                "incident_response": "incident_response",
                "threat_intelligence": "threat_intelligence",
                "prevention": "prevention"
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
            "is_follow_up": False
        }

        config = {"configurable": {"thread_id": session_id}}

        await self.app.ainvoke(initial_state, config=config)

        retrieved_full_state = await self.app.aget_state(config)
        retrieved_full_state = retrieved_full_state.values

        last_response_content = ""
        for msg in reversed(retrieved_full_state["messages"]):
            if isinstance(msg, AIMessage):
                last_response_content = msg.content
                break

        conversation_turns_for_output = []
        for i in range(0, len(retrieved_full_state["messages"]) - 1, 2):
            user_msg = retrieved_full_state["messages"][i]
            agent_msg = retrieved_full_state["messages"][i+1]
            if isinstance(user_msg, HumanMessage) and isinstance(agent_msg, AIMessage):
                conversation_turns_for_output.append(
                    ConversationTurn(
                        user_query=user_msg.content,
                        agent_response=agent_msg.content,
                        agent_type="unknown",
                        timestamp="N/A"
                    )
                )

        return {
            "session_id": session_id,
            "user_query": user_query,
            "response": last_response_content,
            "agent_type": retrieved_full_state["agent_type"],
            "confidence_score": retrieved_full_state["confidence_score"],
            "num_docs_retrieved": len(retrieved_full_state.get("retrieved_docs", [])),
            "full_conversation_messages": retrieved_full_state["messages"],
            "conversation_history_summary": conversation_turns_for_output
        }
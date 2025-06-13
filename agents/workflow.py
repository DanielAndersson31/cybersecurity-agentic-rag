# workflow.py

import uuid
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
# Ensure this import is AsyncSqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver 
from typing import Optional
from pathlib import Path

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
        self.db_path = Path("data") / "conversations" / "chat_history.db"
        
        self.collaboration_system = CollaborationSystem(
            ir_agent=self.ir_agent,
            ti_agent=self.ti_agent,
            prevention_agent=self.prevention_agent
        )
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._checkpointer_context_manager = AsyncSqliteSaver.from_conn_string(str(self.db_path))
        self.checkpointer = None 
        
        self.workflow = self._build_workflow()
        self.app = None  # Add this line - initialize app as None
        
    async def __aenter__(self):
        """Enter the async context manager"""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager and cleanup resources"""
        if self._checkpointer_context_manager and self.checkpointer:
            await self._checkpointer_context_manager.__aexit__(None, None, None)
            self.checkpointer = None
            self.app = None
        return False  # Don't suppress exceptions
    
    async def initialize(self):
        """Initialize the workflow with async checkpointer"""
        if self.app is not None:
            # Already initialized
            return
            
        try:
            # Await entering the async context manager
            self.checkpointer = await self._checkpointer_context_manager.__aenter__()
            self.app = self.workflow.compile(
                checkpointer=self.checkpointer,
                interrupt_before=[],
                interrupt_after=[]
            )
        except Exception as e:
            # Clean up if initialization fails
            if self.checkpointer:
                await self._checkpointer_context_manager.__aexit__(type(e), e, e.__traceback__)
                self.checkpointer = None
            raise
    async def process_query_async(self, user_query: str, session_id: Optional[str] = None) -> dict:
        
        if self.app is None:
            raise RuntimeError("Workflow not initialized. Use 'async with' or call initialize() first.")
        
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
            
            "collaboration_mode": "single_agent",
            "consulting_agents": [],
            "agent_responses": {},
            "needs_collaboration": False,
            "primary_agent": None,
            "collaboration_confidence": None
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
            "conversation_history_summary": conversation_turns_for_output,
            
            "agent_responses": retrieved_full_state.get("agent_responses", {}),
            "was_collaboration": retrieved_full_state.get("needs_collaboration", False)
        }
    async def summarize_conversation(self, state: AgentState) -> AgentState:
        """Summarize conversation when it gets too long"""
        messages = state["messages"]
        
        # If conversation is getting long (e.g., > 20 messages)
        if len(messages) > 20:
            # Keep last 10 messages, summarize the rest
            messages_to_summarize = messages[:-10]
            recent_messages = messages[-10:]
            
            # Format messages for summary
            conversation_text = "\n".join([
                f"{msg.__class__.__name__.replace('Message', '')}: {msg.content}"
                for msg in messages_to_summarize
            ])
            
            # Use LLM to create summary
            summary_prompt = f"""Summarize this conversation:
            {conversation_text}
            """
            
            summary = await self.summarizer_llm.ainvoke(summary_prompt)
            
            # Update state
            state["conversation_summary"] = summary.content
            state["messages"] = recent_messages
        
        return state

    def _enhanced_routing_logic(self, state: AgentState) -> str:
        needs_collaboration = state.get("needs_collaboration", False)
        
        if needs_collaboration:
            # Set the primary agent to the current agent type when collaboration is needed
            state["primary_agent"] = state["agent_type"]
            return "team_collaboration"
        else:
            return state["agent_type"]
    
    def _build_workflow(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        
        workflow.add_node("summarize_conversation", self.summarize_conversation)
        workflow.add_node("router", self.router.router_query)
        workflow.add_node("incident_response", self.ir_agent.process_async)
        workflow.add_node("threat_intelligence", self.ti_agent.process_async)
        workflow.add_node("prevention", self.prevention_agent.process_async)
        workflow.add_node("team_collaboration", self.collaboration_system.multi_agent_consultation_async)
        
        workflow.set_entry_point("summarize_conversation")
        
        workflow.add_edge("summarize_conversation", "router")
        
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
        workflow.add_edge("team_collaboration", END)
        
        return workflow

    
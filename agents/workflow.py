# workflow.py

import uuid
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from typing import Optional, Dict
from pathlib import Path

from .state import AgentState, ConversationTurn
from .router import RouterAgent
from .specialized_agents import IncidentResponseAgent, ThreatIntelligenceAgent, PreventionAgent
from .collaboration import CollaborationSystem


class CybersecurityRAGWorkflow:
    LLM_MAP = {
        "claude_sonnet": ChatAnthropic(model="claude-3-5-sonnet-20240620", temperature=0.1),
        "openai_mini": ChatOpenAI(model="gpt-4o-mini", temperature=0.1),
        "gpt4o": ChatOpenAI(model="gpt-4o", temperature=0.2),
    }

    def __init__(self, llm_choice: str = "openai_mini") -> None:
        self.llm_choice = llm_choice
        
        self.router = RouterAgent(llm_map=self.LLM_MAP, router_llm_key="openai_mini")
        self.ir_agent = IncidentResponseAgent(llm_map=self.LLM_MAP)
        self.ti_agent = ThreatIntelligenceAgent(llm_map=self.LLM_MAP)
        self.prevention_agent = PreventionAgent(llm_map=self.LLM_MAP)

        self.summarize_conversation_llm = self.LLM_MAP.get(self.llm_choice, self.LLM_MAP["openai_mini"])

        self.collaboration_system = CollaborationSystem(
            ir_agent=self.ir_agent,
            ti_agent=self.ti_agent,
            prevention_agent=self.prevention_agent,
            llm_map=self.LLM_MAP
        )

        self.workflow = self._build_workflow()
        self.checkpointer_manager = self._create_checkpointer_manager()
        self.checkpointer = None  # Will be set in initialize
        self.app = None  # Will be set in initialize

    async def initialize(self):
        """Enters the checkpointer context and compiles the app."""
        if self.app is None:
            self.checkpointer = await self.checkpointer_manager.__aenter__()
            self.app = self.workflow.compile(checkpointer=self.checkpointer)

    async def close(self):
        """Cleans up resources by exiting the checkpointer context."""
        if self.checkpointer_manager:
            await self.checkpointer_manager.__aexit__(None, None, None)

    def _create_checkpointer_manager(self):
        """Creates the checkpointer context manager."""
        checkpoint_dir = Path("data/conversation_checkpoints")
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        db_path = checkpoint_dir / "langgraph.sqlite"
        # Return the context manager object itself
        return AsyncSqliteSaver.from_conn_string(str(db_path))

    async def summarize_conversation(self, state: AgentState) -> AgentState:
        """Summarizes the conversation history, integrating the new query."""
        conversation_history = state.get("conversation_summary", "")

        current_query_message = state["messages"][-1]
        new_message_content = current_query_message.content if isinstance(current_query_message, HumanMessage) else ""

        if not conversation_history:
            return {"conversation_summary": new_message_content}

        summary_prompt = SystemMessage(
            content=f"""You are a helpful assistant tasked with summarizing conversation history between a user and a cybersecurity assistant.
            The current conversation history is:
            {conversation_history}

            The new user query is:
            {new_message_content}

            Please provide a concise summary of the entire conversation so far, integrating the new query.
            If the new query is a follow-up, ensure the summary reflects that continuity.
            """
        )

        summary = await self.summarize_conversation_llm.ainvoke([summary_prompt])
        return {"conversation_summary": summary.content}


    def _enhanced_routing_logic(self, state: AgentState) -> str:
        """Determine the next node based on router's decision and collaboration needs."""
        if state["needs_collaboration"]:
            if not state.get("primary_agent"):
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

    async def process_query_async(self, user_query: str, client_config: Optional[Dict] = None) -> Dict:
        """
        Processes a user query through the LangGraph workflow, allowing for dynamic LLM and agent selection.
        """

        if self.app is None:
            raise RuntimeError("Workflow not initialized or compiled. Ensure self.app is set in __init__ or initialize().")

        if client_config is None:
            client_config = {}

        thread_id = client_config.get("configurable", {}).get("thread_id", str(uuid.uuid4()))

        preferred_llm_choice = client_config.get("preferred_llm_choice", self.llm_choice)
        preferred_agent = client_config.get("preferred_agent", None)

        initial_messages = [HumanMessage(content=user_query)]
        initial_state = {
            "messages": initial_messages,
            "agent_type": None,
            "retrieved_docs": [],
            "confidence_score": 0.0,
            "needs_routing": True,
            "thread_id": thread_id,
            "is_follow_up": False,
            "preferred_agent": preferred_agent,
            "llm_choice": preferred_llm_choice,

            "collaboration_mode": "single_agent",
            "consulting_agents": [],
            "agent_responses": {},
            "needs_collaboration": False,
            "primary_agent": None,
            "collaboration_confidence": None,
            "thought_process": [],
            "needs_web_search": False,
            "conversation_summary": ""
        }

        langgraph_invoke_config = client_config.copy()
        if "configurable" not in langgraph_invoke_config:
            langgraph_invoke_config["configurable"] = {}
        langgraph_invoke_config["configurable"]["thread_id"] = thread_id

        await self.app.ainvoke(initial_state, config=langgraph_invoke_config)

        retrieved_full_state = await self.app.aget_state(langgraph_invoke_config)
        retrieved_full_state_values = retrieved_full_state.values

        last_response_content = ""
        for msg in reversed(retrieved_full_state_values["messages"]):
            if isinstance(msg, AIMessage):
                last_response_content = msg.content
                break

        conversation_turns_for_output = []
        for i in range(0, len(retrieved_full_state_values["messages"]) - 1, 2):
            user_msg = retrieved_full_state_values["messages"][i]
            if i + 1 < len(retrieved_full_state_values["messages"]):
                agent_msg = retrieved_full_state_values["messages"][i+1]
                if isinstance(user_msg, HumanMessage) and isinstance(agent_msg, AIMessage):
                    conversation_turns_for_output.append(
                        ConversationTurn(
                            user_query=user_msg.content,
                            agent_response=agent_msg.content,
                            agent_type=retrieved_full_state_values.get("agent_type", "unknown"),
                            timestamp="N/A"
                        )
                    )

        return {
            "session_id": thread_id,
            "user_query": user_query,
            "response": last_response_content,
            "agent_type": retrieved_full_state_values.get("agent_type"),
            "primary_agent": retrieved_full_state_values.get("primary_agent"),
            "confidence_score": retrieved_full_state_values.get("confidence_score", 0.0),
            "collaboration_confidence": retrieved_full_state_values.get("collaboration_confidence"),
            "collaboration_mode": retrieved_full_state_values.get("collaboration_mode", "single_agent"),
            "consulting_agents": retrieved_full_state_values.get("consulting_agents", []),
            "num_docs_retrieved": len(retrieved_full_state_values.get("retrieved_docs", [])),
            "conversation_history_summary": conversation_turns_for_output,
            "overall_conversation_summary": retrieved_full_state_values.get("conversation_summary"),

            "agent_responses": retrieved_full_state_values.get("agent_responses", {}),
            "was_collaboration": retrieved_full_state_values.get("needs_collaboration", False),
            "final_llm_choice": retrieved_full_state_values.get("llm_choice")
        }
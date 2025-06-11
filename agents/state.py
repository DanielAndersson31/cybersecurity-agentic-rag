from typing import TypedDict, List, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ConversationTurn(TypedDict):
    """"Represents a single turn in a conversation, including the message and metadata."""
    user_query: str
    agent_response: str
    agent_type: str
    timestamp: str

class AgentState(TypedDict):
    """Represents the state of an agent, including its messages and metadata."""
    messages: Annotated[List[BaseMessage], add_messages]
    agent_type: Optional[str]
    retrieved_docs: List[dict]
    confidence_score: Optional[float]
    needs_routing: bool
    session_id: Optional[str]
    is_follow_up: bool
    conversation_history: Optional[List[ConversationTurn]]
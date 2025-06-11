from typing import TypedDict, List, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing import Dict


class ConversationTurn(TypedDict):
    """"Represents a single turn in a conversation, including the message and metadata."""
    user_query: str
    agent_response: str
    agent_type: str
    timestamp: str

class AgentState(TypedDict):
    """Represents the state of an agent, including its messages and metadata."""
    # Your existing fields
    messages: Annotated[List[BaseMessage], add_messages]
    agent_type: Optional[str]
    retrieved_docs: List[dict]
    confidence_score: Optional[float]
    
    collaboration_mode: Optional[str]  # "consultation", "multi_perspective"
    consulting_agents: List[str]  # Which agents to consult
    agent_responses: Dict[str, str]  # Responses from each agent
    needs_collaboration: bool
    primary_agent: Optional[str]  # Lead agent for this query
    collaboration_confidence: Optional[float]  # Team confidence
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
    messages: Annotated[List[BaseMessage], add_messages]
    agent_type: str
    retrieved_docs: List[dict]
    confidence_score: float
    preferred_agent: str # Preferred agent for the query
    llm_choice: str  # LLM choice for the query
    thread_id: str  # Thread ID for the conversation / Session ID
    
    collaboration_mode: str  # "consultation", "multi_perspective"
    consulting_agents: List[str]  # Which agents to consult
    agent_responses: Dict[str, str]  # Responses from each agent
    needs_collaboration: bool
    primary_agent: str  # Lead agent for this query
    collaboration_confidence: float # Team confidence
    thought_process: List[str] # Steps taken in processing the query
    needs_web_search: bool  # Whether the query needs web search
    conversation_summary: str  # Summary of the conversation

    
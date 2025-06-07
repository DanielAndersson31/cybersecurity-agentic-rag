from typing import TypeDict, List, Optional, Annotated
from langchain_core.messages import BaseMessage
from operator import add

class AgentState(TypeDict):
    """Represents the state of an agent, including its messages and metadata."""
    
    message: Annotated[List[BaseMessage], add]
    query: str
    agent_type: Optional[str] = None
    retrieved_docs: List[dict]
    context: str
    response: str
    confidence_score:float
    needs_routing: bool
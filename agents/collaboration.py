from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from .state import AgentState
from typing import Dict
import asyncio

class CollaborationSystem:
    def __init__(self, ir_agent, ti_agent, prevention_agent):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        self.agents = {
            "incident_response": ir_agent,
            "threat_intelligence": ti_agent,
            "prevention": prevention_agent
        }

    async def _get_all_perspectives_async(self, query: str) -> Dict[str, Dict[str, str]]:
        """Get responses and retrieved docs from all agents concurrently"""
        async def process_agent(agent_name, agent):
            state = {"messages": [HumanMessage(content=query)]}
            response = await agent.process_async(state)
            return agent_name, {
                "response": response["messages"][-1].content,
                "retrieved_docs": response.get("retrieved_docs", [])
            }

        tasks = [process_agent(name, agent) for name, agent in self.agents.items()]
        results = await asyncio.gather(*tasks)
        return dict(results)

    async def _get_consultation_async(self, primary_agent: str, query: str) -> Dict[str, str]:
        """Get consultation from other agents concurrently"""
        async def get_agent_consultation(agent_name, agent):
            if agent_name != primary_agent:
                state = {"messages": [HumanMessage(content=query)]}
                response = await agent.process_async(state)
                return agent_name, response["messages"][-1].content
            return None

        tasks = [get_agent_consultation(name, agent) for name, agent in self.agents.items()]
        responses = await asyncio.gather(*tasks)
        return {k: v for k, v in responses if v is not None}

    async def multi_agent_consultation_async(self, state: AgentState) -> AgentState:
        """Execute multi-agent collaboration based on collaboration mode"""
        
        print("\n🤝 Collaboration Process:")
        print("-" * 40)
        
        # Extract the user's query from conversation history
        current_query = ""
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                current_query = msg.content
                break
        
        print(f"Processing query: {current_query}")
        
        # Get collaboration strategy from state
        collaboration_mode = state.get("collaboration_mode")
        if not collaboration_mode:
            raise ValueError("No collaboration mode specified in state")
            
        primary_agent = state.get("primary_agent")
        
        print(f"\nCollaboration Strategy:")
        print(f"  - Mode: {collaboration_mode}")
        if primary_agent:
            print(f"  - Primary Agent: {primary_agent}")
        
        # Execute appropriate collaboration strategy
        if collaboration_mode == "multi_perspective":
            print("\nGathering multi-perspective analysis...")
            # Get all relevant agent perspectives concurrently (now with docs)
            agent_outputs = await self._get_all_perspectives_async(current_query)
            agent_responses = {k: v["response"] for k, v in agent_outputs.items()}
            all_docs = []
            for v in agent_outputs.values():
                all_docs.extend(v["retrieved_docs"])
            state["agent_responses"] = agent_responses
            state["consulting_agents"] = list(agent_responses.keys())
            state["retrieved_docs"] = all_docs  # Aggregate docs for workflow state
            print(f"  - Consulting Agents: {', '.join(state['consulting_agents'])}")
            final_response = await self._synthesize_perspectives_async(agent_responses, current_query)
            
        elif collaboration_mode == "consultation":
            print("\nGathering expert consultation...")
            # Primary agent with consultation from others
            consultation = await self._get_consultation_async(primary_agent, current_query)
            other_agents = [agent for agent in self.agents.keys() if agent != primary_agent]
            state["consulting_agents"] = [primary_agent] + other_agents[:1]
            print(f"  - Primary Agent: {primary_agent}")
            print(f"  - Consulting Agent: {other_agents[0]}")
            final_response = await self._get_enhanced_primary_response_async(primary_agent, current_query, consultation)
            
        else:
            # This should never happen - raise an exception
            raise ValueError(f"Invalid collaboration mode: {collaboration_mode}. Expected 'multi_perspective' or 'consultation'")
        
        # Update state with collaborative response
        state["messages"].append(AIMessage(content=final_response))
        state["collaboration_confidence"] = 0.9
        state["agent_type"] = "team_collaboration"
        
        print("\nCollaboration Complete:")
        print(f"  - Final Agent Type: {state['agent_type']}")
        print(f"  - Team Confidence: {state['collaboration_confidence']}")
        print("-" * 40)
        
        return state
    
    async def _synthesize_perspectives_async(self, responses: Dict[str, str], query: str) -> str:
        """Synthesize multiple agent perspectives into a cohesive response"""
        print("\nSynthesizing Perspectives:")
        print("-" * 40)
        print("  - Combining insights from all agents...")
            
        # Create a prompt that includes all perspectives
        perspectives = "\n\n".join([f"{agent}: {response}" for agent, response in responses.items()])
        synthesis_prompt = f"""Synthesize the following perspectives into a cohesive response to the query: "{query}"

Perspectives:
{perspectives}

Provide a comprehensive response that integrates all relevant insights while maintaining clarity and coherence."""

        # Use the synthesis agent to combine perspectives
        synthesis_response = await self.llm.ainvoke([HumanMessage(content=synthesis_prompt)])
        final_response = synthesis_response.content
        
        print("  - Synthesis complete")
        print("-" * 40)
        return final_response

    async def _get_enhanced_primary_response_async(self, primary_agent: str, query: str, consultation: Dict[str, str]) -> str:
        """Get enhanced response from primary agent with consultation"""
        print("\nEnhancing Primary Response:")
        print("-" * 40)
        print(f"  - Primary Agent: {primary_agent}")
        
        # Get primary agent's response
        state = {"messages": [HumanMessage(content=query)]}
        primary_response = await self.agents[primary_agent].process_async(state)
        primary_content = primary_response["messages"][-1].content
        
        # Create enhancement prompt
        consultation_text = "\n\n".join([f"{agent}: {response}" for agent, response in consultation.items()])
        enhancement_prompt = f"""Enhance the primary response with insights from the consultation.

Primary Response:
{primary_content}

Consultation:
{consultation_text}

Provide an enhanced response that incorporates relevant insights from the consultation while maintaining the primary perspective."""

        # Use the synthesis agent to enhance the response
        enhanced_response = await self.llm.ainvoke([HumanMessage(content=enhancement_prompt)])
        final_response = enhanced_response.content
        
        print("  - Enhancement complete")
        print("-" * 40)
        return final_response
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from .state import AgentState
from typing import Dict

class CollaborationSystem:
    def __init__(self, ir_agent, ti_agent, prevention_agent):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        self.agents = {
            "incident_response": ir_agent,
            "threat_intelligence": ti_agent,
            "prevention": prevention_agent
        }
    def multi_agent_consultation(self, state: AgentState) -> AgentState:
        """Execute multi-agent collaboration based on collaboration mode"""
        
        # Extract the user's query from conversation history
        current_query = ""
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                current_query = msg.content
                break
        
        # Get collaboration strategy from state
        collaboration_mode = state.get("collaboration_mode", "single_agent")
        primary_agent = state.get("primary_agent")
        
        # Execute appropriate collaboration strategy
        if collaboration_mode == "multi_perspective":
            # Get all relevant agent perspectives
            agent_responses = self._get_all_perspectives(current_query)
            state["agent_responses"] = agent_responses
            state["consulting_agents"] = list(agent_responses.keys())
            final_response = self._synthesize_perspectives(agent_responses, current_query)
            
        elif collaboration_mode == "consultation":
            # Primary agent with consultation from others
            consultation = self._get_consultation(primary_agent, current_query)
            other_agents = [agent for agent in self.agents.keys() if agent != primary_agent]
            state["consulting_agents"] = [primary_agent] + other_agents[:1]
            final_response = self._get_enhanced_primary_response(primary_agent, current_query, consultation)
            
        else:
            # Fallback - shouldn't happen with proper routing
            final_response = "Error: Unknown collaboration mode"
        
        # Update state with collaborative response
        state["messages"].append(AIMessage(content=final_response))
        state["collaboration_confidence"] = 0.9
        state["agent_type"] = "team_collaboration"
        
        return state
    
    def _get_all_perspectives(self, query: str) -> Dict[str, str]:
        """Get perspective from all three agents for multi-perspective analysis"""
        perspectives = {}
        
        # Iterate through each agent to get their expert perspective
        for agent_type, agent in self.agents.items():
            # Create role-specific consultation prompt
            prompt = f"As a {agent_type.replace('_', ' ')} expert, provide your key insights on: {query}\n\nBe concise but actionable (2-3 main points)."
            
            # Use agent's specialized search tool to get relevant context
            search_results = agent.search_tool.invoke({"query": query})
            
            # Extract content from search results (handle tuple format from vector store)
            context_parts = []
            for result in search_results[:2]:  # Top 2 results for context
                if isinstance(result, tuple):
                    doc, score = result
                    context_parts.append(doc.page_content)
                else:
                    context_parts.append(result.page_content)
            
            context = "\n".join(context_parts)
            
            # Construct messages with agent's system prompt and context
            messages = [
                SystemMessage(content=agent.system_prompt),
                HumanMessage(content=f"Context: {context}\n\n{prompt}")
            ]
            
            # Get agent's perspective
            response = self.llm.invoke(messages)
            perspectives[agent_type] = response.content
        
        return perspectives
    def _synthesize_perspectives(self, perspectives: Dict[str, str], query: str) -> str:
        """Combine all agent perspectives into a unified team response"""
        
        # User-friendly agent names with emojis
        agent_names = {
            "incident_response": "🚨 Incident Response",
            "threat_intelligence": "🕵️ Threat Intelligence", 
            "prevention": "🛡️ Prevention & Architecture"
        }
        
        # Build response with clear sections for each expert
        response_parts = ["**🤝 Cybersecurity Team Analysis**\n"]
        
        # Add each agent's perspective as a labeled section
        for agent_type, content in perspectives.items():
            agent_name = agent_names.get(agent_type, agent_type)
            response_parts.append(f"**{agent_name}:**\n{content}\n")
        
        # Create synthesis prompt to integrate all perspectives
        synthesis_prompt = f"""Based on these expert perspectives, provide a unified team recommendation for: {query}

    Expert Input:
    {chr(10).join([f"{k}: {v}" for k, v in perspectives.items()])}

    Provide a concise team recommendation that integrates the key insights."""
        
        # Get AI-synthesized team conclusion
        synthesis_response = self.llm.invoke([HumanMessage(content=synthesis_prompt)])
        response_parts.append(f"**🎯 Team Recommendation:**\n{synthesis_response.content}")
        
        return "\n".join(response_parts)
    def _get_consultation(self, primary_agent: str, query: str) -> str:
        """Get consultation input from other agents for the primary agent"""
        
        # Get list of agents excluding the primary agent
        other_agents = [agent for agent in self.agents.keys() if agent != primary_agent]
        consultations = []
        
        # Get consultation from one other agent (keep it simple)
        for agent_type in other_agents[:1]:
            agent = self.agents[agent_type]
            
            # Create consultation-specific prompt
            prompt = f"Provide consultation input for the {primary_agent.replace('_', ' ')} team on: {query}\n\nFocus on insights from your domain that would help their analysis."
            
            # Get context from the consulting agent's knowledge base
            search_results = agent.search_tool.invoke({"query": query})
            context_parts = []
            for result in search_results[:2]:
                if isinstance(result, tuple):
                    doc, score = result
                    context_parts.append(doc.page_content)
                else:
                    context_parts.append(result.page_content)
            
            context = "\n".join(context_parts)
            
            # Get consultation response
            messages = [
                SystemMessage(content=agent.system_prompt),
                HumanMessage(content=f"Context: {context}\n\n{prompt}")
            ]
            
            response = self.llm.invoke(messages)
            consultations.append(f"{agent_type.replace('_', ' ').title()}: {response.content}")
        
        return "\n\n".join(consultations)
    def _get_enhanced_primary_response(self, primary_agent: str, query: str, consultation: str) -> str:
        """Get primary agent response enhanced with consultation from other experts"""
        
        agent = self.agents[primary_agent]
        
        # Get primary agent's specialized context
        search_results = agent.search_tool.invoke({"query": query})
        context_parts = []
        for result in search_results[:3]:  # Slightly more context for primary agent
            if isinstance(result, tuple):
                doc, score = result
                context_parts.append(doc.page_content)
            else:
                context_parts.append(result.page_content)
        
        context = "\n".join(context_parts)
        
        # Create enhanced prompt that includes consultation input
        enhanced_prompt = f"""Provide expert analysis incorporating team consultation.

    Your expertise context: {context}

    Team consultation: {consultation}

    Query: {query}

    Provide comprehensive response leveraging both your specialized expertise and the team input."""
        
        # Get enhanced primary agent response
        messages = [
            SystemMessage(content=agent.system_prompt),
            HumanMessage(content=enhanced_prompt)
        ]
        
        response = self.llm.invoke(messages)
        
        # Format with clear indication of enhanced analysis
        agent_title = primary_agent.replace('_', ' ').title()
        return f"**🎯 Enhanced {agent_title} Analysis (with team consultation):**\n\n{response.content}"
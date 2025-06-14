from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.language_models.chat_models import BaseChatModel
from .state import AgentState
from typing import Dict, Any, List
import asyncio

class CollaborationSystem:
    def __init__(self, ir_agent, ti_agent, prevention_agent, llm_map: Dict[str, BaseChatModel]):
        self.llm_map = llm_map
        self.agents = {
            "incident_response": ir_agent,
            "threat_intelligence": ti_agent,
            "prevention": prevention_agent
        }

    async def multi_agent_consultation_async(self, state: AgentState) -> AgentState:
        """Execute multi-agent collaboration based on collaboration mode"""

        print("\n🤝 Collaboration Process:")
        print("-" * 40)

        current_query = ""
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                current_query = msg.content
                break

        print(f"Processing query: {current_query}")

        collaboration_mode = state.get("collaboration_mode")
        if not collaboration_mode:
            raise ValueError("No collaboration mode specified in state")

        primary_agent = state.get("primary_agent")
        
        llm_choice = state.get("llm_choice", "openai_mini")
        self.llm = self.llm_map.get(llm_choice, self.llm_map["openai_mini"])

        print("\nCollaboration Strategy:")
        print(f"  - Mode: {collaboration_mode}")
        print(f"  - Primary Agent: {primary_agent if primary_agent else 'None'}")
        print(f"  - Collaboration System LLM: {llm_choice}")

        agent_responses: Dict[str, str] = {}
        consulting_agents: List[str] = []

        if collaboration_mode == "multi_perspective":
            print("  - Executing Multi-Perspective Collaboration")
            tasks = []
            for agent_name, agent_instance in self.agents.items():
                print(f"    - Consulting {agent_name}...")
                consulting_agents.append(agent_name)
                consult_state = AgentState(messages=[HumanMessage(content=current_query)],
                                          llm_choice=llm_choice,
                                          agent_type=None, retrieved_docs=[], confidence_score=0.0,
                                          conversation_summary="", collaboration_mode="", consulting_agents=[],
                                          agent_responses={}, needs_collaboration=False, primary_agent=None,
                                          collaboration_confidence=None, thought_process=[], needs_web_search=False,
                                          thread_id=state.get("thread_id")
                                          )
                tasks.append(agent_instance.process_async(consult_state))
            
            consultation_results = await asyncio.gather(*tasks)
            for res in consultation_results:
                agent_name = res["agent_type"]
                response_content = ""
                for msg in reversed(res["messages"]):
                    if isinstance(msg, AIMessage):
                        response_content = msg.content
                        break
                agent_responses[agent_name] = response_content
                state["thought_process"].append(f"Multi-perspective: {agent_name} provided insights.")

            final_response = await self._synthesize_multi_perspective_response_async(current_query, agent_responses)
            state["collaboration_confidence"] = self._calculate_collaboration_confidence(agent_responses)


        elif collaboration_mode == "consultation" and primary_agent:
            print(f"  - Executing Consultation Mode with {primary_agent} as primary")
            consulting_agents = [name for name in self.agents if name != primary_agent]

            print(f"    - Getting initial response from {primary_agent}...")
            primary_state = AgentState(messages=[HumanMessage(content=current_query)],
                                       llm_choice=llm_choice,
                                       agent_type=None, retrieved_docs=[], confidence_score=0.0,
                                       conversation_summary="", collaboration_mode="", consulting_agents=[],
                                       agent_responses={}, needs_collaboration=False, primary_agent=None,
                                       collaboration_confidence=None, thought_process=[], needs_web_search=False,
                                       thread_id=state.get("thread_id")
                                       )
            primary_response_state = await self.agents[primary_agent].process_async(primary_state)
            primary_response_content = ""
            for msg in reversed(primary_response_state["messages"]):
                if isinstance(msg, AIMessage):
                    primary_response_content = msg.content
                    break
            agent_responses[primary_agent] = primary_response_content
            state["thought_process"].append(f"Consultation: {primary_agent} provided initial response.")

            consultation_tasks = []
            for agent_name in consulting_agents:
                print(f"    - {agent_name} consulting on {primary_agent}'s response...")
                consultation_prompt = f"""Review the following initial response from the {primary_agent} agent:

Initial Response:
{primary_response_content}

Your task as a {agent_name} specialist is to provide additional insights, confirm, or raise concerns regarding this response based on your expertise. Focus on adding value from your unique perspective.
"""
                consult_state = AgentState(messages=[HumanMessage(content=consultation_prompt)],
                                           llm_choice=llm_choice,
                                           agent_type=None, retrieved_docs=[], confidence_score=0.0,
                                           conversation_summary="", collaboration_mode="", consulting_agents=[],
                                           agent_responses={}, needs_collaboration=False, primary_agent=None,
                                           collaboration_confidence=None, thought_process=[], needs_web_search=False,
                                           thread_id=state.get("thread_id")
                                           )
                consultation_tasks.append(self.agents[agent_name].process_async(consult_state))
            
            consultation_results = await asyncio.gather(*consultation_tasks)
            for res in consultation_results:
                agent_name = res["agent_type"]
                response_content = ""
                for msg in reversed(res["messages"]):
                    if isinstance(msg, AIMessage):
                        response_content = msg.content
                        break
                agent_responses[agent_name] = response_content
                state["thought_process"].append(f"Consultation: {agent_name} provided consultation on primary response.")

            final_response = await self._get_enhanced_primary_response_async(primary_agent, current_query, agent_responses)
            state["collaboration_confidence"] = self._calculate_collaboration_confidence(agent_responses)

        else:
            raise ValueError(f"Invalid collaboration mode '{collaboration_mode}' or missing primary agent for consultation.")

        state["messages"].append(AIMessage(content=final_response))
        state["agent_responses"] = agent_responses
        state["consulting_agents"] = consulting_agents
        state["needs_collaboration"] = False
        
        print("\nCollaboration Process Complete.")
        print("-" * 40)
        return state

    async def _synthesize_multi_perspective_response_async(self, query: str, perspectives: Dict[str, str]) -> str:
        """Synthesize a final response from multiple agent perspectives."""
        print("\nSynthesizing Multi-Perspective Response:")
        print("-" * 40)
        synthesis_prompt_content = f"""You are a master cybersecurity synthesizer. Your task is to integrate the following multiple agent perspectives into a single, comprehensive, and cohesive response to the user's original query.

Original User Query:
{query}

Agent Perspectives:
"""
        for agent, response in perspectives.items():
            synthesis_prompt_content += f"\n**{agent.replace('_', ' ').title()} Agent's Perspective:**\n{response}\n"

        synthesis_prompt_content += """
Provide a unified response that leverages insights from all relevant perspectives. Maintain a professional, informative, and actionable tone. Format the response using markdown for better readability. Use headings, lists, and bold text where appropriate. Ensure all key aspects of the original query are addressed comprehensively.
"""
        synthesis_response = await self.llm.ainvoke([HumanMessage(content=synthesis_prompt_content)])
        final_response = synthesis_response.content

        print("  - Synthesis complete")
        print("-" * 40)
        return final_response

    async def _get_enhanced_primary_response_async(self, primary_agent: str, query: str, consultation: Dict[str, str]) -> str:
        """Get enhanced response from primary agent with consultation"""
        print("\nEnhancing Primary Response:")
        print("-" * 40)
        print(f"  - Primary Agent: {primary_agent}")

        enhancement_prompt = f"""You are the lead {primary_agent.replace('_', ' ').title()} agent.
Your task is to provide a comprehensive and actionable response to the original user query, incorporating insights and feedback from the consulting agents.

Original User Query:
{query}

Consulting Agent Feedback:
"""
        consultation_feedback = {k: v for k, v in consultation.items() if k != primary_agent}
        
        if consultation_feedback:
            for agent, response in consultation_feedback.items():
                enhancement_prompt += f"\n**Feedback from {agent.replace('_', ' ').title()} Agent:**\n{response}\n"
        else:
            enhancement_prompt += "\nNo additional consultation feedback was provided."


        enhancement_prompt += """
Provide a final, enhanced response that addresses the user's query thoroughly, integrating relevant points from the consultations. Format the response using markdown for better readability. Use headings, lists, and bold text where appropriate.
"""
        enhanced_response = await self.llm.ainvoke([HumanMessage(content=enhancement_prompt)])
        final_response = enhanced_response.content

        print("  - Enhancement complete")
        print("-" * 40)
        return final_response

    def _calculate_collaboration_confidence(self, agent_responses: Dict[str, str]) -> float:
        """Calculates a collaboration confidence score based on consistency or completeness of responses."""
        total_chars = sum(len(resp) for resp in agent_responses.values())
        num_agents = len(agent_responses)
        
        if num_agents == 0:
            return 0.0
        
        avg_length_score = min(1.0, total_chars / (num_agents * 500))
        
        return round(avg_length_score, 2)
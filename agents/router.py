from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage, AIMessage
from .state import AgentState
import json

class RouterAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        
    def router_query(self, state: AgentState) -> AgentState:
        """"Determine which speciliast agent should handle the query."""
        current_query_message = state["messages"][-1]
        query_content = current_query_message.content if isinstance(current_query_message, HumanMessage) else ""
        
        print("\n🤔 Router Analysis:")
        print("-" * 40)
        
        # Analyze collaboration needs
        collaboration_info = self._detect_collaboration_need(query_content)
        state["collaboration_mode"] = collaboration_info.get("mode")
        state["needs_collaboration"] = collaboration_info.get("needs_collaboration")
        
        print(f"Collaboration Detection:")
        print(f"  - Mode: {collaboration_info.get('mode')}")
        print(f"  - Needs Collaboration: {collaboration_info.get('needs_collaboration')}")
        
        all_messages = state["messages"]
        is_follow_up = self._detect_follow_up(query_content, all_messages[:-1])
        state["is_follow_up"] = is_follow_up
        
        print(f"Follow-up Detection: {is_follow_up}")
        
        if state.get("agent_type") and not state.get("needs_routing", True) and not is_follow_up:
            print("Using existing agent type (no re-routing needed)")
            return state
        
        print("\nAnalyzing query for specialist routing...")
        
        system_prompt = """You are a cybersecurity query router. Analyze the user's query and determine which specialist should handle it.

        Available specialists:
        - incident_response: For active security incidents, breaches, malware infections, ransomware, containment, investigation, forensics
        - threat_intelligence: For IOCs, threat actors, TTPs, vulnerability analysis, threat hunting, attribution
        - prevention: For security frameworks, policies, best practices, risk assessment, compliance, proactive security measures

        Consider if the query spans multiple domains or requires collaboration between specialists.

        Respond with only a JSON object in this format:
        {
            "agent_type": "incident_response|threat_intelligence|prevention",
            "confidence": 0.8,
            "reasoning": "Brief explanation",
            "requires_collaboration": false,
            "collaboration_agents": []
        }"""
        
        router_messages = [SystemMessage(content=system_prompt)]
        if is_follow_up:
            recent_context_messages = [
                m for m in all_messages if isinstance(m, (HumanMessage, AIMessage))
            ][-4:]
            router_messages.extend(recent_context_messages)
            
        router_messages.append(HumanMessage(content=f"Current Query: {query_content}"))
        
        response = self.llm.invoke(router_messages)
        
        try:
            routing_decision = json.loads(response.content)
            state["agent_type"] = routing_decision.get("agent_type")
            state["confidence_score"] = routing_decision.get("confidence")
            state["needs_routing"] = False
            
            print("\nRouting Decision:")
            print(f"  - Selected Agent: {routing_decision.get('agent_type')}")
            print(f"  - Confidence: {routing_decision.get('confidence')}")
            print(f"  - Reasoning: {routing_decision.get('reasoning')}")
            if routing_decision.get("requires_collaboration"):
                print(f"  - Collaboration Agents: {', '.join(routing_decision.get('collaboration_agents', []))}")
            
        except (json.JSONDecodeError, KeyError):
            state["agent_type"] = "prevention"  # Default to prevention for unclear queries
            state["confidence_score"] = 0.3
            state["needs_routing"] = False
            print("\n⚠️ Routing Error: Defaulting to prevention agent")
        
        print("-" * 40)
        return state
    
    def _detect_follow_up(self, query: str, conversation_history: list[BaseMessage]) -> bool:
        """Detect if the current query is a follow-up based on conversation history."""
        if len(conversation_history) <= 1:
            return False
        
        follow_up_indicators = [
            "this", "that", "it", "also", "what about", "how about",
            "tell me more", "expand", "clarify", "explain", "additionally",
            "furthermore", "regarding", "concerning", "about that"
        ]
        
        query_lower = query.lower()

        has_follow_up_phrase = any(indicator in query_lower for indicator in follow_up_indicators)

        is_short_question = len(query.split()) <= 8

        has_recent_context = len(conversation_history) > 1

        return has_follow_up_phrase or (is_short_question and has_recent_context)
    
    def _detect_collaboration_need(self, query: str) -> dict:
        """Detect collaboration needs and determine strategy"""
        query_lower = query.lower()
        
        # Multi-domain patterns
        multi_domain_indicators = [
            # Incident Response + Prevention
            ("respond" in query_lower and "prevent" in query_lower),
            ("handle" in query_lower and "prevent" in query_lower),
            ("deal with" in query_lower and "prevent" in query_lower),
            ("incident" in query_lower and "prevent" in query_lower),
            ("breach" in query_lower and "prevent" in query_lower),
            ("attack" in query_lower and "prevent" in query_lower),
            ("contain" in query_lower and "prevent" in query_lower),
            ("mitigate" in query_lower and "prevent" in query_lower),
            ("detect" in query_lower and "prevent" in query_lower),
            ("monitor" in query_lower and "prevent" in query_lower),
            ("alert" in query_lower and "prevent" in query_lower),
            
            # Investigation + Attribution
            ("investigate" in query_lower and "attribution" in query_lower),
            ("analyze" in query_lower and "attribution" in query_lower),
            ("determine" in query_lower and "attribution" in query_lower),
            ("identify" in query_lower and "attribution" in query_lower),
            ("trace" in query_lower and "attribution" in query_lower),
            ("track" in query_lower and "attribution" in query_lower),
            
            # Multiple domains in one query
            ("incident" in query_lower and "threat" in query_lower),
            ("breach" in query_lower and "threat" in query_lower),
            ("attack" in query_lower and "threat" in query_lower),
            ("prevent" in query_lower and "threat" in query_lower),
            ("detect" in query_lower and "threat" in query_lower),
            ("monitor" in query_lower and "threat" in query_lower),
            
            # General multi-domain indicators
            any(word in query_lower for word in [
                "comprehensive", "complete analysis", "multiple perspectives",
                "both", "and", "along with", "as well as", "in addition to",
                "not only", "but also", "while also", "together", "combined",
                "integrated", "holistic", "end-to-end", "full", "complete",
                "thorough", "detailed", "extensive", "comprehensive"
            ])
        ]
        
        # Complex query patterns
        complex_query_indicators = [
            # Complexity indicators
            "complex", "detailed analysis", "expert opinion", "best practice",
            "recommend", "suggest", "advise", "guidance", "strategy",
            "approach", "solution", "plan", "framework", "policy",
            "procedure", "process", "methodology", "standard",
            "comprehensive", "thorough", "detailed", "extensive",
            "complete", "full", "holistic", "integrated", "end-to-end",
            "best", "optimal", "effective", "efficient", "robust",
            "secure", "reliable", "resilient", "sustainable"
        ]
        
        # Check for multi-domain patterns
        if any(multi_domain_indicators):
            return {"mode": "multi_perspective", "needs_collaboration": True}
        
        # Check for complex query patterns
        if any(word in query_lower for word in complex_query_indicators):
            return {"mode": "consultation", "needs_collaboration": True}
        
        # Check for multiple agent types in the query
        agent_type_indicators = {
            "incident_response": [
                "incident", "breach", "attack", "respond", "handle", "contain",
                "detect", "alert", "investigate", "analyze", "forensics",
                "malware", "ransomware", "exploit", "vulnerability", "patch",
                "remediate", "recover", "restore", "backup"
            ],
            "threat_intelligence": [
                "threat", "intelligence", "ioc", "ttp", "attribution",
                "actor", "campaign", "malware", "ransomware", "exploit",
                "vulnerability", "zero-day", "apt", "advanced persistent threat",
                "indicator", "signature", "pattern", "behavior", "tactic",
                "technique", "procedure", "mitre", "attack"
            ],
            "prevention": [
                "prevent", "secure", "protect", "defend", "mitigate", "framework",
                "policy", "procedure", "standard", "guideline", "best practice",
                "control", "safeguard", "measure", "countermeasure", "defense",
                "security", "compliance", "audit", "assessment", "risk",
                "vulnerability", "threat", "exposure", "weakness"
            ]
        }
        
        # Count how many different agent types are mentioned
        mentioned_types = sum(
            1 for indicators in agent_type_indicators.values()
            if any(indicator in query_lower for indicator in indicators)
        )
        
        # If multiple agent types are mentioned, trigger collaboration
        if mentioned_types > 1:
            return {"mode": "multi_perspective", "needs_collaboration": True}
        
        # Check for high-stakes scenarios that might need collaboration
        high_stakes_indicators = [
            "critical", "severe", "serious", "major", "significant",
            "important", "crucial", "vital", "essential", "key",
            "sensitive", "confidential", "private", "restricted",
            "emergency", "urgent", "immediate", "priority", "high-priority",
            "high-risk", "high-value", "high-impact", "high-stakes"
        ]
        
        if any(word in query_lower for word in high_stakes_indicators):
            return {"mode": "consultation", "needs_collaboration": True}
        
        return {"mode": "single_agent", "needs_collaboration": False}
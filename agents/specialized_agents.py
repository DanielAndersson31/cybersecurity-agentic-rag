# agents/specialized_agents.py
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from .state import AgentState
from .tools import search_knowledge_base, web_search
from typing import Dict, List, Optional
import json

class BaseAgent:
    """Base class for specialized cybersecurity agents."""

    def __init__(self, agent_type: str, system_prompt: str, llm_map: Dict[str, BaseChatModel]):
        self.llm_map = llm_map
        self.tools = [search_knowledge_base, web_search]
        self.agent_type = agent_type
        self.system_prompt = system_prompt
        
    async def get_cybersecurity_intent_score(self, query: str) -> float:
        """Use the LLM to score how likely a query is cybersecurity-related (1.0) vs. not (0.0)."""
        system_prompt = (
            "You are an intent classifier for a cybersecurity assistant. "
            "Given a user query, respond ONLY with a number between 0.0 and 1.0. "
            "1.0 means the query is highly related to cybersecurity. "
            "0.0 means the query is not related to cybersecurity at all. "
            "Do not explain your answer.\n"
            "Here is a list of cybersecurity-related keywords and concepts: "
            "cybersecurity, malware, ransomware, phishing, threat intelligence, incident response, vulnerability, CVE, exploit, SIEM, firewall, intrusion, detection, prevention, attack, breach, data leak, encryption, authentication, access control, risk, compliance, NIST, MITRE, TTP, IOC, forensics, pentest, red team, blue team, zero-day, patch, security policy, endpoint, SOC, CISO, cybercrime, hacking, DDoS, botnet, rootkit, spyware, keylogger, vulnerability management, security framework, defense, mitigation, response, recovery, security awareness, password, MFA, privilege, escalation, social engineering, spearphishing, whaling, smishing, vishing, cyberattack, cyber defense, cyber threat, cyber risk, cyber hygiene, cyber law, cyber insurance, cyber policy, cyber incident, cyber investigation, cyber operations, cyber warfare, cyber espionage, cyber resilience, cyber safety, cyber strategy, cyber training, digital forensics, information security, network security, application security, cloud security, endpoint security, identity management, access management, security operations, security monitoring, security analytics, security automation, security orchestration, vulnerability assessment, vulnerability scanning, vulnerability remediation, vulnerability disclosure, vulnerability exploitation, vulnerability research, vulnerability scanning, vulnerability testing, vulnerability validation, vulnerability verification, vulnerability workflow, vulnerability workflow management, vulnerability workflow process, vulnerability workflow system, vulnerability workflow tool, vulnerability workflow automation, vulnerability workflow orchestration, vulnerability workflow platform, vulnerability workflow solution, vulnerability workflow software, vulnerability workflow service, vulnerability workflow provider, vulnerability workflow vendor, vulnerability workflow consultant, vulnerability workflow expert, vulnerability workflow specialist, vulnerability workflow engineer, vulnerability workflow analyst, vulnerability workflow manager, vulnerability workflow director, vulnerability workflow leader, vulnerability workflow architect, vulnerability workflow designer, vulnerability workflow developer, vulnerability workflow tester, vulnerability workflow auditor, vulnerability workflow assessor, vulnerability workflow reviewer, vulnerability workflow evaluator, vulnerability workflow investigator, vulnerability workflow responder, vulnerability workflow handler, vulnerability workflow coordinator, vulnerability workflow communicator, vulnerability workflow trainer, vulnerability workflow educator, vulnerability workflow mentor, vulnerability workflow coach, vulnerability workflow advisor. "
            "If the query is about any of these topics or closely related, score it higher. If it is not related, score it lower."
        )
        prompt = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User query: {query}")
        ]
        response = await self.llm.ainvoke(prompt)
        try:
            score = float(response.content.strip())
            return min(max(score, 0.0), 1.0)
        except Exception:
            return 0.5
    
    async def needs_web_search(self, query: str) -> bool:
        """Determine if a query needs web search based on temporal/current information needs."""
        system_prompt = (
            "You are a query analyzer. Determine if the following query requires current, real-time, or recent information that would need a web search. "
            "Respond with ONLY 'yes' or 'no'.\n"
            "Examples that need web search:\n"
            "- Current time, date, weather\n"
            "- Recent events, news, incidents\n"
            "- Latest versions, updates, releases\n"
            "- Current prices, rates, statistics\n"
            "- Recent vulnerabilities, exploits, threats\n"
            "- Anything with temporal indicators (today, now, latest, recent, current, 2024, etc.)\n"
            "Examples that don't need web search:\n"
            "- General concepts, definitions\n"
            "- Historical information\n"
            "- Technical explanations\n"
            "- Best practices that don't change frequently"
        )
        prompt = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Query: {query}")
        ]
        response = await self.llm.ainvoke(prompt)
        return response.content.strip().lower() == "yes"

    async def perform_web_search(self, query: str, agent_type: str) -> List[dict]:
        """Perform web search and return structured documents."""
        print("  - Performing web search...")
        # This now returns a list of dicts directly
        web_search_docs = await web_search.ainvoke({"query": query, "agent_type": agent_type})

        # Gracefully handle potential errors from the tool
        if web_search_docs and isinstance(web_search_docs[0], dict) and "error" in web_search_docs[0]:
            print(f"  - Web search failed: {web_search_docs[0]['error']}")
            return []
        
        if web_search_docs:
            print(f"  - Retrieved {len(web_search_docs)} web search documents.")
        else:
            print("  - No results parsed from web search.")
        
        return web_search_docs

    async def process_async(self, state: AgentState) -> AgentState:
        """Processes a query using the agent's specific LLM and tools."""
        print(f"\n⚙️ {self.agent_type.replace('_', ' ').title()} Agent Processing:")
        print("-" * 40)

        current_query = state["messages"][-1].content
        llm_choice = state.get("llm_choice", "openai_mini")
        self.llm = self.llm_map.get(llm_choice, self.llm_map["openai_mini"])
        history = state["messages"]

        intent_score = await self.get_cybersecurity_intent_score(current_query)
        print(f"Cybersecurity intent score: {intent_score:.2f}")
        state["thought_process"].append(f"Cybersecurity intent score: {intent_score:.2f}")

        needs_search = await self.needs_web_search(current_query)
        print(f"Needs web search: {needs_search}")
        state["thought_process"].append(f"Web search needed: {needs_search}")

        web_search_docs = []
        if needs_search:
            web_search_docs = await self.perform_web_search(current_query, self.agent_type)
            if web_search_docs:
                state["retrieved_docs"].extend(web_search_docs)
                state["thought_process"].append(f"Web search performed. Retrieved {len(web_search_docs)} documents.")

        knowledge_base_results = []
        if intent_score >= 0.3:
            print("  - Query is cybersecurity-related. Searching knowledge base...")
            knowledge_base_results = await search_knowledge_base.ainvoke({"query": current_query, "agent_type": self.agent_type})
            if knowledge_base_results:
                state["retrieved_docs"].extend(knowledge_base_results)
                state["thought_process"].append(f"Retrieved {len(knowledge_base_results)} docs from knowledge base.")
                print(f"  - Retrieved {len(knowledge_base_results)} docs from knowledge base.")
            else:
                state["thought_process"].append("No relevant docs found in knowledge base.")
                print("  - No relevant docs found in knowledge base.")
        else:
            print("  - Query is not cybersecurity-related. Skipping knowledge base search.")
            state["thought_process"].append("Non-cybersecurity query - skipped knowledge base search.")

        kb_context = "\n\n".join([
            f"Source: {doc.get('source', 'knowledge_base')}\n{doc.get('content', '')}" 
            for doc in state["retrieved_docs"] 
            if doc.get("source") != "web_search" and doc.get("content")
        ])
        
        web_context = "\n\n".join([
            f"{'🔐 TRUSTED ' if doc.get('is_trusted') else ''}Web Source: {doc.get('url', 'Unknown')}\nTitle: {doc.get('title', 'No title')}\n{doc.get('raw_content', doc.get('content', ''))}"
            for doc in state["retrieved_docs"]
            if doc.get("source") == "web_search"
        ])
        
        context = ""
        if web_context:
            context += f"=== WEB SEARCH RESULTS ===\n{web_context}\n\n"
        if kb_context:
            context += f"=== KNOWLEDGE BASE RESULTS ===\n{kb_context}\n\n"

        if not context.strip():
            context = "No specific context found. Provide a general answer based on your expertise."

        if intent_score < 0.3:
            response_prompt = "You are a helpful assistant. Use the provided context to answer the user's query. Be sure to reference and cite sources when appropriate."
        else:
            response_prompt = self.system_prompt

        history_without_current = history[:-1]
        human_message_with_context = HumanMessage(
            content=f"Context:\n{context}\n\nUser Query: {current_query}"
        )
        prompt_messages = [SystemMessage(content=response_prompt)] + history_without_current + [human_message_with_context]

        response = await self.llm.ainvoke(prompt_messages)
        final_answer = response.content

        state["messages"].append(AIMessage(content=final_answer))
        state["agent_type"] = self.agent_type
        state["confidence_score"] = self._calculate_confidence(final_answer, state["retrieved_docs"])
        
        print(f"  - Agent response generated. Confidence: {state['confidence_score']:.2f}")
        print(f"  - Total docs used: {len(state['retrieved_docs'])} (Web: {len(web_search_docs)}, KB: {len(knowledge_base_results)})")
        print(f"  - Query type: {'Cybersecurity' if intent_score >= 0.3 else 'Non-cybersecurity'}")
        print("-" * 40)
        
        return state

    def _calculate_confidence(self, response: str, docs: List[dict]) -> float:
        """Calculates a confidence score based on the response and retrieved documents."""
        score = 0.0
        if docs:
            score += 0.5
            
            web_docs = [d for d in docs if d.get("source") == "web_search"]
            kb_docs = [d for d in docs if d.get("source") != "web_search"]
            
            if web_docs:
                score += 0.2
                if any(d.get("is_trusted") for d in web_docs):
                    score += 0.1
            
            if kb_docs:
                score += 0.1
            
            response_lower = response.lower()
            for doc in docs[:5]:
                if doc.get("content"):
                    content_words = set(doc["content"].lower().split()[:20])
                    response_words = set(response_lower.split())
                    overlap = len(content_words & response_words)
                    if overlap > 5:
                        score += 0.05

        score = max(0.0, min(1.0, score))
        return score


class IncidentResponseAgent(BaseAgent):
    """An agent specializing in incident response."""
    def __init__(self, llm_map: Dict[str, BaseChatModel]):
        system_prompt = """You are an expert incident response specialist. 
        Based on the provided context (which includes BOTH web search results and knowledge base information), offer clear, actionable guidance for cybersecurity incident response.
        
        IMPORTANT: Always use information from web search results when available, especially for current threats and recent incidents.
        Focus on detection, containment, eradication, recovery, and post-incident analysis.

        **IMPORTANT**: Format your response using strict markdown for the best readability.

        Use the following structure:
        - Use `#` for the main title.
        - Use `##` for section headers (e.g., ## Detection, ## Containment).
        - Use `###` for sub-section headers.
        - Use bullet points (`*` or `-`) for lists of actions or items.
        - Use `**bold**` text for emphasis on critical terms.
        - When referencing web sources, mention them explicitly.
        """
        super().__init__(
            agent_type="incident_response",
            system_prompt=system_prompt,
            llm_map=llm_map
        )


class ThreatIntelligenceAgent(BaseAgent):
    """An agent specializing in threat intelligence."""
    def __init__(self, llm_map: Dict[str, BaseChatModel]):
        system_prompt = """You are an expert threat intelligence analyst. 
        Based on the provided context (which includes BOTH web search results and knowledge base information), provide detailed threat intelligence analysis.
        
        IMPORTANT: Prioritize current threat information from web search results, especially from trusted sources (marked with 🔐).
        Include IOCs, TTPs, attribution, and defensive recommendations.

        **IMPORTANT**: Format your response using strict markdown for the best readability.

        Use the following structure:
        - Use `#` for the main title.
        - Use `##` for section headers (e.g., ## Indicators of Compromise, ## TTPs).
        - Use `###` for sub-section headers.
        - Use bullet points (`*` or `-`) for lists of IOCs, TTPs, etc.
        - Use `**bold**` text for emphasis.
        - Cite web sources when using current threat intelligence.
        """
        super().__init__(
            agent_type="threat_intelligence",
            system_prompt=system_prompt,
            llm_map=llm_map
        )


class PreventionAgent(BaseAgent):
    """An agent specializing in cybersecurity prevention."""
    def __init__(self, llm_map: Dict[str, BaseChatModel]):
        system_prompt = """You are an expert cybersecurity architect and prevention specialist.
        Based on the provided context (which includes BOTH web search results and knowledge base information), provide comprehensive security frameworks, preventive measures, and best practices.
        
        IMPORTANT: Include latest security standards and frameworks from web search results, especially from trusted sources (marked with 🔐).
        Focus on proactive security and risk mitigation.

        **IMPORTANT**: Format your response using strict markdown for the best readability.

        Use the following structure:
        - Use `#` for the main title.
        - Use `##` for section headers (e.g., ## Security Frameworks, ## Best Practices).
        - Use `###` for sub-section headers.
        - Use bullet points (`*` or `-`) for lists of recommendations.
        - Use `**bold**` text for emphasis.
        - Reference current standards and frameworks found in web search.
        """
        super().__init__(
            agent_type="prevention",
            system_prompt=system_prompt,
            llm_map=llm_map
        )
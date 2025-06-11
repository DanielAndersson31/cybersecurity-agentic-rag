# cli.py
import argparse
from agents.workflow import CybersecurityRAGWorkflow
from datetime import datetime
import uuid
import asyncio

class CybersecurityRAGApp:
    def __init__(self):
        print("Initializing Cybersecurity RAG System...")
        self.workflow = CybersecurityRAGWorkflow()
        self.current_session_id = None
        print("System ready!")
    
    async def initialize(self):
        """Initialize the workflow with async components."""
        await self.workflow.initialize()
    
    async def run_cli(self):
        """Run the command line interface."""
        print("\n" + "="*60)
        print("🛡️  CYBERSECURITY RAG ASSISTANT")
        print("="*60)
        print("Ask any cybersecurity question and the system will automatically")
        print("route it to the most appropriate expert agent:")
        print("")
        print("🚨 Incident Response • 🕵️ Threat Intelligence • 🛡️ Prevention • 📚 General")
        print("")
        print("Special commands:")
        print("  /new     - Start a new conversation")
        print("  /history - View conversation history")
        print("  /clear   - Clear conversation history")
        print("  quit     - Exit the program")
        print("="*60)
        
        # Start a new session
        self._start_new_session()
        
        while True:
            try:
                # Get user input
                print("\n" + "-"*40)
                query = input("🔍 Ask your cybersecurity question: ").strip()
                
                if not query:
                    continue
                
                # Handle special commands
                if query.startswith('/'):
                    await self._handle_special_command(query)
                    continue
                    
                if query.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye! Stay secure! 🛡️")
                    break
                
                # Process the query - let the system auto-route
                print("\n🔄 Processing query...")
                result = await self.workflow.process_query(query, session_id=self.current_session_id)
                
                # Display results
                self._display_result(result)
                
            except KeyboardInterrupt:
                print("\n\nGoodbye! Stay secure! 🛡️")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                print("Please try again.")
    
    def _start_new_session(self):
        """Start a new conversation session."""
        self.current_session_id = str(uuid.uuid4())
        print(f"\n📝 Starting new conversation (Session ID: {self.current_session_id[:8]}...)")
    
    async def _handle_special_command(self, command: str):
        """Handle special CLI commands."""
        cmd = command.lower()
        
        if cmd == '/new':
            self._start_new_session()
        elif cmd == '/history':
            await self._show_conversation_history()
        elif cmd == '/clear':
            await self._clear_conversation_history()
        else:
            print(f"❌ Unknown command: {command}")
    
    async def _show_conversation_history(self):
        """Display the current conversation history."""
        if not self.current_session_id:
            print("No active conversation session.")
            return
            
        try:
            # Get the current state from the workflow
            state = await self.workflow.app.aget_state({"configurable": {"thread_id": self.current_session_id}})
            state = state.values
            
            if not state.get("messages"):
                print("No conversation history available.")
                return
                
            print("\n" + "="*60)
            print("📜 CONVERSATION HISTORY")
            print("="*60)
            
            for i in range(0, len(state["messages"]), 2):
                if i + 1 < len(state["messages"]):
                    user_msg = state["messages"][i]
                    agent_msg = state["messages"][i + 1]
                    
                    print(f"\n👤 You: {user_msg.content}")
                    print(f"🤖 Assistant: {agent_msg.content}")
                    print("-" * 40)
            
            print("="*60)
            
        except Exception as e:
            print(f"❌ Error retrieving conversation history: {e}")
    
    async def _clear_conversation_history(self):
        """Clear the current conversation history."""
        if not self.current_session_id:
            print("No active conversation session.")
            return
            
        try:
            # Start a new session to clear history
            self._start_new_session()
            print("✅ Conversation history cleared.")
        except Exception as e:
            print(f"❌ Error clearing conversation history: {e}")
    
    def _display_result(self, result: dict):
        """Display the query result in a formatted way."""
        # Map agent types to emojis for cleaner display
        agent_icons = {
            "incident_response": "🚨",
            "threat_intelligence": "🕵️", 
            "prevention": "🛡️",
            "shared": "📚"
        }
        
        agent_names = {
            "incident_response": "Incident Response Specialist",
            "threat_intelligence": "Threat Intelligence Analyst",
            "prevention": "Security Prevention Expert", 
            "shared": "General Cybersecurity Expert"
        }
        
        icon = agent_icons.get(result['agent_type'], "🤖")
        name = agent_names.get(result['agent_type'], result['agent_type'])
        
        print("\n" + "="*60)
        print("📋 RESPONSE")
        print("="*60)
        print(f"{icon} Expert: {name}")
        print(f"📊 Confidence: {result['confidence_score']:.0%}")
        print(f"📚 Sources: {result['num_docs_retrieved']} documents")
        print("\n" + "-"*40)
        print(result['response'])
        print("="*60)
    
    async def run_tests(self):
        """Run predefined test queries to verify system functionality."""
        print("🧪 Running agentic routing tests...")
        
        test_queries = [
            "How do I respond to a ransomware attack?",
            "What are common indicators of compromise for APT groups?", 
            "What security frameworks should a startup implement?",
            "How does PowerShell work in cyberattacks?",
            "What is the MITRE ATT&CK framework?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n{'='*60}")
            print(f"🧪 TEST {i}/5: {query}")
            print("-" * 60)
            
            try:
                # Let the system auto-route each query
                result = await self.workflow.process_query(query)
                self._display_result(result)
            except Exception as e:
                print(f"❌ Test failed: {e}")
        
        print(f"\n🎉 Agentic routing tests completed!")

async def main():
    """Main entry point with basic argument parsing."""
    parser = argparse.ArgumentParser(
        description="Cybersecurity Agentic RAG System - AI agents that automatically route queries to domain experts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This agentic system automatically routes cybersecurity questions to specialized experts:

🚨 Incident Response Agent: Active security incidents, breaches, malware response
🕵️ Threat Intelligence Agent: IOCs, threat actors, TTPs, attack analysis  
🛡️ Prevention Agent: Security frameworks, policies, risk management
📚 General Expert: Broad cybersecurity knowledge and concepts

The system uses intelligent routing to automatically select the best expert
for each question, combined with retrieval-augmented generation (RAG) to
provide accurate, contextual responses from a cybersecurity knowledge base.

Examples of questions:
- "Help! We have a ransomware infection"
- "What are common phishing indicators?"  
- "Which security framework should we implement?"
- "How does SSL/TLS encryption work?"

Usage:
  python cli.py           # Start interactive mode
  python cli.py --test    # Test the agentic routing system
        """
    )
    
    parser.add_argument(
        '--test', 
        action='store_true',
        help='Run test queries to verify agentic routing functionality'
    )
    
    parser.add_argument(
        '--version', 
        action='version', 
        version='Cybersecurity Agentic RAG System v1.0.0'
    )
    
    args = parser.parse_args()
    
    # Initialize the application
    app = CybersecurityRAGApp()
    await app.initialize()
    
    # Handle different modes
    if args.test:
        # Run agentic routing tests
        await app.run_tests()
    else:
        # Interactive mode (default)
        await app.run_cli()

if __name__ == "__main__":
    asyncio.run(main())
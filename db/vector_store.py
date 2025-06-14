from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from .document_processor import process_all_documents
from pathlib import Path
import asyncio
import torch

device = "cuda" if torch.cuda.is_available() else "cpu"

class DatabaseManager:
    """Manages vector database operations including creation, population, and testing."""
    
    def __init__(self, persist_directory: str = "data/embeddings/chroma_db", collection_name: str = "cybersecurity_knowledge"):
        # Use default path if persist_directory is None
        self.persist_directory = Path(persist_directory if persist_directory is not None else "data/embeddings/chroma_db")
        self.collection_name = collection_name
        self.vector_store = None
        
        # Initialize embeddings with optimized settings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-large-en-v1.5",
            model_kwargs={
                'device': device,
                'trust_remote_code': True  
            },
            encode_kwargs={
                'normalize_embeddings': True,
                'batch_size': 128 if device == "cuda" else 32, 
                'show_progress_bar': True
            },
            show_progress=True
        )
    
    def _create_vector_store(self) -> Chroma:
        """Create and return a Chroma vector store with BAAI/Bge-large-en-v1.5 embeddings."""
        try:
            # Ensure the directory exists
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            
            vector_store = Chroma(
                persist_directory=str(self.persist_directory),
                embedding_function=self.embeddings
            )
            return vector_store
        except Exception as e:
            raise ValueError(f"Error creating vector store: {e}")

    def populate_database(self):
        """Populate the vector store with processed documents."""
        try:
            print("Processing all documents for vector store population...")
            
            # Get processed documents
            all_documents, all_metadatas, all_ids = process_all_documents()
            
            if not all_documents:
                print("No documents to add to the vector store.")
                return False
                
            print(f"Creating vector store from {len(all_documents)} documents...")
            
            # Create vector store from documents
            self.vector_store = Chroma.from_texts(
                texts=all_documents,
                metadatas=all_metadatas,
                embedding=self.embeddings,
                persist_directory=str(self.persist_directory),
                collection_name=self.collection_name,
                ids=all_ids
            )
            
            # Note: Chroma automatically persists when persist_directory is specified
            print(f"Vector store populated with {len(all_documents)} documents")
            return True
            
        except Exception as e:
            print(f"Error populating vector store: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_vector_store(self) -> Chroma:
        """Get the existing vector store or create a new one."""
        if not self.vector_store:
            self.vector_store = self._create_vector_store()
        return self.vector_store
    
    def setup_database(self):
        """Setup and populate the vector database."""
        print("Setting up cybersecurity knowledge database...")
        
        if self.populate_database():
            print("Vector store populated successfully!")
            return True
        else:
            print("Failed to populate vector store.")
            return False
    
    def _perform_search(self, query: str, agent_type: str = None, k: int = 5):
        """Internal method to perform the actual search with filtering."""
        if not self.vector_store:
            self.vector_store = self.get_vector_store()
        
        # Only filter if agent_type is specified
        where_filter = {"agent_type": agent_type} if agent_type else None
        
        try:
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=k,
                filter=where_filter
            )
            return results
        except Exception as e:
            print(f"Search error: {e}")
            return []

    def search(self, query: str, agent_type: str = None, k: int = 5):
        """Synchronous search method."""
        return self._perform_search(query, agent_type, k)

    async def asearch(self, query: str, agent_type: str = None, k: int = 5):
        """Async wrapper for the search method."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self._perform_search(query, agent_type, k)
        )
    
    def test_searches(self):
        """Test search functionality for different agent types."""
        if not self.vector_store:
            print("Vector store not initialized. Run setup_database() first.")
            return
            
        print("\nTesting search functionality:")
        
        search_queries = {
            "Incident Response": ("ransomware response", "incident_response"),
            "Threat Intelligence": ("malicious IP", "threat_intelligence"), 
            "Prevention": ("security framework", "prevention"),
            "Shared Knowledge": ("PowerShell", "shared")
        }

        for search_name, (query, agent_type) in search_queries.items():
            print(f"\n--- {search_name} Search (Query: '{query}', Agent Type: '{agent_type}') ---")
            
            results = self.search(query, agent_type, k=2)
            
            if results:
                print(f"Found {len(results)} results:")
                for i, result in enumerate(results):
                    if isinstance(result, tuple):  # (doc, score)
                        doc, score = result
                        print(f"  Result {i+1} (Score: {score:.4f}):")
                        print(f"    Metadata: {doc.metadata}")
                        content = doc.page_content
                    else:  # just doc
                        doc = result
                        print(f"  Result {i+1}:")
                        print(f"    Metadata: {doc.metadata}")
                        content = doc.page_content
                    
                    print(f"    Document: {content[:200]}{'...' if len(content) > 200 else ''}")
                    print("-" * 20)
            else:
                print("No results found.") 
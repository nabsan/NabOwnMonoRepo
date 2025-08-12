#!/usr/bin/env python3
"""
MCP server for RAG (Retrieval Augmented Generation) using Qdrant vector database
"""

import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests
from mcp.server.fastmcp import FastMCP

# Qdrant configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "http://172.21.32.1:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "rag_collection")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://172.21.32.1:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

# Initialize FastMCP server
mcp = FastMCP("rag-qdrant-server")

class QdrantRAGClient:
    def __init__(self):
        self.qdrant_url = QDRANT_HOST
        self.collection_name = QDRANT_COLLECTION
        self.ollama_url = OLLAMA_HOST
        self.embedding_model = EMBEDDING_MODEL
    
    def _get_embeddings(self, text: str) -> List[float]:
        """Get embeddings from Ollama"""
        try:
            payload = {
                "model": self.embedding_model,
                "prompt": text
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("embedding", [])
            
        except Exception as e:
            print(f"Error getting embeddings: {e}")
            return []
    
    def _ensure_collection_exists(self) -> bool:
        """Ensure the Qdrant collection exists"""
        try:
            # Check if collection exists
            response = requests.get(f"{self.qdrant_url}/collections/{self.collection_name}")
            
            if response.status_code == 200:
                return True
            elif response.status_code == 404:
                # Create collection
                collection_config = {
                    "vectors": {
                        "size": 768,  # Default size for nomic-embed-text
                        "distance": "Cosine"
                    }
                }
                
                create_response = requests.put(
                    f"{self.qdrant_url}/collections/{self.collection_name}",
                    json=collection_config
                )
                
                return create_response.status_code in [200, 201]
            else:
                return False
                
        except Exception as e:
            print(f"Error ensuring collection exists: {e}")
            return False
    
    def add_document(self, text: str, metadata: Dict[str, Any] = None) -> bool:
        """Add a document to the Qdrant collection"""
        try:
            if not self._ensure_collection_exists():
                return False
            
            # Get embeddings
            embeddings = self._get_embeddings(text)
            if not embeddings:
                return False
            
            # Create document ID based on content hash
            doc_id = hashlib.sha256(text.encode()).hexdigest()[:16]
            
            # Prepare metadata
            if metadata is None:
                metadata = {}
            
            metadata.update({
                "text": text,
                "timestamp": datetime.now().isoformat(),
                "doc_id": doc_id
            })
            
            # Upload to Qdrant
            point = {
                "id": doc_id,
                "vector": embeddings,
                "payload": metadata
            }
            
            response = requests.put(
                f"{self.qdrant_url}/collections/{self.collection_name}/points",
                json={
                    "points": [point]
                }
            )
            
            return response.status_code in [200, 201]
            
        except Exception as e:
            print(f"Error adding document: {e}")
            return False
    
    def search_documents(self, query: str, limit: int = 5, score_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """Search for similar documents in Qdrant"""
        try:
            if not self._ensure_collection_exists():
                return []
            
            # Get query embeddings
            query_embeddings = self._get_embeddings(query)
            if not query_embeddings:
                return []
            
            # Search in Qdrant
            search_payload = {
                "vector": query_embeddings,
                "limit": limit,
                "score_threshold": score_threshold,
                "with_payload": True
            }
            
            response = requests.post(
                f"{self.qdrant_url}/collections/{self.collection_name}/points/search",
                json=search_payload
            )
            
            if response.status_code != 200:
                return []
            
            results = response.json().get("result", [])
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.get("id"),
                    "score": result.get("score", 0),
                    "text": result.get("payload", {}).get("text", ""),
                    "metadata": {k: v for k, v in result.get("payload", {}).items() if k != "text"}
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching documents: {e}")
            return []
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection"""
        try:
            response = requests.get(f"{self.qdrant_url}/collections/{self.collection_name}")
            
            if response.status_code == 200:
                return response.json().get("result", {})
            else:
                return {"error": f"Collection not found or error: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Error getting collection info: {e}"}

# Initialize RAG client
rag_client = QdrantRAGClient()

@mcp.tool()
def add_text_document(text: str, title: str = "", source: str = "", tags: str = "") -> str:
    """
    Add a text document to the RAG collection.
    
    Args:
        text (str): The text content to add
        title (str): Optional title for the document
        source (str): Optional source information
        tags (str): Optional comma-separated tags
    
    Returns:
        str: Success or error message
    """
    try:
        if not text.strip():
            return "❌ Error: Text content cannot be empty."
        
        # Prepare metadata
        metadata = {}
        if title:
            metadata["title"] = title
        if source:
            metadata["source"] = source
        if tags:
            metadata["tags"] = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # Add document
        success = rag_client.add_document(text, metadata)
        
        if success:
            doc_length = len(text)
            return f"""✅ Document added successfully to RAG collection!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 Title: {title or "Untitled"}
📝 Length: {doc_length} characters
🏷️  Tags: {tags or "None"}
📂 Source: {source or "Not specified"}
🗃️  Collection: {QDRANT_COLLECTION}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        else:
            return "❌ Error: Failed to add document to RAG collection."
            
    except Exception as e:
        return f"❌ Error adding document: {str(e)}"

@mcp.tool()
def search_rag_documents(query: str, limit: int = 5, min_score: float = 0.5) -> str:
    """
    Search for relevant documents in the RAG collection.
    
    Args:
        query (str): Search query
        limit (int): Maximum number of results to return (default: 5)
        min_score (float): Minimum similarity score (0.0-1.0, default: 0.5)
    
    Returns:
        str: Search results
    """
    try:
        if not query.strip():
            return "❌ Error: Search query cannot be empty."
        
        # Search documents
        results = rag_client.search_documents(query, limit, min_score)
        
        if not results:
            return f"""🔍 No documents found for query: "{query}"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Try:
- Using different keywords
- Lowering the minimum score (currently: {min_score})
- Checking if documents are added to the collection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        # Format results
        result_text = f"""🔍 Found {len(results)} relevant document(s) for: "{query}"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        for i, result in enumerate(results, 1):
            score = result.get("score", 0)
            text = result.get("text", "")
            metadata = result.get("metadata", {})
            
            # Truncate long text
            display_text = text[:300] + "..." if len(text) > 300 else text
            
            result_text += f"""

📄 Result {i} (Score: {score:.3f})
Title: {metadata.get("title", "Untitled")}
Source: {metadata.get("source", "Not specified")}
Tags: {", ".join(metadata.get("tags", [])) or "None"}

Content:
{display_text}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        return result_text
        
    except Exception as e:
        return f"❌ Error searching documents: {str(e)}"

@mcp.tool()
def get_rag_collection_info() -> str:
    """
    Get information about the RAG collection.
    
    Returns:
        str: Collection information
    """
    try:
        info = rag_client.get_collection_info()
        
        if "error" in info:
            return f"❌ {info['error']}"
        
        # Extract useful information
        vectors_count = info.get("vectors_count", 0)
        config = info.get("config", {})
        vector_config = config.get("params", {}).get("vectors", {})
        
        return f"""📊 RAG Collection Information
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🗃️  Collection: {QDRANT_COLLECTION}
🌐 Qdrant Host: {QDRANT_HOST}
📄 Documents: {vectors_count}
🔢 Vector Size: {vector_config.get('size', 'Unknown')}
📏 Distance Metric: {vector_config.get('distance', 'Unknown')}
🤖 Embedding Model: {EMBEDDING_MODEL}
🔗 Ollama Host: {OLLAMA_HOST}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
    except Exception as e:
        return f"❌ Error getting collection info: {str(e)}"

@mcp.tool()
def answer_with_rag(question: str, search_limit: int = 3, min_score: float = 0.6) -> str:
    """
    Answer a question using RAG (Retrieval Augmented Generation).
    This tool searches for relevant documents and uses them to provide context for answering.
    
    Args:
        question (str): The question to answer
        search_limit (int): Number of documents to retrieve for context (default: 3)
        min_score (float): Minimum similarity score for retrieved documents (default: 0.6)
    
    Returns:
        str: Answer based on retrieved documents
    """
    try:
        if not question.strip():
            return "❌ Error: Question cannot be empty."
        
        # Search for relevant documents
        results = rag_client.search_documents(question, search_limit, min_score)
        
        if not results:
            return f"""🤷 No relevant documents found to answer: "{question}"

Try:
- Adding relevant documents to the collection first
- Using different keywords
- Lowering the minimum score threshold"""
        
        # Combine retrieved documents as context
        context_parts = []
        for i, result in enumerate(results, 1):
            text = result.get("text", "")
            metadata = result.get("metadata", {})
            title = metadata.get("title", f"Document {i}")
            
            context_parts.append(f"Document {i} ({title}):\n{text}")
        
        context = "\n\n".join(context_parts)
        
        # Format the response with retrieved context
        response = f"""🤖 Answer based on {len(results)} retrieved document(s):

📚 Retrieved Context:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{context}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❓ Question: {question}

💡 Based on the retrieved documents above, here's what I found relevant to your question. The documents contain information that may help answer your query. Please review the context provided to get detailed information."""
        
        return response
        
    except Exception as e:
        return f"❌ Error in RAG answering: {str(e)}"

if __name__ == "__main__":
    # Test connection on startup
    try:
        print(f"🔍 Testing Qdrant connection at {QDRANT_HOST}")
        response = requests.get(f"{QDRANT_HOST}/collections", timeout=5)
        if response.status_code == 200:
            print("✅ Qdrant connection successful")
        else:
            print(f"⚠️  Qdrant connection warning: HTTP {response.status_code}")
    except Exception as e:
        print(f"⚠️  Qdrant connection error: {e}")
    
    try:
        print(f"🔍 Testing Ollama embeddings at {OLLAMA_HOST}")
        test_response = requests.post(
            f"{OLLAMA_HOST}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": "test"},
            timeout=10
        )
        if test_response.status_code == 200:
            print("✅ Ollama embeddings connection successful")
        else:
            print(f"⚠️  Ollama embeddings warning: HTTP {test_response.status_code}")
    except Exception as e:
        print(f"⚠️  Ollama embeddings error: {e}")
    
    # Start MCP server
    mcp.run()
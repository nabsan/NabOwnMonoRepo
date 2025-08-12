#!/usr/bin/env python3
"""
Document Loader for Qdrant RAG Collection
Loads text documents (.txt, .md, .pdf) into Qdrant vector database for RAG functionality.
"""

import os
import sys
import argparse
import hashlib
import mimetypes
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests

# PDF processing (optional, install with: pip install PyPDF2)
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("⚠️  PyPDF2 not installed. PDF support disabled.")
    print("   Install with: pip install PyPDF2")

# Configuration from environment variables
QDRANT_HOST = os.getenv("QDRANT_HOST", "http://172.21.32.1:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "rag_collection")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://172.21.32.1:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

class DocumentLoader:
    def __init__(self):
        self.qdrant_url = QDRANT_HOST
        self.collection_name = QDRANT_COLLECTION
        self.ollama_url = OLLAMA_HOST
        self.embedding_model = EMBEDDING_MODEL
        
    def get_embeddings(self, text: str) -> List[float]:
        """Get embeddings from Ollama"""
        try:
            payload = {
                "model": self.embedding_model,
                "prompt": text
            }
            
            print(f"🤖 Getting embeddings from {self.ollama_url}...")
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            embeddings = result.get("embedding", [])
            print(f"✅ Generated embeddings: {len(embeddings)} dimensions")
            return embeddings
            
        except Exception as e:
            print(f"❌ Error getting embeddings: {e}")
            return []
    
    def ensure_collection_exists(self) -> bool:
        """Ensure the Qdrant collection exists"""
        try:
            print(f"🔍 Checking collection '{self.collection_name}' at {self.qdrant_url}...")
            
            # Check if collection exists
            response = requests.get(f"{self.qdrant_url}/collections/{self.collection_name}")
            
            if response.status_code == 200:
                print(f"✅ Collection '{self.collection_name}' exists")
                return True
            elif response.status_code == 404:
                print(f"📁 Creating collection '{self.collection_name}'...")
                
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
                
                if create_response.status_code in [200, 201]:
                    print(f"✅ Collection '{self.collection_name}' created successfully")
                    return True
                else:
                    print(f"❌ Failed to create collection: HTTP {create_response.status_code}")
                    return False
            else:
                print(f"❌ Error checking collection: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error ensuring collection exists: {e}")
            return False
    
    def read_text_file(self, file_path: str) -> Optional[str]:
        """Read text content from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"📖 Read {len(content)} characters from {file_path}")
            return content
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                print(f"📖 Read {len(content)} characters from {file_path} (latin-1 encoding)")
                return content
            except Exception as e:
                print(f"❌ Error reading file {file_path}: {e}")
                return None
        except Exception as e:
            print(f"❌ Error reading file {file_path}: {e}")
            return None
    
    def read_pdf_file(self, file_path: str) -> Optional[str]:
        """Read text content from PDF file"""
        if not PDF_SUPPORT:
            print(f"❌ PDF support not available. Install PyPDF2: pip install PyPDF2")
            return None
            
        try:
            content = ""
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                print(f"📄 Processing PDF with {len(pdf_reader.pages)} pages...")
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        page_text = page.extract_text()
                        content += page_text + "\n"
                        print(f"   Page {page_num}: {len(page_text)} characters")
                    except Exception as e:
                        print(f"   ⚠️  Error reading page {page_num}: {e}")
                        continue
                        
            print(f"📖 Extracted {len(content)} total characters from PDF")
            return content.strip()
            
        except Exception as e:
            print(f"❌ Error reading PDF file {file_path}: {e}")
            return None
    
    def extract_text_from_file(self, file_path: str) -> Optional[str]:
        """Extract text content based on file type"""
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension == '.pdf':
            return self.read_pdf_file(file_path)
        elif file_extension in ['.txt', '.md', '.markdown', '.text']:
            return self.read_text_file(file_path)
        else:
            # Try to read as text file anyway
            print(f"⚠️  Unknown file type {file_extension}, attempting to read as text...")
            return self.read_text_file(file_path)
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Split text into overlapping chunks"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence or paragraph boundary
            if end < len(text):
                # Look for sentence ending
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start + chunk_size // 2:
                    end = sentence_end + 1
                else:
                    # Look for word boundary
                    word_end = text.rfind(' ', start, end)
                    if word_end > start + chunk_size // 2:
                        end = word_end
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            
        print(f"📝 Split text into {len(chunks)} chunks")
        return chunks
    
    def add_document_to_qdrant(self, text: str, metadata: Dict[str, Any]) -> bool:
        """Add a document chunk to Qdrant collection"""
        try:
            # Get embeddings
            embeddings = self.get_embeddings(text)
            if not embeddings:
                return False
            
            # Create UUID-based document ID
            import uuid
            content_hash = hashlib.sha256(text.encode()).hexdigest()
            
            # Generate UUID from hash (deterministic)
            namespace = uuid.UUID('12345678-1234-5678-1234-123456789abc')
            doc_uuid = uuid.uuid5(namespace, f"{metadata.get('filename', 'unknown')}_{content_hash}")
            doc_id = str(doc_uuid)
            
            # Prepare payload
            payload = metadata.copy()
            payload.update({
                "text": text,
                "timestamp": datetime.now().isoformat(),
                "doc_id": doc_id,
                "text_length": len(text),
                "content_hash": content_hash
            })
            
            # Upload to Qdrant
            point = {
                "id": doc_id,
                "vector": embeddings,
                "payload": payload
            }
            
            response = requests.put(
                f"{self.qdrant_url}/collections/{self.collection_name}/points",
                json={"points": [point]}
            )
            
            if response.status_code in [200, 201]:
                print(f"✅ Added chunk to Qdrant: {doc_id[:8]}...")
                return True
            else:
                print(f"❌ Failed to add to Qdrant: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error adding document to Qdrant: {e}")
            return False
    
    def load_file(self, file_path: str, chunk_size: int = 1000, tags: List[str] = None) -> bool:
        """Load a file into Qdrant collection"""
        print(f"\n🚀 Loading file: {file_path}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return False
        
        # Extract file information
        file_info = Path(file_path)
        filename = file_info.name
        file_size = file_info.stat().st_size
        file_extension = file_info.suffix.lower()
        
        print(f"📁 File: {filename}")
        print(f"📏 Size: {file_size:,} bytes")
        print(f"🏷️  Type: {file_extension}")
        
        # Extract text content
        text_content = self.extract_text_from_file(file_path)
        if not text_content:
            print(f"❌ Failed to extract text from {file_path}")
            return False
        
        if not text_content.strip():
            print(f"❌ File appears to be empty: {file_path}")
            return False
        
        # Prepare metadata
        metadata = {
            "filename": filename,
            "filepath": str(file_path),
            "file_size": file_size,
            "file_extension": file_extension,
            "source": f"File: {file_path}",
            "title": filename,
        }
        
        if tags:
            metadata["tags"] = tags
        
        # Split into chunks if necessary
        if len(text_content) > chunk_size:
            chunks = self.chunk_text(text_content, chunk_size)
            
            print(f"📄 Processing {len(chunks)} chunks...")
            success_count = 0
            
            for i, chunk in enumerate(chunks, 1):
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "chunk_id": f"{filename}_chunk_{i}_{hashlib.sha256(chunk.encode()).hexdigest()[:8]}"
                })
                
                print(f"   Processing chunk {i}/{len(chunks)}...")
                if self.add_document_to_qdrant(chunk, chunk_metadata):
                    success_count += 1
                else:
                    print(f"   ❌ Failed to add chunk {i}")
            
            print(f"📊 Results: {success_count}/{len(chunks)} chunks added successfully")
            return success_count > 0
            
        else:
            # Single document
            print(f"📄 Processing single document...")
            return self.add_document_to_qdrant(text_content, metadata)
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            response = requests.get(f"{self.qdrant_url}/collections/{self.collection_name}")
            if response.status_code == 200:
                return response.json().get("result", {})
            else:
                return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

def main():
    parser = argparse.ArgumentParser(
        description="Load documents into Qdrant RAG collection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python load_documents_to_qdrant.py /path/to/document.txt
  python load_documents_to_qdrant.py /path/to/document.pdf --chunk-size 800
  python load_documents_to_qdrant.py /path/to/document.md --tags "python,tutorial"
  python load_documents_to_qdrant.py /path/to/document.txt --tags "manual,guide" --chunk-size 1500

Environment Variables:
  QDRANT_HOST          Qdrant server URL (default: http://43.24.170.44:6333)
  QDRANT_COLLECTION    Collection name (default: rag_collection)
  OLLAMA_HOST          Ollama server URL (default: http://43.24.170.44:11434)
  EMBEDDING_MODEL      Model for embeddings (default: nomic-embed-text)
        """
    )
    
    parser.add_argument(
        "file_path",
        help="Full path to the document file (.txt, .md, .pdf)"
    )
    
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Maximum size of text chunks (default: 1000 characters)"
    )
    
    parser.add_argument(
        "--tags",
        type=str,
        help="Comma-separated tags for the document"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show collection statistics after loading"
    )
    
    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="Test connections to Qdrant and Ollama without loading files"
    )
    
    args = parser.parse_args()
    
    # Initialize loader
    loader = DocumentLoader()
    
    print("🤖 Qdrant Document Loader")
    print("=" * 50)
    print(f"📍 Qdrant Host: {QDRANT_HOST}")
    print(f"🗃️  Collection: {QDRANT_COLLECTION}")
    print(f"🤖 Ollama Host: {OLLAMA_HOST}")
    print(f"🔤 Embedding Model: {EMBEDDING_MODEL}")
    print("=" * 50)
    
    # Test connection if requested
    if args.test_connection:
        print("\n🔍 Testing connections...")
        
        # Test Qdrant
        try:
            response = requests.get(f"{QDRANT_HOST}/collections", timeout=5)
            if response.status_code == 200:
                print("✅ Qdrant connection successful")
            else:
                print(f"⚠️  Qdrant connection warning: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Qdrant connection failed: {e}")
        
        # Test Ollama
        try:
            response = requests.post(
                f"{OLLAMA_HOST}/api/embeddings",
                json={"model": EMBEDDING_MODEL, "prompt": "test"},
                timeout=10
            )
            if response.status_code == 200:
                print("✅ Ollama embeddings connection successful")
            else:
                print(f"⚠️  Ollama connection warning: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Ollama connection failed: {e}")
        
        return
    
    # Ensure collection exists
    if not loader.ensure_collection_exists():
        print("❌ Failed to ensure collection exists. Exiting.")
        sys.exit(1)
    
    # Parse tags
    tags = None
    if args.tags:
        tags = [tag.strip() for tag in args.tags.split(",") if tag.strip()]
        print(f"🏷️  Tags: {', '.join(tags)}")
    
    # Load the file
    success = loader.load_file(
        args.file_path,
        chunk_size=args.chunk_size,
        tags=tags
    )
    
    if success:
        print(f"\n✅ Successfully loaded document: {args.file_path}")
    else:
        print(f"\n❌ Failed to load document: {args.file_path}")
        sys.exit(1)
    
    # Show stats if requested
    if args.stats:
        print("\n📊 Collection Statistics:")
        stats = loader.get_collection_stats()
        
        if "error" in stats:
            print(f"❌ Error getting stats: {stats['error']}")
        else:
            vectors_count = stats.get("vectors_count", 0)
            print(f"📄 Total documents: {vectors_count}")
            
            config = stats.get("config", {})
            vector_config = config.get("params", {}).get("vectors", {})
            print(f"🔢 Vector size: {vector_config.get('size', 'Unknown')}")
            print(f"📏 Distance metric: {vector_config.get('distance', 'Unknown')}")

if __name__ == "__main__":
    main()
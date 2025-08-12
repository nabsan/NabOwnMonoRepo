# Qdrant Document Loading Scripts

These scripts allow you to load text documents into the Qdrant RAG collection for use with nabmcp2.

## Files

- `load_documents_to_qdrant.py` - Single file loader
- `batch_load_documents.py` - Batch directory loader
- `README.md` - This guide

## Prerequisites

1. **Python Environment**: Same virtual environment as nabmcp2
2. **Dependencies**:
   ```bash
   pip install requests
   pip install PyPDF2  # For PDF support (optional)
   ```
3. **Services Running**:
   - Qdrant at `http://43.24.170.44:6333`
   - Ollama with `nomic-embed-text` model

## Supported File Types

- `.txt` - Plain text files
- `.md`, `.markdown` - Markdown files  
- `.pdf` - PDF documents (requires PyPDF2)
- `.text` - Text files with .text extension

## Environment Variables

Set these in your `.env` file or export them:

```bash
QDRANT_HOST=http://43.24.170.44:6333
QDRANT_COLLECTION=rag_collection
OLLAMA_HOST=http://43.24.170.44:11434
EMBEDDING_MODEL=nomic-embed-text
```

## Usage

### Single File Loading

```bash
# Basic usage
python load_documents_to_qdrant.py /path/to/document.txt

# With custom chunk size
python load_documents_to_qdrant.py /path/to/document.pdf --chunk-size 800

# With tags
python load_documents_to_qdrant.py /path/to/manual.md --tags "manual,guide,python"

# Show collection stats after loading
python load_documents_to_qdrant.py /path/to/doc.txt --stats

# Test connections without loading
python load_documents_to_qdrant.py --test-connection /dev/null
```

### Batch Directory Loading

```bash
# Load all documents in directory
python batch_load_documents.py /path/to/documents/

# Include subdirectories
python batch_load_documents.py /path/to/documents/ --recursive

# With tags for all files
python batch_load_documents.py /path/to/docs/ --tags "documentation,v2.0"

# Dry run (see what would be processed)
python batch_load_documents.py /path/to/docs/ --dry-run

# Continue on errors
python batch_load_documents.py /path/to/docs/ --continue-on-error
```

## Examples

### Loading a Single PDF Manual

```bash
python load_documents_to_qdrant.py \
    /home/user/manuals/docker_guide.pdf \
    --tags "docker,containers,devops" \
    --chunk-size 1200 \
    --stats
```

### Loading All Documentation

```bash
python batch_load_documents.py \
    /home/user/project_docs/ \
    --recursive \
    --tags "project,documentation" \
    --continue-on-error
```

### Loading Python Tutorials

```bash
python batch_load_documents.py \
    /home/user/python_tutorials/ \
    --tags "python,tutorial,programming" \
    --chunk-size 800
```

## Text Chunking

Large documents are automatically split into chunks:

- **Default chunk size**: 1000 characters
- **Overlap**: 100 characters between chunks
- **Smart splitting**: Attempts to break at sentence/word boundaries
- **Metadata preservation**: Each chunk maintains file metadata

## Output Format

### Successful Loading
```
🚀 Loading file: /path/to/document.txt
📁 File: document.txt
📏 Size: 15,423 bytes
🏷️  Type: .txt
📖 Read 15423 characters from /path/to/document.txt
📝 Split text into 16 chunks
🤖 Getting embeddings from http://43.24.170.44:11434...
✅ Generated embeddings: 768 dimensions
✅ Added chunk to Qdrant: document.txt_a1b2c3d4
   Processing chunk 1/16...
   Processing chunk 2/16...
   ...
📊 Results: 16/16 chunks added successfully
✅ Successfully loaded document: /path/to/document.txt
```

### Error Handling
```
❌ File not found: /path/to/missing.txt
❌ PDF support not available. Install PyPDF2: pip install PyPDF2
❌ Error getting embeddings: Connection refused
❌ Failed to add to Qdrant: HTTP 404
```

## Troubleshooting

### Connection Issues

```bash
# Test connections
python load_documents_to
#!/usr/bin/env python3
"""
Batch Document Loader for Qdrant RAG Collection
Loads multiple documents from a directory into Qdrant vector database.
"""

import os
import sys
import argparse
import glob
from pathlib import Path
from typing import List
from load_documents_to_qdrant import DocumentLoader

def find_supported_files(directory: str, recursive: bool = False) -> List[str]:
    """Find supported document files in directory"""
    supported_extensions = ['.txt', '.md', '.markdown', '.pdf', '.text']
    files = []
    
    if recursive:
        for ext in supported_extensions:
            pattern = os.path.join(directory, '**', f'*{ext}')
            files.extend(glob.glob(pattern, recursive=True))
    else:
        for ext in supported_extensions:
            pattern = os.path.join(directory, f'*{ext}')
            files.extend(glob.glob(pattern))
    
    return sorted(files)

def main():
    parser = argparse.ArgumentParser(
        description="Batch load documents from directory into Qdrant RAG collection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python batch_load_documents.py /path/to/documents/
  python batch_load_documents.py /path/to/documents/ --recursive
  python batch_load_documents.py /path/to/documents/ --tags "documentation,manual"
  python batch_load_documents.py /path/to/documents/ --chunk-size 800 --recursive

Supported file types: .txt, .md, .markdown, .pdf, .text
        """
    )
    
    parser.add_argument(
        "directory",
        help="Directory containing documents to load"
    )
    
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="Search subdirectories recursively"
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
        help="Comma-separated tags for all documents"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which files would be processed without actually loading them"
    )
    
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue processing other files if one fails"
    )
    
    args = parser.parse_args()
    
    # Check if directory exists
    if not os.path.isdir(args.directory):
        print(f"❌ Directory not found: {args.directory}")
        sys.exit(1)
    
    # Find supported files
    print(f"🔍 Searching for documents in: {args.directory}")
    if args.recursive:
        print("   (including subdirectories)")
    
    files = find_supported_files(args.directory, args.recursive)
    
    if not files:
        print("❌ No supported document files found")
        print("   Supported types: .txt, .md, .markdown, .pdf, .text")
        sys.exit(1)
    
    print(f"📄 Found {len(files)} document(s):")
    for i, file_path in enumerate(files, 1):
        relative_path = os.path.relpath(file_path, args.directory)
        file_size = os.path.getsize(file_path)
        print(f"   {i:2d}. {relative_path} ({file_size:,} bytes)")
    
    if args.dry_run:
        print("\n🏃 Dry run mode - no files will be processed")
        return
    
    # Confirm before processing
    if len(files) > 5:
        response = input(f"\n❓ Process {len(files)} files? (y/N): ")
        if response.lower() != 'y':
            print("❌ Cancelled by user")
            return
    
    # Parse tags
    tags = None
    if args.tags:
        tags = [tag.strip() for tag in args.tags.split(",") if tag.strip()]
        print(f"🏷️  Tags for all documents: {', '.join(tags)}")
    
    # Initialize loader
    loader = DocumentLoader()
    
    # Ensure collection exists
    if not loader.ensure_collection_exists():
        print("❌ Failed to ensure collection exists. Exiting.")
        sys.exit(1)
    
    # Process files
    print(f"\n🚀 Processing {len(files)} files...")
    print("=" * 60)
    
    success_count = 0
    failed_files = []
    
    for i, file_path in enumerate(files, 1):
        print(f"\n📂 [{i}/{len(files)}] Processing: {os.path.basename(file_path)}")
        
        try:
            success = loader.load_file(
                file_path,
                chunk_size=args.chunk_size,
                tags=tags
            )
            
            if success:
                success_count += 1
                print(f"✅ Successfully processed: {os.path.basename(file_path)}")
            else:
                failed_files.append(file_path)
                print(f"❌ Failed to process: {os.path.basename(file_path)}")
                
                if not args.continue_on_error:
                    print("❌ Stopping due to error (use --continue-on-error to continue)")
                    break
                    
        except KeyboardInterrupt:
            print(f"\n⚠️  Interrupted by user after processing {success_count} files")
            break
            
        except Exception as e:
            failed_files.append(file_path)
            print(f"❌ Error processing {os.path.basename(file_path)}: {e}")
            
            if not args.continue_on_error:
                print("❌ Stopping due to error (use --continue-on-error to continue)")
                break
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 BATCH PROCESSING SUMMARY")
    print("=" * 60)
    print(f"✅ Successfully processed: {success_count}/{len(files)} files")
    
    if failed_files:
        print(f"❌ Failed files ({len(failed_files)}):")
        for file_path in failed_files:
            print(f"   - {os.path.basename(file_path)}")
    
    # Show collection stats
    print(f"\n📈 Collection Statistics:")
    stats = loader.get_collection_stats()
    
    if "error" in stats:
        print(f"❌ Error getting stats: {stats['error']}")
    else:
        vectors_count = stats.get("vectors_count", 0)
        print(f"📄 Total documents in collection: {vectors_count}")
    
    if success_count > 0:
        print(f"\n🎉 Batch processing completed! {success_count} files loaded successfully.")
    else:
        print(f"\n😞 No files were processed successfully.")
        sys.exit(1)

if __name__ == "__main__":
    main()
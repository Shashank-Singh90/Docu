import json
import asyncio
from pathlib import Path
from typing import List, Dict
from src.chunking.smart_chunker import SmartDocumentChunker
from src.retrieval.vector_store import ChromaVectorStore
from src.utils.logger import get_logger

logger = get_logger(__name__)

async def process_and_add_documentation():
    """Process scraped documentation and add to vector store"""
    
    logger.info("🚀 Starting documentation processing and ingestion...")
    
    # Initialize components
    chunker = SmartDocumentChunker()
    vector_store = ChromaVectorStore()
    
    # Files to process
    scraped_files = [
        ("data/scraped/django_docs.json", "Django"),
        ("data/scraped/react_nextjs_docs.json", "React/Next.js"), 
        ("data/scraped/python_docs.json", "Python")
    ]
    
    total_chunks_added = 0
    
    for file_path, doc_type in scraped_files:
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            logger.warning(f"⚠️ File not found: {file_path}")
            continue
            
        logger.info(f"📖 Processing {doc_type} documentation from {file_path}")
        
        # Load scraped documents
        with open(file_path_obj, 'r', encoding='utf-8') as f:
            documents = json.load(f)
        
        logger.info(f"📄 Loaded {len(documents)} {doc_type} documents")
        
        # Process each document
        chunks_for_this_source = []
        
        for i, doc in enumerate(documents):
            try:
                # Chunk the document
                chunks = await chunker.chunk_document(
                    content=doc['content'],
                    metadata={
                        'title': doc['title'],
                        'source': doc['source'],
                        'url': doc['url'],
                        'doc_type': doc.get('doc_type', 'general'),
                        'scraped_at': doc.get('scraped_at', '')
                    }
                )
                
                chunks_for_this_source.extend(chunks)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"📋 Processed {i + 1}/{len(documents)} {doc_type} documents")
                    
            except Exception as e:
                logger.error(f"❌ Error processing document {doc['title']}: {e}")
                continue
        
        # Add chunks to vector store
        if chunks_for_this_source:
            logger.info(f"💾 Adding {len(chunks_for_this_source)} {doc_type} chunks to vector store...")
            
            # Prepare documents for vector store
            texts = [chunk['content'] for chunk in chunks_for_this_source]
            metadatas = [chunk['metadata'] for chunk in chunks_for_this_source]
            ids = [f"{chunk['metadata']['source']}_{i}" for i, chunk in enumerate(chunks_for_this_source)]
            
            # Add to vector store
            vector_store.add_documents(
                texts=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            total_chunks_added += len(chunks_for_this_source)
            logger.info(f"✅ Added {len(chunks_for_this_source)} {doc_type} chunks successfully")
        
        else:
            logger.warning(f"⚠️ No chunks generated for {doc_type}")
    
    # Get updated statistics
    stats = vector_store.get_collection_stats()
    
    logger.info("🎉 Documentation processing completed!")
    logger.info(f"📊 Total chunks added: {total_chunks_added}")
    logger.info(f"📊 Total chunks in database: {stats.get('total_chunks', 0)}")
    logger.info(f"📊 Sources in database: {len(stats.get('sources', {}))}")
    
    # Show source breakdown
    logger.info("📋 Source breakdown:")
    for source, count in stats.get('sources', {}).items():
        logger.info(f"  • {source.upper()}: {count} chunks")

def main():
    """Main function"""
    asyncio.run(process_and_add_documentation())

if __name__ == "__main__":
    main()
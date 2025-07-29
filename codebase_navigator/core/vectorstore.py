"""
Vector store management for codebase embeddings
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from .embeddings import CodeChunker, create_embeddings


class CodebaseVectorStore:
    """
    Vector store for codebase embeddings with specialized code search capabilities
    """
    
    def __init__(
        self,
        persist_directory: str,
        embedding_model: str = "text-embedding-3-small",
        collection_name: str = "codebase"
    ):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.embeddings = create_embeddings(embedding_model)
        self.collection_name = collection_name
        
        # Initialize Chroma vector store
        self.vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=str(self.persist_directory)
        )
        
        self.chunker = CodeChunker()
    
    def index_repository(
        self, 
        repo_path: str, 
        ignore_patterns: Optional[List[str]] = None,
        force_reindex: bool = False
    ) -> int:
        """
        Index a repository by chunking and embedding all code files
        
        Args:
            repo_path: Path to repository root
            ignore_patterns: File patterns to ignore
            force_reindex: Whether to clear existing index first
            
        Returns:
            Number of documents indexed
        """
        if force_reindex:
            self.clear_index()
        
        # Check if already indexed
        if not force_reindex and self.get_document_count() > 0:
            print(f"Repository already indexed with {self.get_document_count()} documents")
            return self.get_document_count()
        
        print(f"Indexing repository: {repo_path}")
        
        # Chunk all repository files  
        documents = self.chunker.chunk_repository(repo_path, ignore_patterns)
        
        if not documents:
            print("No documents found to index")
            return 0
        
        # Add documents to vector store in batches
        batch_size = 100
        total_docs = len(documents)
        
        for i in range(0, total_docs, batch_size):
            batch = documents[i:i + batch_size]
            self.vectorstore.add_documents(batch)
            print(f"Indexed {min(i + batch_size, total_docs)}/{total_docs} documents")
        
        # Persist the vector store
        self.vectorstore.persist()
        
        print(f"Successfully indexed {total_docs} document chunks")
        return total_docs
    
    def search_code(
        self, 
        query: str, 
        k: int = 5,
        filter_by_language: Optional[str] = None,
        filter_by_chunk_type: Optional[str] = None
    ) -> List[Tuple[Document, float]]:
        """
        Search for relevant code chunks
        
        Args:
            query: Search query
            k: Number of results to return
            filter_by_language: Filter by programming language
            filter_by_chunk_type: Filter by chunk type (class, function, etc.)
            
        Returns:
            List of (Document, score) tuples
        """
        # Build metadata filter
        where_filter = {}
        if filter_by_language:
            where_filter['language'] = filter_by_language
        if filter_by_chunk_type:
            where_filter['chunk_type'] = filter_by_chunk_type
        
        # Perform similarity search
        if where_filter:
            results = self.vectorstore.similarity_search_with_score(
                query, k=k, where=where_filter
            )
        else:
            results = self.vectorstore.similarity_search_with_score(query, k=k)
        
        return results
    
    def search_by_file_path(self, file_path: str, k: int = 10) -> List[Document]:
        """
        Get all chunks for a specific file
        
        Args:
            file_path: Path to the file
            k: Maximum number of chunks to return
            
        Returns:
            List of document chunks for the file
        """
        results = self.vectorstore.similarity_search(
            "", k=k, where={"path": file_path}
        )
        
        # Sort by chunk_index to maintain order
        results.sort(key=lambda doc: doc.metadata.get('chunk_index', 0))
        return results
    
    def get_file_list(self) -> List[str]:
        """Get list of all indexed files"""
        # This requires querying the underlying ChromaDB collection
        collection = self.vectorstore._collection
        
        # Get all documents and extract unique file paths
        results = collection.get()
        file_paths = set()
        
        for metadata in results['metadatas']:
            if 'path' in metadata:
                file_paths.add(metadata['path'])
        
        return sorted(list(file_paths))
    
    def get_language_stats(self) -> Dict[str, int]:
        """Get statistics of indexed languages"""
        collection = self.vectorstore._collection
        results = collection.get()
        
        language_counts = {}
        for metadata in results['metadatas']:
            language = metadata.get('language', 'unknown')
            language_counts[language] = language_counts.get(language, 0) + 1
        
        return language_counts
    
    def get_document_count(self) -> int:
        """Get total number of indexed documents"""
        return self.vectorstore._collection.count()
    
    def clear_index(self):
        """Clear all indexed documents"""
        self.vectorstore._collection.delete()
        print("Cleared vector store index")
    
    def get_retriever(self, search_kwargs: Optional[Dict[str, Any]] = None):
        """
        Get a LangChain retriever for this vector store
        
        Args:
            search_kwargs: Additional search parameters
            
        Returns:
            LangChain retriever instance
        """
        if search_kwargs is None:
            search_kwargs = {"k": 5}
        
        return self.vectorstore.as_retriever(
            search_type="mmr",  # Maximum Marginal Relevance for diversity
            search_kwargs=search_kwargs
        )
    
    def similarity_search_with_metadata(
        self, 
        query: str, 
        k: int = 5, 
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search with structured metadata output
        
        Args:
            query: Search query
            k: Number of results
            score_threshold: Minimum similarity score
            
        Returns:
            List of search results with structured metadata
        """
        results = self.vectorstore.similarity_search_with_score(query, k=k)
        
        structured_results = []
        for doc, score in results:
            if score >= score_threshold:
                result = {
                    'content': doc.page_content,
                    'score': score,
                    'metadata': doc.metadata,
                    'path': doc.metadata.get('path', ''),
                    'start_line': doc.metadata.get('start_line', 0),
                    'end_line': doc.metadata.get('end_line', 0),
                    'language': doc.metadata.get('language', 'unknown'),
                    'chunk_type': doc.metadata.get('chunk_type', 'code_block')
                }
                structured_results.append(result)
        
        return structured_results


def create_vectorstore(
    persist_directory: str,
    embedding_model: str = "text-embedding-3-small",
    collection_name: str = "codebase"
) -> CodebaseVectorStore:
    """
    Create a new codebase vector store
    
    Args:
        persist_directory: Directory to persist vector store
        embedding_model: OpenAI embedding model name
        collection_name: Name for the vector store collection
        
    Returns:
        CodebaseVectorStore instance
    """
    return CodebaseVectorStore(
        persist_directory=persist_directory,
        embedding_model=embedding_model,
        collection_name=collection_name
    )
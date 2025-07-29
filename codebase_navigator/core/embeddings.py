"""
Code chunking and embedding utilities
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings


class CodeChunker:
    """
    Intelligent code chunking that preserves syntactic units
    """
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Language-specific separators that respect syntax
        self.language_separators = {
            'python': ['\nclass ', '\ndef ', '\n    def ', '\nif __name__', '\n\n'],
            'javascript': ['\nfunction ', '\nclass ', '\nconst ', '\nlet ', '\nvar ', '\n\n'],
            'typescript': ['\nfunction ', '\nclass ', '\ninterface ', '\ntype ', '\nconst ', '\n\n'],
            'java': ['\npublic class ', '\nprivate class ', '\npublic void ', '\nprivate void ', '\n\n'],
            'go': ['\nfunc ', '\ntype ', '\nvar ', '\nconst ', '\n\n'],
            'rust': ['\nfn ', '\nstruct ', '\nimpl ', '\nenum ', '\nmod ', '\n\n'],
            'c': ['\nvoid ', '\nint ', '\nchar ', '\nfloat ', '\ndouble ', '\n\n'],
            'cpp': ['\nvoid ', '\nint ', '\nclass ', '\nstruct ', '\nnamespace ', '\n\n'],
        }
    
    def detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        suffix = Path(file_path).suffix.lower()
        
        language_map = {
            '.py': 'python',
            '.js': 'javascript', 
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.c': 'c',
            '.h': 'c',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.hpp': 'cpp',
            '.md': 'markdown',
            '.rst': 'restructuredtext',
            '.txt': 'text',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.sql': 'sql',
        }
        
        return language_map.get(suffix, 'text')
    
    def chunk_code(self, content: str, file_path: str) -> List[Document]:
        """
        Chunk code content while preserving syntactic boundaries
        
        Args:
            content: File content to chunk
            file_path: Path to the file for metadata
            
        Returns:
            List of Document objects with chunked content
        """
        language = self.detect_language(file_path)
        separators = self.language_separators.get(language, ['\n\n', '\n'])
        
        # Create language-aware splitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=separators,
            keep_separator=True
        )
        
        # Split the content
        chunks = splitter.split_text(content)
        
        documents = []
        content_lines = content.splitlines()
        
        for i, chunk in enumerate(chunks):
            # Calculate line numbers for this chunk
            start_line = self._find_line_number(content, chunk, content_lines)
            end_line = start_line + len(chunk.splitlines()) - 1
            
            # Create document with metadata
            doc = Document(
                page_content=chunk,
                metadata={
                    'path': file_path,
                    'language': language,
                    'chunk_index': i,
                    'start_line': start_line,
                    'end_line': end_line,
                    'chunk_type': self._classify_chunk(chunk, language)
                }
            )
            documents.append(doc)
        
        return documents
    
    def _find_line_number(self, full_content: str, chunk: str, content_lines: List[str]) -> int:
        """Find the starting line number of a chunk in the full content"""
        try:
            # Find the chunk in the full content
            chunk_start = full_content.find(chunk.strip())
            if chunk_start == -1:
                return 1
            
            # Count newlines before the chunk
            lines_before = full_content[:chunk_start].count('\n')
            return lines_before + 1
        except:
            return 1
    
    def _classify_chunk(self, chunk: str, language: str) -> str:
        """Classify the type of code chunk"""
        chunk_lower = chunk.lower().strip()
        
        if language == 'python':
            if chunk_lower.startswith('class '):
                return 'class_definition'
            elif chunk_lower.startswith('def '):
                return 'function_definition'
            elif 'import ' in chunk_lower or 'from ' in chunk_lower:
                return 'imports'
            elif chunk_lower.startswith('#') or '"""' in chunk or "'''" in chunk:
                return 'documentation'
        
        elif language in ['javascript', 'typescript']:
            if 'function ' in chunk_lower or '=>' in chunk:
                return 'function_definition'
            elif 'class ' in chunk_lower:
                return 'class_definition' 
            elif 'import ' in chunk_lower or 'export ' in chunk_lower:
                return 'imports'
            elif chunk_lower.startswith('//') or '/*' in chunk:
                return 'documentation'
        
        elif language == 'java':
            if 'public class ' in chunk_lower or 'private class ' in chunk_lower:
                return 'class_definition'
            elif 'public void ' in chunk_lower or 'private void ' in chunk_lower:
                return 'method_definition'
            elif 'import ' in chunk_lower:
                return 'imports'
        
        # Default classification
        if any(keyword in chunk_lower for keyword in ['todo', 'fixme', 'hack', 'bug']):
            return 'comment_todo'
        elif len(chunk.strip().splitlines()) == 1:
            return 'single_line'
        else:
            return 'code_block'
    
    def chunk_repository(self, repo_path: str, ignore_patterns: Optional[List[str]] = None) -> List[Document]:
        """
        Chunk all files in a repository
        
        Args:
            repo_path: Path to repository root
            ignore_patterns: Patterns to ignore (like .gitignore)
            
        Returns:
            List of all document chunks from the repository
        """
        if ignore_patterns is None:
            ignore_patterns = [
                '*.pyc', '__pycache__', '.git', '.venv', 'venv', 'node_modules',
                '.DS_Store', '*.log', '.env', '*.min.js', '*.bundle.js',
                'dist/', 'build/', 'target/', '.next/', '.nuxt/'
            ]
        
        repo_path = Path(repo_path)
        all_documents = []
        
        # Supported file extensions
        code_extensions = {
            '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go', '.rs',
            '.c', '.h', '.cpp', '.hpp', '.cc', '.cxx', '.php', '.rb',
            '.scala', '.kt', '.swift', '.dart', '.sh', '.bash', '.zsh',
            '.sql', '.html', '.css', '.scss', '.less', '.vue', '.svelte'
        }
        
        doc_extensions = {'.md', '.rst', '.txt', '.json', '.yaml', '.yml', '.xml'}
        
        supported_extensions = code_extensions | doc_extensions
        
        for file_path in self._walk_repository(repo_path, ignore_patterns):
            if file_path.suffix.lower() in supported_extensions:
                try:
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Skip empty files
                    if not content.strip():
                        continue
                    
                    # Get relative path for metadata
                    relative_path = str(file_path.relative_to(repo_path))
                    
                    # Chunk the file
                    file_documents = self.chunk_code(content, relative_path)
                    all_documents.extend(file_documents)
                    
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    continue
        
        return all_documents
    
    def _walk_repository(self, repo_path: Path, ignore_patterns: List[str]) -> List[Path]:
        """Walk repository and return files that should be processed"""
        files = []
        
        def should_ignore(path: Path) -> bool:
            path_str = str(path)
            for pattern in ignore_patterns:
                if pattern.startswith('*'):
                    if path_str.endswith(pattern[1:]):
                        return True
                elif pattern.endswith('/'):
                    if pattern[:-1] in path.parts:
                        return True
                elif pattern in path_str:
                    return True
            return False
        
        for file_path in repo_path.rglob('*'):
            if file_path.is_file() and not should_ignore(file_path):
                files.append(file_path)
        
        return files


def create_embeddings(model_name: str = "text-embedding-3-small") -> OpenAIEmbeddings:
    """
    Create OpenAI embeddings instance
    
    Args:
        model_name: Name of the embedding model to use
        
    Returns:
        OpenAI embeddings instance
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    return OpenAIEmbeddings(
        model=model_name,
        openai_api_key=api_key
    )
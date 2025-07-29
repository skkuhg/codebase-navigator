"""
GitHub Repository Analyzer

Fetches and analyzes GitHub repositories for RAG-based question answering.
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
import requests
import base64
from urllib.parse import urlparse
import git
from git import Repo
import zipfile
import io

from .repository import RepositoryAnalyzer
from .vectorstore import CodebaseVectorStore


class GitHubAnalyzer:
    """Analyzes GitHub repositories for code understanding"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        self.session = requests.Session()
        if self.github_token:
            self.session.headers.update({
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            })
    
    def parse_github_url(self, url: str) -> Dict[str, str]:
        """Parse GitHub URL to extract owner and repo name"""
        # Handle different GitHub URL formats
        if url.startswith('https://github.com/'):
            path = url.replace('https://github.com/', '').rstrip('/')
        elif url.startswith('github.com/'):
            path = url.replace('github.com/', '').rstrip('/')
        else:
            # Assume format is "owner/repo"
            path = url.rstrip('/')
        
        parts = path.split('/')
        if len(parts) >= 2:
            return {
                'owner': parts[0],
                'repo': parts[1].replace('.git', '')
            }
        else:
            raise ValueError(f"Invalid GitHub URL format: {url}")
    
    def get_repo_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information from GitHub API"""
        url = f"https://api.github.com/repos/{owner}/{repo}"
        response = self.session.get(url)
        
        if response.status_code == 404:
            raise ValueError(f"Repository {owner}/{repo} not found or is private")
        elif response.status_code != 200:
            raise ValueError(f"Failed to fetch repository info: {response.status_code}")
        
        return response.json()
    
    def download_repository(self, owner: str, repo: str, branch: str = 'main') -> str:
        """Download repository as ZIP and extract to temporary directory"""
        # Try main branch first, then master
        branches_to_try = [branch, 'main', 'master']
        
        temp_dir = None
        for branch_name in branches_to_try:
            try:
                # Download ZIP from GitHub
                zip_url = f"https://api.github.com/repos/{owner}/{repo}/zipball/{branch_name}"
                response = self.session.get(zip_url)
                
                if response.status_code == 200:
                    # Create temporary directory
                    temp_dir = tempfile.mkdtemp(prefix=f"github_{owner}_{repo}_")
                    
                    # Extract ZIP
                    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                        zip_file.extractall(temp_dir)
                    
                    # Find the extracted directory (GitHub creates a folder with commit hash)
                    extracted_dirs = [d for d in os.listdir(temp_dir) 
                                    if os.path.isdir(os.path.join(temp_dir, d))]
                    
                    if extracted_dirs:
                        # Move contents up one level
                        extracted_path = os.path.join(temp_dir, extracted_dirs[0])
                        final_path = os.path.join(temp_dir, 'repo')
                        shutil.move(extracted_path, final_path)
                        return final_path
                    
                    break
                    
            except Exception as e:
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                continue
        
        if temp_dir is None:
            raise ValueError(f"Failed to download repository {owner}/{repo}")
        
        return temp_dir
    
    def clone_repository(self, owner: str, repo: str, branch: str = 'main') -> str:
        """Clone repository using git (alternative to ZIP download)"""
        temp_dir = tempfile.mkdtemp(prefix=f"github_{owner}_{repo}_")
        repo_url = f"https://github.com/{owner}/{repo}.git"
        
        try:
            # Clone with depth=1 for faster download
            Repo.clone_from(
                repo_url, 
                temp_dir,
                branch=branch,
                depth=1,
                single_branch=True
            )
            return temp_dir
        except git.GitCommandError as e:
            # Try different branches if the specified one doesn't exist
            for branch_name in ['main', 'master']:
                if branch_name != branch:
                    try:
                        shutil.rmtree(temp_dir)
                        temp_dir = tempfile.mkdtemp(prefix=f"github_{owner}_{repo}_")
                        Repo.clone_from(
                            repo_url, 
                            temp_dir,
                            branch=branch_name,
                            depth=1,
                            single_branch=True
                        )
                        return temp_dir
                    except git.GitCommandError:
                        continue
            
            # If all branches fail, clean up and raise error
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            raise ValueError(f"Failed to clone repository {owner}/{repo}: {str(e)}")
    
    def analyze_github_repo(self, github_url: str, method: str = 'download') -> Dict[str, Any]:
        """
        Analyze a GitHub repository and return analysis results
        
        Args:
            github_url: GitHub repository URL or owner/repo format
            method: 'download' for ZIP download or 'clone' for git clone
            
        Returns:
            Dictionary with repository info and analysis results
        """
        # Parse GitHub URL
        parsed = self.parse_github_url(github_url)
        owner, repo = parsed['owner'], parsed['repo']
        
        # Get repository information
        repo_info = self.get_repo_info(owner, repo)
        
        # Download/clone repository
        if method == 'clone':
            local_path = self.clone_repository(owner, repo, repo_info.get('default_branch', 'main'))
        else:
            local_path = self.download_repository(owner, repo, repo_info.get('default_branch', 'main'))
        
        try:
            # Analyze the repository
            analyzer = RepositoryAnalyzer(local_path)
            analysis = analyzer.get_project_info()
            
            # Create vector store and index
            vector_store = CodebaseVectorStore(
                persist_directory=os.path.join(local_path, '.vector_store')
            )
            
            # Index the repository
            chunks = vector_store.index_repository(local_path)
            
            return {
                'repo_info': repo_info,
                'local_path': local_path,
                'analysis': analysis,
                'vector_store': vector_store,
                'indexed_chunks': len(chunks),
                'cleanup_path': local_path  # Path to clean up later
            }
            
        except Exception as e:
            # Clean up on error but don't fail if cleanup fails
            try:
                if os.path.exists(local_path):
                    self.cleanup_repo(local_path)
            except:
                pass  # Don't fail if cleanup fails
            raise e
    
    def cleanup_repo(self, local_path: str):
        """Clean up downloaded repository with retry logic for Windows"""
        if os.path.exists(local_path):
            try:
                # On Windows, close any vector store connections first
                import time
                time.sleep(0.5)  # Give time for file handles to close
                
                # Retry logic for Windows file locking issues
                max_retries = 3
                for i in range(max_retries):
                    try:
                        shutil.rmtree(local_path)
                        break
                    except (PermissionError, OSError) as e:
                        if i < max_retries - 1:
                            time.sleep(1)  # Wait a bit before retry
                            continue
                        else:
                            # Log warning but don't fail the operation
                            print(f"Warning: Could not clean up temporary directory {local_path}: {e}")
            except Exception as e:
                print(f"Warning: Could not clean up temporary directory {local_path}: {e}")
    
    def get_file_content(self, owner: str, repo: str, file_path: str, branch: str = 'main') -> str:
        """Get content of a specific file from GitHub API"""
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
        params = {'ref': branch}
        
        response = self.session.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('encoding') == 'base64':
                return base64.b64decode(data['content']).decode('utf-8')
            else:
                return data['content']
        else:
            raise ValueError(f"Failed to get file {file_path}: {response.status_code}")
    
    def search_repositories(self, query: str, language: Optional[str] = None, 
                          sort: str = 'stars', limit: int = 10) -> List[Dict[str, Any]]:
        """Search GitHub repositories"""
        search_query = query
        if language:
            search_query += f" language:{language}"
        
        url = "https://api.github.com/search/repositories"
        params = {
            'q': search_query,
            'sort': sort,
            'order': 'desc',
            'per_page': min(limit, 100)
        }
        
        response = self.session.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('items', [])
        else:
            raise ValueError(f"Failed to search repositories: {response.status_code}")


class GitHubRAGSession:
    """Manages a RAG session for a GitHub repository"""
    
    def __init__(self, github_analyzer: GitHubAnalyzer, analysis_result: Dict[str, Any]):
        self.github_analyzer = github_analyzer
        self.analysis_result = analysis_result
        self.vector_store = analysis_result['vector_store']
        self.repo_info = analysis_result['repo_info']
        self.local_path = analysis_result['local_path']
    
    def query(self, question: str, k: int = 5) -> Dict[str, Any]:
        """Query the repository using RAG"""
        # Search for relevant code chunks
        results = self.vector_store.similarity_search_with_score(question, k=k)
        
        # Format context from retrieved chunks
        context = []
        sources = []
        
        for doc, score in results:
            context.append(f"File: {doc.metadata.get('source', 'unknown')}\n{doc.page_content}")
            sources.append({
                'file': doc.metadata.get('source', 'unknown'),
                'chunk_type': doc.metadata.get('chunk_type', 'unknown'),
                'score': float(score)
            })
        
        return {
            'question': question,
            'context': '\n\n---\n\n'.join(context),
            'sources': sources,
            'repo_name': self.repo_info['full_name'],
            'repo_description': self.repo_info.get('description', ''),
            'repo_language': self.repo_info.get('language', 'Unknown'),
            'stars': self.repo_info.get('stargazers_count', 0)
        }
    
    def get_file_structure(self) -> Dict[str, Any]:
        """Get the repository file structure"""
        analyzer = RepositoryAnalyzer(self.local_path)
        return analyzer.get_project_info()
    
    def cleanup(self):
        """Clean up the downloaded repository"""
        try:
            # Close vector store connection first
            if hasattr(self.vector_store, 'vectorstore') and hasattr(self.vector_store.vectorstore, '_client'):
                try:
                    self.vector_store.vectorstore._client.reset()
                except:
                    pass
        except:
            pass
        
        # Then cleanup the repository files
        self.github_analyzer.cleanup_repo(self.local_path)


def create_github_session(github_url: str, method: str = 'download', github_token: Optional[str] = None) -> GitHubRAGSession:
    """Create a GitHub RAG session for analyzing a repository"""
    analyzer = GitHubAnalyzer(github_token)
    analysis_result = analyzer.analyze_github_repo(github_url, method=method)
    return GitHubRAGSession(analyzer, analysis_result)

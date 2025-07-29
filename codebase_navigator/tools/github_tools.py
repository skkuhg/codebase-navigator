"""
GitHub integration tools for LangChain agents
"""

from typing import Any, Optional, Dict, List
from langchain.tools import BaseTool
from pydantic import BaseModel

from ..core.github_analyzer import GitHubAnalyzer, GitHubRAGSession, create_github_session


class AnalyzeGitHubRepoTool(BaseTool):
    """Tool for analyzing GitHub repositories"""
    name: str = "analyze_github_repo"
    description: str = """Analyze a GitHub repository and create a RAG session for it.
    Input: {"url": str, "method": str}  # method can be 'download' or 'clone'
    Output: Repository analysis with indexed chunks for RAG"""
    
    github_token: Optional[str] = None
    
    def __init__(self, github_token: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.github_token = github_token
        self.sessions: Dict[str, GitHubRAGSession] = {}
    
    def _run(self, url: str, method: str = 'download') -> Dict[str, Any]:
        try:
            analyzer = GitHubAnalyzer(self.github_token)
            parsed = analyzer.parse_github_url(url)
            repo_key = f"{parsed['owner']}/{parsed['repo']}"
            
            # Check if we already have a session for this repo
            if repo_key in self.sessions:
                session = self.sessions[repo_key]
                return {
                    'status': 'already_analyzed',
                    'repo_name': session.repo_info['full_name'],
                    'description': session.repo_info.get('description', ''),
                    'language': session.repo_info.get('language', 'Unknown'),
                    'stars': session.repo_info.get('stargazers_count', 0),
                    'indexed_chunks': session.analysis_result['indexed_chunks']
                }
            
            # Analyze the repository
            analysis_result = analyzer.analyze_github_repo(url, method)
            session = GitHubRAGSession(analyzer, analysis_result)
            
            # Store session for reuse
            self.sessions[repo_key] = session
            
            return {
                'status': 'analyzed',
                'repo_name': session.repo_info['full_name'],
                'description': session.repo_info.get('description', ''),
                'language': session.repo_info.get('language', 'Unknown'),
                'stars': session.repo_info.get('stargazers_count', 0),
                'indexed_chunks': analysis_result['indexed_chunks'],
                'local_path': analysis_result['local_path']
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }


class QueryGitHubRepoTool(BaseTool):
    """Tool for querying analyzed GitHub repositories"""
    name: str = "query_github_repo"
    description: str = """Query an analyzed GitHub repository using RAG.
    Input: {"repo": str, "question": str, "k": int}  # repo in format 'owner/repo'
    Output: RAG-based answer with relevant code chunks"""
    
    def __init__(self, analyze_tool: AnalyzeGitHubRepoTool, **kwargs):
        super().__init__(**kwargs)
        self.analyze_tool = analyze_tool
    
    def _run(self, repo: str, question: str, k: int = 5) -> Dict[str, Any]:
        try:
            # Check if repo is analyzed
            if repo not in self.analyze_tool.sessions:
                return {
                    'status': 'error',
                    'error': f'Repository {repo} not analyzed. Use analyze_github_repo first.'
                }
            
            session = self.analyze_tool.sessions[repo]
            result = session.query(question, k)
            
            return {
                'status': 'success',
                'answer': result,
                'repo_info': {
                    'name': result['repo_name'],
                    'description': result['repo_description'],
                    'language': result['repo_language'],
                    'stars': result['stars']
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }


class SearchGitHubReposTool(BaseTool):
    """Tool for searching GitHub repositories"""
    name: str = "search_github_repos"
    description: str = """Search GitHub repositories by query.
    Input: {"query": str, "language": str, "limit": int}
    Output: List of relevant repositories with metadata"""
    
    github_token: Optional[str] = None
    
    def __init__(self, github_token: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.github_token = github_token
    
    def _run(self, query: str, language: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        try:
            analyzer = GitHubAnalyzer(self.github_token)
            repos = analyzer.search_repositories(query, language, limit=limit)
            
            # Format results
            formatted_repos = []
            for repo in repos:
                formatted_repos.append({
                    'full_name': repo['full_name'],
                    'description': repo.get('description', ''),
                    'language': repo.get('language', 'Unknown'),
                    'stars': repo.get('stargazers_count', 0),
                    'forks': repo.get('forks_count', 0),
                    'url': repo['html_url'],
                    'updated_at': repo.get('updated_at', ''),
                    'topics': repo.get('topics', [])
                })
            
            return {
                'status': 'success',
                'query': query,
                'total_found': len(formatted_repos),
                'repositories': formatted_repos
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }


class GetRepoStructureTool(BaseTool):
    """Tool for getting repository file structure"""
    name: str = "get_repo_structure"
    description: str = """Get the file structure of an analyzed GitHub repository.
    Input: {"repo": str}  # repo in format 'owner/repo'
    Output: Repository file structure and project information"""
    
    def __init__(self, analyze_tool: AnalyzeGitHubRepoTool, **kwargs):
        super().__init__(**kwargs)
        self.analyze_tool = analyze_tool
    
    def _run(self, repo: str) -> Dict[str, Any]:
        try:
            # Check if repo is analyzed
            if repo not in self.analyze_tool.sessions:
                return {
                    'status': 'error',
                    'error': f'Repository {repo} not analyzed. Use analyze_github_repo first.'
                }
            
            session = self.analyze_tool.sessions[repo]
            structure = session.get_file_structure()
            
            return {
                'status': 'success',
                'repo_name': repo,
                'structure': structure
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }


def create_github_tools(github_token: Optional[str] = None) -> List[BaseTool]:
    """Create GitHub analysis tools for LangChain agents"""
    analyze_tool = AnalyzeGitHubRepoTool(github_token=github_token)
    
    tools = [
        analyze_tool,
        QueryGitHubRepoTool(analyze_tool=analyze_tool),
        SearchGitHubReposTool(github_token=github_token),
        GetRepoStructureTool(analyze_tool=analyze_tool)
    ]
    
    return tools

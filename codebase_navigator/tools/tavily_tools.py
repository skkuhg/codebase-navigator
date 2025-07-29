"""
Tavily search integration for external documentation and standards
"""

import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from langchain.tools import BaseTool
from tavily import TavilyClient


class TavilyResult(BaseModel):
    """Represents a Tavily search result"""
    title: str
    url: str
    snippet: str
    content: Optional[str] = None


class TavilySearchTool(BaseTool):
    """Tool for high-quality web search using Tavily"""
    name: str = "tavily_search"
    description: str = """Search the web for documentation, standards, and technical information.
    Input: {"query": str, "max_results": int, "include_answers": bool}
    Output: List of search results with titles, URLs, and snippets"""
    
    api_key: str = ""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__()
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "")
        
    def _run(self, query: str, max_results: int = 5, include_answers: bool = True) -> List[TavilyResult]:
        if not self.api_key:
            return [TavilyResult(
                title="Error",
                url="",
                snippet="Tavily API key not configured",
                content=""
            )]
        
        try:
            client = TavilyClient(api_key=self.api_key)
            
            # Perform search with focus on technical documentation
            response = client.search(
                query=query,
                search_depth="advanced",
                max_results=max_results,
                include_answer=include_answers,
                include_domains=[
                    "docs.python.org",
                    "nodejs.org",
                    "developer.mozilla.org", 
                    "reactjs.org",
                    "vuejs.org",
                    "angular.io",
                    "docs.djangoproject.com",
                    "flask.palletsprojects.com",
                    "fastapi.tiangolo.com",
                    "stackoverflow.com",
                    "github.com",
                    "langchain.readthedocs.io",
                    "python.langchain.com"
                ]
            )
            
            results = []
            
            # Add search answer if available
            if include_answers and response.get("answer"):
                results.append(TavilyResult(
                    title="Tavily Answer",
                    url="tavily://answer",
                    snippet=response["answer"],
                    content=response["answer"]
                ))
            
            # Add search results
            for result in response.get("results", []):
                results.append(TavilyResult(
                    title=result.get("title", ""),
                    url=result.get("url", ""),
                    snippet=result.get("content", ""),
                    content=result.get("raw_content", "")
                ))
            
            return results
            
        except Exception as e:
            return [TavilyResult(
                title="Search Error",
                url="",
                snippet=f"Error performing search: {str(e)}",
                content=""
            )]


def tavily_search(query: str, max_results: int = 5, include_answers: bool = True, api_key: Optional[str] = None) -> List[TavilyResult]:
    """
    Search the web using Tavily for high-quality technical documentation and standards
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        include_answers: Whether to include Tavily's answer
        api_key: Tavily API key (uses env var if not provided)
    
    Returns:
        List of TavilyResult objects with search results
    """
    tool = TavilySearchTool(api_key=api_key)
    return tool._run(query, max_results, include_answers)


def create_tavily_tool(api_key: Optional[str] = None) -> TavilySearchTool:
    """Create a Tavily search tool instance"""
    return TavilySearchTool(api_key=api_key)
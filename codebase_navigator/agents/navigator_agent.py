"""
Main codebase navigator agent using LangChain
"""

import os
import json
from typing import List, Dict, Any, Optional, Union
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferWindowMemory
from langchain_openai import ChatOpenAI
from langchain import hub
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool

from ..core import CodebaseVectorStore, RepositoryAnalyzer
from ..tools import create_tools, create_tavily_tool, create_github_tools
from .response_models import NavigatorResponse, Citation, RetrievedSource, ProposedPatch, TestSuggestion, RiskAssessment


class CodebaseNavigatorAgent:
    """
    Main agent for codebase navigation and code review with structured responses
    """
    
    def __init__(
        self,
        vectorstore: CodebaseVectorStore,
        repo_path: str,
        model_name: str = "gpt-4-turbo-preview",
        tavily_api_key: Optional[str] = None,
        temperature: float = 0.1
    ):
        self.vectorstore = vectorstore
        self.repo_path = repo_path
        self.repo_analyzer = RepositoryAnalyzer(repo_path)
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Create tools
        self.tools = create_tools(repo_path, vectorstore)
        
        # Add GitHub analysis tools
        github_token = os.getenv("GITHUB_TOKEN")
        github_tools = create_github_tools(github_token)
        self.tools.extend(github_tools)
        
        # Add Tavily search if API key is available
        if tavily_api_key:
            self.tools.append(create_tavily_tool(tavily_api_key))
        
        # Initialize memory
        self.memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=10  # Keep last 10 exchanges
        )
        
        # Create agent
        self.agent = self._create_agent()
        
        # Create agent executor
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            max_iterations=10,
            early_stopping_method="generate"
        )
    
    def _create_agent(self):
        """Create the structured chat agent"""
        
        # Get the react prompt template from hub
        prompt = hub.pull("hwchase17/react-chat")
        
        # Add our custom system prompt
        system_prompt = self._get_system_prompt()
        prompt = prompt.partial(system_message=system_prompt)
        
        # Create react agent
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        return agent
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent"""
        
        # Get repository information
        repo_info = self.repo_analyzer.get_project_info()
        
        return f"""You are **Codebase Navigator & Reviewer**, a meticulous senior engineer agent for repository analysis and code review.

## Repository Context
- **Project**: {repo_info['name']}
- **Path**: {repo_info['path']}
- **Languages**: {', '.join(repo_info['languages'].keys())}
- **Frameworks**: {', '.join(repo_info['frameworks'])}
- **Git Repository**: {repo_info['is_git_repo']}

## Core Responsibilities
1. **Answer developer questions** about APIs, modules, flows, examples, usage patterns
2. **Diagnose issues** using CI logs, stack traces, and tests  
3. **Refactor or optimize** code on request (complexity, memory, I/O, concurrency, SQL, security)
4. **Generate patches** in unified diff format with targeted edits and companion tests
5. **Ground every claim** in retrieved repository context and credible external sources

## Response Requirements
You MUST respond with a valid JSON object following this exact schema:

```json
{{
  "answer": "Developer-friendly explanation",
  "citations": [
    {{"path": "file/path.py", "start_line": 10, "end_line": 20}}
  ],
  "retrieved_sources": [
    {{"title": "Source Title", "url": "https://example.com"}}
  ],
  "proposed_patch": {{
    "status": "FINAL" or "DRAFT",
    "diff": "unified diff content"
  }},
  "tests": {{
    "suggested": true,
    "commands": ["pytest tests/"],
    "new_tests": [{{"path": "test_file.py", "purpose": "Test description"}}]
  }},
  "risk": {{
    "level": "low" | "medium" | "high",
    "concerns": ["Risk concern 1", "Risk concern 2"],
    "roll_back": "How to undo changes"
  }}
}}
```

## Workflow Process
1. **Clarify Intent**: Understand if this is a question vs. change request
2. **Retrieve Context**: Use retrieve_code tool to get relevant chunks, then read_file for full context
3. **Build Hypothesis**: Form understanding based on retrieved code
4. **External Research**: Use tavily_search for official docs/standards if needed
5. **Generate Response**: Provide explanation or create patches with proper citations

## Patch Generation Rules
When generating patches:
- Create **minimal unified diffs** that apply cleanly with `git apply`
- Include proper file headers: `--- a/<path>` and `+++ b/<path>`
- Each hunk starts with `@@ -<start,len> +<start,len> @@`
- Preserve whitespace and formatting exactly
- Provide companion tests for behavior changes
- Mark as DRAFT if uncertain, FINAL if confident

## Quality Standards
- **Always cite sources** with exact file paths and line ranges
- **Never invent APIs** - verify everything through retrieval
- **Prefer secure defaults** - parameterized queries, input validation, etc.
- **Consider performance** - time/space complexity, N+1 queries, blocking I/O
- **Provide rollback plans** for risky changes

## Tool Usage
- **retrieve_code**: Search vector store for relevant code chunks
- **read_file**: Get full file contents around retrieved chunks  
- **search_repo**: Use ripgrep for pattern matching
- **tavily_search**: Get external documentation when local context insufficient
- **run_lint**: Check code quality before finalizing patches
- **run_tests**: Validate changes don't break existing functionality

Remember: Ground every claim in retrieved code context and cite exact file locations. When uncertain, mark patches as DRAFT and explain limitations.
"""
    
    def query(self, question: str, context: Optional[Dict[str, Any]] = None) -> NavigatorResponse:
        """
        Query the agent with a developer question
        
        Args:
            question: The developer's question or request
            context: Optional additional context (file paths, error messages, etc.)
            
        Returns:
            NavigatorResponse with structured answer
        """
        # Prepare input with context
        input_text = question
        if context:
            input_text += f"\n\nAdditional context: {json.dumps(context, indent=2)}"
        
        try:
            # Run the agent
            result = self.agent_executor.invoke({"input": input_text})
            
            # Parse the response
            response_text = result.get("output", "")
            
            # Try to parse as JSON first
            try:
                response_data = json.loads(response_text)
                return NavigatorResponse(**response_data)
            except json.JSONDecodeError:
                # If not JSON, create a basic response
                return NavigatorResponse(
                    answer=response_text,
                    citations=[],
                    retrieved_sources=[]
                )
                
        except Exception as e:
            return NavigatorResponse(
                answer=f"Error processing query: {str(e)}",
                citations=[],
                retrieved_sources=[]
            )
    
    def diagnose_issue(
        self, 
        error_message: str, 
        file_path: Optional[str] = None,
        stack_trace: Optional[str] = None
    ) -> NavigatorResponse:
        """
        Diagnose a specific issue with error context
        
        Args:
            error_message: The error message
            file_path: Optional file where error occurred
            stack_trace: Optional full stack trace
            
        Returns:
            NavigatorResponse with diagnosis and potential fixes
        """
        context = {
            "error_message": error_message,
            "file_path": file_path,
            "stack_trace": stack_trace
        }
        
        question = f"Diagnose this error and suggest a fix: {error_message}"
        return self.query(question, context)
    
    def suggest_refactor(
        self, 
        file_path: str, 
        refactor_type: str = "general",
        specific_concerns: Optional[List[str]] = None
    ) -> NavigatorResponse:
        """
        Suggest refactoring for a specific file
        
        Args:
            file_path: Path to file to refactor
            refactor_type: Type of refactoring (performance, readability, security, etc.)
            specific_concerns: Specific areas of concern
            
        Returns:
            NavigatorResponse with refactoring suggestions
        """
        context = {
            "file_path": file_path,
            "refactor_type": refactor_type,
            "concerns": specific_concerns or []
        }
        
        question = f"Analyze {file_path} and suggest {refactor_type} refactoring improvements"
        return self.query(question, context)
    
    def explain_code(self, file_path: str, line_start: Optional[int] = None, line_end: Optional[int] = None) -> NavigatorResponse:
        """
        Explain how specific code works
        
        Args:
            file_path: Path to file to explain
            line_start: Optional starting line number
            line_end: Optional ending line number
            
        Returns:
            NavigatorResponse with code explanation
        """
        context = {
            "file_path": file_path,
            "line_start": line_start,
            "line_end": line_end
        }
        
        line_info = ""
        if line_start and line_end:
            line_info = f" (lines {line_start}-{line_end})"
        
        question = f"Explain how the code in {file_path}{line_info} works"
        return self.query(question, context)
    
    def find_usage_examples(self, api_or_function: str) -> NavigatorResponse:
        """
        Find usage examples of an API or function
        
        Args:
            api_or_function: Name of API, function, or class to find examples for
            
        Returns:
            NavigatorResponse with usage examples
        """
        question = f"Find and show usage examples of {api_or_function} in this codebase"
        return self.query(question)
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the conversation history"""
        messages = self.memory.chat_memory.messages
        history = []
        
        for message in messages:
            if isinstance(message, HumanMessage):
                history.append({"role": "human", "content": message.content})
            elif isinstance(message, AIMessage):
                history.append({"role": "assistant", "content": message.content})
        
        return history
    
    def clear_memory(self):
        """Clear the conversation memory"""
        self.memory.clear()


def create_navigator_agent(
    vectorstore: CodebaseVectorStore,
    repo_path: str,
    model_name: str = "gpt-4-turbo-preview",
    tavily_api_key: Optional[str] = None,
    temperature: float = 0.1
) -> CodebaseNavigatorAgent:
    """
    Create a codebase navigator agent
    
    Args:
        vectorstore: Initialized vector store with indexed codebase
        repo_path: Path to repository root
        model_name: OpenAI model name
        tavily_api_key: Tavily API key for web search
        temperature: LLM temperature for responses
        
    Returns:
        CodebaseNavigatorAgent instance
    """
    return CodebaseNavigatorAgent(
        vectorstore=vectorstore,
        repo_path=repo_path,
        model_name=model_name,
        tavily_api_key=tavily_api_key,
        temperature=temperature
    )
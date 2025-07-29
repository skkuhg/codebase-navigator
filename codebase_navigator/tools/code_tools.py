"""
Core code analysis and retrieval tools
"""

import os
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, ClassVar
from pydantic import BaseModel, Field
from langchain.tools import BaseTool


class CodeChunk(BaseModel):
    """Represents a chunk of code with metadata"""
    path: str
    start_line: int
    end_line: int
    snippet: str
    score: float = 0.0


class FileContent(BaseModel):
    """Represents file content"""
    path: str
    text: Optional[str] = None
    lines: Optional[List[Dict[str, Union[int, str]]]] = None


class RepoMatch(BaseModel):
    """Represents a search match in the repository"""
    path: str
    line: int
    text: str


class CILogResult(BaseModel):
    """CI log results"""
    status: str
    failing_tests: List[str] = []
    logs: str = ""


class LintResult(BaseModel):
    """Lint result"""
    path: str
    line: int
    rule: str
    message: str
    severity: str


class TestResult(BaseModel):
    """Test execution result"""
    passed: int
    failed: int
    summary: str
    failing: List[Dict[str, str]] = []


class RetrieveCodeTool(BaseTool):
    """Tool for retrieving code chunks from vector store"""
    name: str = "retrieve_code"
    description: str = """Search the vector index for relevant code chunks.
    Input: {"query": str, "k": int}
    Output: List of code chunks with metadata"""
    
    vectorstore: Any = None
    
    def __init__(self, vectorstore=None, **kwargs):
        super().__init__(**kwargs)
        self.vectorstore = vectorstore
    
    def _run(self, query: str, k: int = 5) -> List[CodeChunk]:
        if not self.vectorstore:
            return []
        
        try:
            docs = self.vectorstore.similarity_search_with_score(query, k=k)
            chunks = []
            
            for doc, score in docs:
                metadata = doc.metadata
                chunk = CodeChunk(
                    path=metadata.get('path', ''),
                    start_line=metadata.get('start_line', 0),
                    end_line=metadata.get('end_line', 0),
                    snippet=doc.page_content,
                    score=score
                )
                chunks.append(chunk)
                
            return chunks
        except Exception as e:
            return []


class ReadFileTool(BaseTool):
    """Tool for reading file contents"""
    name: str = "read_file"
    description: str = """Read file contents with optional line range.
    Input: {"path": str, "start_line": int, "end_line": int}
    Output: File content with line numbers"""
    
    repo_path: str = "./"
    
    def _run(self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> FileContent:
        try:
            full_path = Path(self.repo_path) / path
            
            if not full_path.exists():
                return FileContent(path=path, text="File not found")
            
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            if start_line is None and end_line is None:
                return FileContent(path=path, text=''.join(lines))
            
            start_idx = (start_line - 1) if start_line else 0
            end_idx = end_line if end_line else len(lines)
            
            selected_lines = []
            for i, line in enumerate(lines[start_idx:end_idx], start=start_idx + 1):
                selected_lines.append({"no": i, "text": line})
            
            return FileContent(path=path, lines=selected_lines)
            
        except Exception as e:
            return FileContent(path=path, text=f"Error reading file: {str(e)}")


class SearchRepoTool(BaseTool):
    """Tool for searching repository with ripgrep/grep"""
    name: str = "search_repo"
    description: str = """Search repository for patterns using ripgrep.
    Input: {"glob": str or list[str]}
    Output: List of matches with file path, line number, and text"""
    
    repo_path: str = "./"
    
    def _run(self, glob: Union[str, List[str]], pattern: Optional[str] = None) -> List[RepoMatch]:
        try:
            if isinstance(glob, str):
                search_pattern = glob
            else:
                search_pattern = pattern or ""
            
            cmd = ["rg", "--line-number", "--no-heading"]
            if isinstance(glob, list):
                for g in glob:
                    cmd.extend(["--glob", g])
            
            cmd.append(search_pattern)
            
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            matches = []
            for line in result.stdout.splitlines():
                if ':' in line:
                    parts = line.split(':', 2)
                    if len(parts) >= 3:
                        path, line_no, text = parts[0], parts[1], parts[2]
                        matches.append(RepoMatch(
                            path=path,
                            line=int(line_no),
                            text=text.strip()
                        ))
            
            return matches
            
        except Exception as e:
            return []


class GetCILogsTool(BaseTool):
    """Tool for getting CI logs and status"""
    name: str = "get_ci_logs"
    description: str = """Get CI logs and status for a run/branch/commit.
    Input: run_id or branch or commit
    Output: CI status and logs"""
    
    def _run(self, identifier: str) -> CILogResult:
        # This would integrate with your CI system (GitHub Actions, Jenkins, etc.)
        # For now, return a mock result
        return CILogResult(
            status="unknown",
            failing_tests=[],
            logs="CI integration not configured"
        )


class RunLintTool(BaseTool):
    """Tool for running linters"""
    name: str = "run_lint"
    description: str = """Run linters on specified paths.
    Input: {"paths": list[str]}
    Output: List of lint violations"""
    
    repo_path: str = "./"
    
    def _run(self, paths: List[str]) -> List[LintResult]:
        results = []
        
        for path in paths:
            full_path = Path(self.repo_path) / path
            if not full_path.exists():
                continue
                
            # Python files - use flake8
            if path.endswith('.py'):
                try:
                    result = subprocess.run(
                        ["flake8", "--format=json", str(full_path)],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.stdout:
                        violations = json.loads(result.stdout)
                        for v in violations:
                            results.append(LintResult(
                                path=v.get('filename', path),
                                line=v.get('line_number', 0),
                                rule=v.get('code', 'unknown'),
                                message=v.get('text', ''),
                                severity=v.get('type', 'error')
                            ))
                except:
                    pass
                    
            # JavaScript/TypeScript - use eslint  
            elif path.endswith(('.js', '.ts', '.jsx', '.tsx')):
                try:
                    result = subprocess.run(
                        ["eslint", "--format=json", str(full_path)],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.stdout:
                        violations = json.loads(result.stdout)
                        for file_result in violations:
                            for msg in file_result.get('messages', []):
                                results.append(LintResult(
                                    path=file_result.get('filePath', path),
                                    line=msg.get('line', 0),
                                    rule=msg.get('ruleId', 'unknown'),
                                    message=msg.get('message', ''),
                                    severity=msg.get('severity', 1) == 2 and 'error' or 'warning'
                                ))
                except:
                    pass
        
        return results


class RunTestsTool(BaseTool):
    """Tool for running tests"""
    name: str = "run_tests"
    description: str = """Run tests with specified arguments.
    Input: test command arguments
    Output: Test results summary"""
    
    repo_path: str = "./"
    
    def _run(self, test_args: str) -> TestResult:
        try:
            # Detect test framework and run appropriate command
            if "pytest" in test_args:
                cmd = test_args.split()
            elif "npm test" in test_args:
                cmd = ["npm", "test"] + test_args.replace("npm test", "").split()
            elif "python -m unittest" in test_args:
                cmd = test_args.split()
            else:
                cmd = test_args.split()
            
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse test results (simplified)
            output = result.stdout + result.stderr
            passed = output.count("PASSED") + output.count("✓")
            failed = output.count("FAILED") + output.count("✗")
            
            return TestResult(
                passed=passed,
                failed=failed,
                summary=output[-1000:],  # Last 1000 chars
                failing=[]
            )
            
        except Exception as e:
            return TestResult(
                passed=0,
                failed=1,
                summary=f"Error running tests: {str(e)}",
                failing=[]
            )


class FormatCodeTool(BaseTool):
    """Tool for formatting code"""
    name: str = "format_code"
    description: str = """Apply code formatter to file or patch.
    Input: path or patch content
    Output: formatted content"""
    
    repo_path: str = "./"
    
    def _run(self, path_or_patch: str) -> str:
        try:
            # If it's a file path
            if not path_or_patch.startswith("---") and Path(path_or_patch).exists():
                path = Path(self.repo_path) / path_or_patch
                
                if path.suffix == '.py':
                    result = subprocess.run(
                        ["black", "--quiet", str(path)],
                        capture_output=True,
                        text=True
                    )
                    
                    with open(path, 'r') as f:
                        return f.read()
                        
                elif path.suffix in ['.js', '.ts', '.jsx', '.tsx']:
                    result = subprocess.run(
                        ["prettier", "--write", str(path)],
                        capture_output=True,
                        text=True
                    )
                    
                    with open(path, 'r') as f:
                        return f.read()
            
            # If it's a patch, return as-is for now
            return path_or_patch
            
        except Exception as e:
            return f"Error formatting: {str(e)}"


class SecurityScanTool(BaseTool):
    """Tool for security scanning"""
    name: str = "security_scan"
    description: str = """Run security scan on specified paths.
    Input: {"paths": list[str]}
    Output: List of security issues"""
    
    repo_path: str = "./"
    
    def _run(self, paths: List[str]) -> List[Dict[str, Any]]:
        issues = []
        
        for path in paths:
            full_path = Path(self.repo_path) / path
            if not full_path.exists():
                continue
                
            # Python security scan with bandit
            if path.endswith('.py'):
                try:
                    result = subprocess.run(
                        ["bandit", "-f", "json", str(full_path)],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.stdout:
                        scan_result = json.loads(result.stdout)
                        for issue in scan_result.get('results', []):
                            issues.append({
                                'path': issue.get('filename', path),
                                'line': issue.get('line_number', 0),
                                'severity': issue.get('issue_severity', 'unknown'),
                                'message': issue.get('issue_text', ''),
                                'rule': issue.get('test_id', 'unknown')
                            })
                except:
                    pass
        
        return issues


# Tool instances that can be imported
def create_tools(repo_path: str = "./", vectorstore=None):
    """Create tool instances with proper configuration"""
    
    retrieve_tool = RetrieveCodeTool(vectorstore=vectorstore)
    
    read_tool = ReadFileTool()
    read_tool.repo_path = repo_path
    
    search_tool = SearchRepoTool()
    search_tool.repo_path = repo_path
    
    lint_tool = RunLintTool()
    lint_tool.repo_path = repo_path
    
    test_tool = RunTestsTool()
    test_tool.repo_path = repo_path
    
    format_tool = FormatCodeTool()
    format_tool.repo_path = repo_path
    
    security_tool = SecurityScanTool()
    security_tool.repo_path = repo_path
    
    return [
        retrieve_tool,
        read_tool,
        search_tool,
        GetCILogsTool(),
        lint_tool,
        test_tool,
        format_tool,
        security_tool
    ]


# Direct function interfaces for easier use
def retrieve_code(query: str, k: int = 5, vectorstore=None) -> List[CodeChunk]:
    """Retrieve code chunks from vector store"""
    tool = RetrieveCodeTool()
    tool.vectorstore = vectorstore
    return tool._run(query, k)


def read_file(path: str, start_line: Optional[int] = None, end_line: Optional[int] = None, repo_path: str = "./") -> FileContent:
    """Read file contents"""
    tool = ReadFileTool()
    tool.repo_path = repo_path
    return tool._run(path, start_line, end_line)


def search_repo(pattern: str, glob: Optional[Union[str, List[str]]] = None, repo_path: str = "./") -> List[RepoMatch]:
    """Search repository"""
    tool = SearchRepoTool()
    tool.repo_path = repo_path
    return tool._run(glob or pattern, pattern if glob else None)


def get_ci_logs(identifier: str) -> CILogResult:
    """Get CI logs"""
    tool = GetCILogsTool()
    return tool._run(identifier)


def run_lint(paths: List[str], repo_path: str = "./") -> List[LintResult]:
    """Run linters"""
    tool = RunLintTool()
    tool.repo_path = repo_path
    return tool._run(paths)


def run_tests(test_args: str, repo_path: str = "./") -> TestResult:
    """Run tests"""
    tool = RunTestsTool()
    tool.repo_path = repo_path
    return tool._run(test_args)


def format_code(path_or_patch: str, repo_path: str = "./") -> str:
    """Format code"""
    tool = FormatCodeTool()
    tool.repo_path = repo_path
    return tool._run(path_or_patch)


def security_scan(paths: List[str], repo_path: str = "./") -> List[Dict[str, Any]]:
    """Security scan"""
    tool = SecurityScanTool()
    tool.repo_path = repo_path
    return tool._run(paths)
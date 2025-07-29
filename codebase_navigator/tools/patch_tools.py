"""
Unified diff patch generation and application tools
"""

import os
import difflib
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel
from langchain.tools import BaseTool


class UnifiedDiff(BaseModel):
    """Represents a unified diff patch"""
    old_path: str
    new_path: str
    diff_content: str
    hunks: List[Dict[str, Any]] = []


class PatchResult(BaseModel):
    """Result of patch application"""
    success: bool
    message: str
    applied_files: List[str] = []
    conflicts: List[str] = []


def generate_unified_diff(
    old_content: str, 
    new_content: str, 
    old_path: str, 
    new_path: Optional[str] = None,
    context_lines: int = 3
) -> str:
    """
    Generate a unified diff between old and new content
    
    Args:
        old_content: Original file content
        new_content: Modified file content  
        old_path: Path to the original file
        new_path: Path to the new file (defaults to old_path)
        context_lines: Number of context lines around changes
        
    Returns:
        Unified diff string in standard format
    """
    if new_path is None:
        new_path = old_path
    
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{old_path}",
        tofile=f"b/{new_path}",
        n=context_lines
    )
    
    return ''.join(diff)


def parse_unified_diff(diff_content: str) -> List[UnifiedDiff]:
    """
    Parse a unified diff into structured format
    
    Args:
        diff_content: Raw unified diff content
        
    Returns:
        List of UnifiedDiff objects
    """
    diffs = []
    current_diff = None
    current_hunk = None
    
    for line in diff_content.splitlines():
        if line.startswith('--- '):
            if current_diff:
                diffs.append(current_diff)
            
            old_path = line[4:].strip()
            if old_path.startswith('a/'):
                old_path = old_path[2:]
            current_diff = UnifiedDiff(old_path=old_path, new_path="", diff_content="")
            
        elif line.startswith('+++ '):
            if current_diff:
                new_path = line[4:].strip()
                if new_path.startswith('b/'):
                    new_path = new_path[2:]
                current_diff.new_path = new_path
                
        elif line.startswith('@@'):
            if current_hunk:
                current_diff.hunks.append(current_hunk)
            
            # Parse hunk header: @@ -start,count +start,count @@
            parts = line.split()
            old_range = parts[1][1:].split(',')
            new_range = parts[2][1:].split(',')
            
            current_hunk = {
                'old_start': int(old_range[0]),
                'old_count': int(old_range[1]) if len(old_range) > 1 else 1,
                'new_start': int(new_range[0]), 
                'new_count': int(new_range[1]) if len(new_range) > 1 else 1,
                'lines': []
            }
            
        elif current_hunk and (line.startswith(' ') or line.startswith('-') or line.startswith('+')):
            current_hunk['lines'].append(line)
            
        if current_diff:
            current_diff.diff_content += line + '\n'
    
    if current_hunk and current_diff:
        current_diff.hunks.append(current_hunk)
    if current_diff:
        diffs.append(current_diff)
        
    return diffs


class WritePatchTool(BaseTool):
    """Tool for applying unified diff patches"""
    name: str = "write_patch"
    description: str = """Apply a unified diff patch to files.
    Input: {"unified_diff": str, "repo_path": str, "dry_run": bool}
    Output: Result of patch application"""
    
    repo_path: str = "./"
    
    def _run(self, unified_diff: str, dry_run: bool = False) -> PatchResult:
        """
        Apply a unified diff patch
        
        Args:
            unified_diff: The unified diff content
            dry_run: If True, don't actually apply changes
            
        Returns:
            PatchResult with success status and details
        """
        try:
            # Parse the diff to understand what files are being modified
            diffs = parse_unified_diff(unified_diff)
            applied_files = []
            conflicts = []
            
            if dry_run:
                # Just validate the patch can be applied
                return PatchResult(
                    success=True,
                    message=f"Dry run successful. Would modify {len(diffs)} files.",
                    applied_files=[d.new_path for d in diffs],
                    conflicts=[]
                )
            
            # Create a temporary patch file
            patch_file = Path(self.repo_path) / ".temp_patch"
            with open(patch_file, 'w') as f:
                f.write(unified_diff)
            
            try:
                # Apply patch using git apply (more reliable than patch command)
                result = subprocess.run(
                    ["git", "apply", "--check", str(patch_file)],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    # Patch can be applied cleanly
                    result = subprocess.run(
                        ["git", "apply", str(patch_file)],
                        cwd=self.repo_path,
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        applied_files = [d.new_path for d in diffs]
                        return PatchResult(
                            success=True,
                            message="Patch applied successfully",
                            applied_files=applied_files,
                            conflicts=[]
                        )
                    else:
                        return PatchResult(
                            success=False,
                            message=f"Failed to apply patch: {result.stderr}",
                            applied_files=[],
                            conflicts=[]
                        )
                else:
                    # Try to apply with 3-way merge
                    result = subprocess.run(
                        ["git", "apply", "--3way", str(patch_file)],
                        cwd=self.repo_path,
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        applied_files = [d.new_path for d in diffs]
                        return PatchResult(
                            success=True,
                            message="Patch applied with 3-way merge",
                            applied_files=applied_files,
                            conflicts=[]
                        )
                    else:
                        conflicts = [d.new_path for d in diffs]
                        return PatchResult(
                            success=False,
                            message=f"Patch conflicts detected: {result.stderr}",
                            applied_files=[],
                            conflicts=conflicts
                        )
                        
            finally:
                # Clean up temp patch file
                if patch_file.exists():
                    patch_file.unlink()
                    
        except Exception as e:
            return PatchResult(
                success=False,
                message=f"Error applying patch: {str(e)}",
                applied_files=[],
                conflicts=[]
            )


def create_minimal_diff(original_file: str, modified_content: str, file_path: str) -> str:
    """
    Create a minimal unified diff that changes only what's necessary
    
    Args:
        original_file: Original file content
        modified_content: New file content
        file_path: Path to the file being modified
        
    Returns:
        Minimal unified diff string
    """
    # Split into lines for comparison
    original_lines = original_file.splitlines(keepends=True)
    modified_lines = modified_content.splitlines(keepends=True)
    
    # Generate diff with minimal context (1 line)
    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        n=1  # Minimal context
    )
    
    return ''.join(diff)


def validate_diff_syntax(diff_content: str) -> Tuple[bool, str]:
    """
    Validate that a diff has correct syntax
    
    Args:
        diff_content: The unified diff content
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        lines = diff_content.splitlines()
        
        if not lines:
            return False, "Empty diff"
        
        # Check for proper file headers
        has_old_header = any(line.startswith('--- ') for line in lines)
        has_new_header = any(line.startswith('+++ ') for line in lines)
        
        if not (has_old_header and has_new_header):
            return False, "Missing file headers (--- and +++)"
        
        # Check for hunk headers
        has_hunk_header = any(line.startswith('@@') for line in lines)
        if not has_hunk_header:
            return False, "Missing hunk headers (@@)"
        
        # Validate hunk header format
        for line in lines:
            if line.startswith('@@'):
                try:
                    # Parse @@ -start,count +start,count @@
                    parts = line.split()
                    if len(parts) < 3:
                        return False, f"Invalid hunk header format: {line}"
                    
                    old_range = parts[1][1:]  # Remove leading -
                    new_range = parts[2][1:]  # Remove leading +
                    
                    # Validate range format
                    if ',' in old_range:
                        old_start, old_count = old_range.split(',')
                        int(old_start)
                        int(old_count)
                    else:
                        int(old_range)
                        
                    if ',' in new_range:
                        new_start, new_count = new_range.split(',')
                        int(new_start)
                        int(new_count)
                    else:
                        int(new_range)
                        
                except (ValueError, IndexError):
                    return False, f"Invalid hunk header numbers: {line}"
        
        return True, "Valid diff format"
        
    except Exception as e:
        return False, f"Error validating diff: {str(e)}"


# Direct function interfaces
def write_patch(unified_diff: str, repo_path: str = "./", dry_run: bool = False) -> PatchResult:
    """Apply a unified diff patch to files"""
    tool = WritePatchTool()
    tool.repo_path = repo_path
    return tool._run(unified_diff, dry_run)


def create_patch_tool(repo_path: str = "./") -> WritePatchTool:
    """Create a patch tool instance"""
    tool = WritePatchTool()
    tool.repo_path = repo_path
    return tool
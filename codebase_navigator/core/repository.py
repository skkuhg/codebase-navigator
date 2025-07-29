"""
Repository analysis and metadata extraction
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import git
from git.exc import InvalidGitRepositoryError


class RepositoryAnalyzer:
    """
    Analyze repository structure and extract metadata
    """
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.git_repo = None
        
        # Try to initialize git repository
        try:
            self.git_repo = git.Repo(repo_path)
        except InvalidGitRepositoryError:
            self.git_repo = None
    
    def get_project_info(self) -> Dict[str, Any]:
        """
        Extract basic project information
        
        Returns:
            Dictionary with project metadata
        """
        info = {
            'name': self.repo_path.name,
            'path': str(self.repo_path.absolute()),
            'is_git_repo': self.git_repo is not None,
            'languages': self._detect_languages(),
            'frameworks': self._detect_frameworks(),
            'structure': self._analyze_structure(),
            'dependencies': self._extract_dependencies(),
            'git_info': self._get_git_info() if self.git_repo else None
        }
        
        return info
    
    def _detect_languages(self) -> Dict[str, int]:
        """Detect programming languages and count files"""
        language_extensions = {
            'Python': ['.py'],
            'JavaScript': ['.js', '.jsx', '.mjs'],
            'TypeScript': ['.ts', '.tsx'],
            'Java': ['.java'],
            'Go': ['.go'],
            'Rust': ['.rs'],
            'C': ['.c', '.h'],
            'C++': ['.cpp', '.cc', '.cxx', '.hpp'],
            'PHP': ['.php'],
            'Ruby': ['.rb'],
            'Scala': ['.scala'],
            'Kotlin': ['.kt'],
            'Swift': ['.swift'],
            'Dart': ['.dart'],
            'Shell': ['.sh', '.bash', '.zsh'],
            'SQL': ['.sql'],
            'HTML': ['.html', '.htm'],
            'CSS': ['.css', '.scss', '.sass', '.less'],
            'Markdown': ['.md', '.markdown'],
            'JSON': ['.json'],
            'YAML': ['.yaml', '.yml'],
            'XML': ['.xml']
        }
        
        language_counts = {}
        
        for file_path in self.repo_path.rglob('*'):
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                
                for language, extensions in language_extensions.items():
                    if suffix in extensions:
                        language_counts[language] = language_counts.get(language, 0) + 1
                        break
        
        return language_counts
    
    def _detect_frameworks(self) -> List[str]:
        """Detect frameworks and libraries used"""
        frameworks = []
        
        # Check for common framework indicators
        framework_indicators = {
            'React': ['package.json', 'react'],
            'Vue.js': ['package.json', 'vue'],
            'Angular': ['package.json', 'angular'],
            'Django': ['manage.py', 'django'],
            'Flask': ['requirements.txt', 'flask'],
            'FastAPI': ['requirements.txt', 'fastapi'],
            'Express.js': ['package.json', 'express'],
            'Next.js': ['package.json', 'next'],
            'Nuxt.js': ['package.json', 'nuxt'],
            'Spring Boot': ['pom.xml', 'spring-boot'],
            'Rails': ['Gemfile', 'rails'],
            'Laravel': ['composer.json', 'laravel'],
            'Symfony': ['composer.json', 'symfony']
        }
        
        for framework, (file_indicator, content_indicator) in framework_indicators.items():
            indicator_file = self.repo_path / file_indicator
            
            if indicator_file.exists():
                try:
                    content = indicator_file.read_text(encoding='utf-8', errors='ignore')
                    if content_indicator.lower() in content.lower():
                        frameworks.append(framework)
                except:
                    pass
        
        return frameworks
    
    def _analyze_structure(self) -> Dict[str, Any]:
        """Analyze repository structure"""
        structure = {
            'total_files': 0,
            'total_directories': 0,
            'max_depth': 0,
            'common_directories': [],
            'config_files': []
        }
        
        # Common configuration files
        config_files = [
            'package.json', 'package-lock.json', 'yarn.lock',
            'requirements.txt', 'Pipfile', 'pyproject.toml', 'setup.py',
            'Cargo.toml', 'go.mod', 'pom.xml', 'build.gradle',
            'Dockerfile', 'docker-compose.yml',
            '.gitignore', '.gitattributes',
            'README.md', 'LICENSE', 'CHANGELOG.md',
            '.env.example', 'config.yml', 'settings.json'
        ]
        
        # Count files and directories
        for item in self.repo_path.rglob('*'):
            if item.is_file():
                structure['total_files'] += 1
                
                # Check for config files
                if item.name in config_files:
                    structure['config_files'].append(str(item.relative_to(self.repo_path)))
                    
                # Calculate depth
                depth = len(item.relative_to(self.repo_path).parts)
                structure['max_depth'] = max(structure['max_depth'], depth)
                
            elif item.is_dir():
                structure['total_directories'] += 1
        
        # Find common directory patterns
        common_dirs = set()
        for item in self.repo_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                common_dirs.add(item.name)
        
        structure['common_directories'] = list(common_dirs)
        
        return structure
    
    def _extract_dependencies(self) -> Dict[str, List[str]]:
        """Extract project dependencies"""
        dependencies = {}
        
        # Python dependencies
        requirements_files = ['requirements.txt', 'Pipfile', 'pyproject.toml']
        for req_file in requirements_files:
            file_path = self.repo_path / req_file
            if file_path.exists():
                dependencies['python'] = self._parse_python_deps(file_path)
                break
        
        # Node.js dependencies
        package_json = self.repo_path / 'package.json'
        if package_json.exists():
            dependencies['nodejs'] = self._parse_nodejs_deps(package_json)
        
        # Java dependencies
        pom_xml = self.repo_path / 'pom.xml'
        if pom_xml.exists():
            dependencies['java'] = ['Maven project detected']
        
        build_gradle = self.repo_path / 'build.gradle'
        if build_gradle.exists():
            dependencies['java'] = ['Gradle project detected']
        
        return dependencies
    
    def _parse_python_deps(self, file_path: Path) -> List[str]:
        """Parse Python dependencies"""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            if file_path.name == 'requirements.txt':
                deps = []
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Extract package name (before ==, >=, etc.)
                        dep_name = line.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0].strip()
                        deps.append(dep_name)
                return deps
                
            elif file_path.name == 'pyproject.toml':
                # Basic TOML parsing for dependencies
                deps = []
                in_deps_section = False
                for line in content.splitlines():
                    line = line.strip()
                    if line == '[tool.poetry.dependencies]' or line == '[project.dependencies]':
                        in_deps_section = True
                    elif line.startswith('[') and in_deps_section:
                        in_deps_section = False
                    elif in_deps_section and '=' in line:
                        dep_name = line.split('=')[0].strip().strip('"')
                        if dep_name != 'python':
                            deps.append(dep_name)
                return deps
                
        except:
            pass
        
        return []
    
    def _parse_nodejs_deps(self, file_path: Path) -> List[str]:
        """Parse Node.js dependencies"""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            package_data = json.loads(content)
            
            deps = []
            for dep_type in ['dependencies', 'devDependencies']:
                if dep_type in package_data:
                    deps.extend(package_data[dep_type].keys())
            
            return deps
        except:
            pass
        
        return []
    
    def _get_git_info(self) -> Optional[Dict[str, Any]]:
        """Extract Git repository information"""
        if not self.git_repo:
            return None
        
        try:
            git_info = {
                'branch': self.git_repo.active_branch.name,
                'commit_count': len(list(self.git_repo.iter_commits())),
                'contributors': len(set(commit.author.email for commit in self.git_repo.iter_commits())),
                'last_commit': {
                    'hash': self.git_repo.head.commit.hexsha[:8],
                    'message': self.git_repo.head.commit.message.strip(),
                    'author': self.git_repo.head.commit.author.name,
                    'date': self.git_repo.head.commit.committed_date
                },
                'remotes': [remote.url for remote in self.git_repo.remotes],
                'has_uncommitted_changes': self.git_repo.is_dirty(),
                'untracked_files': len(self.git_repo.untracked_files)
            }
            
            return git_info
        except Exception as e:
            return {'error': str(e)}
    
    def get_file_history(self, file_path: str, max_commits: int = 10) -> List[Dict[str, Any]]:
        """Get commit history for a specific file"""
        if not self.git_repo:
            return []
        
        try:
            commits = list(self.git_repo.iter_commits(paths=file_path, max_count=max_commits))
            
            history = []
            for commit in commits:
                history.append({
                    'hash': commit.hexsha[:8],
                    'message': commit.message.strip(),
                    'author': commit.author.name,
                    'date': commit.committed_date,
                    'changes': self._get_commit_changes(commit, file_path)
                })
            
            return history
        except:
            return []
    
    def _get_commit_changes(self, commit, file_path: str) -> Dict[str, int]:
        """Get file changes statistics for a commit"""
        try:
            if commit.parents:
                diff = commit.parents[0].diff(commit, paths=file_path)
                if diff:
                    diff_item = diff[0]
                    return {
                        'insertions': diff_item.diff.decode('utf-8', errors='ignore').count('\n+'),
                        'deletions': diff_item.diff.decode('utf-8', errors='ignore').count('\n-')
                    }
        except:
            pass
        
        return {'insertions': 0, 'deletions': 0}
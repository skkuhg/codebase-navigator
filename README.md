# Codebase Navigator & Reviewer

> **AI-powered autonomous agent that navigates local Git repositories and GitHub codebases, answers developer questions with Retrieval‑Augmented Generation (RAG), and provides intelligent code analysis.**

## 🎯 Features

- **🧭 Intelligent Code Navigation**: Semantic search across your entire codebase using vector embeddings
- **🤖 AI-Powered Analysis**: LangChain agent that understands code patterns, APIs, and architectural decisions  
- **� GitHub Integration**: Analyze any GitHub repository with RAG-powered insights
- **�🔍 External Knowledge**: Tavily integration for accessing official documentation and standards
- **🛠️ Patch Generation**: Creates minimal, applicable unified diffs with proper testing suggestions
- **📊 Risk Assessment**: Evaluates changes with rollback plans and security considerations
- **💬 Natural Language Interface**: Ask questions about your code in plain English
- **🔍 Repository Search**: Search and analyze GitHub repositories with advanced filtering

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/skkuhg/Codebase-Navigator.git
cd codebase-navigator

# Install the package
pip install -e .

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Environment Setup

```bash
# Required: OpenAI API Key for embeddings and LLM
OPENAI_API_KEY=your_openai_api_key_here

# Required: Tavily API Key for web search  
TAVILY_API_KEY=your_tavily_api_key_here

# Optional: GitHub token for private repos and higher rate limits
GITHUB_TOKEN=your_github_token_here

# Optional: Customize paths and models
REPO_PATH=./
VECTOR_STORE_PATH=./vector_store
EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4-turbo-preview
```

### Local Repository Analysis

```bash
# Index current directory
codebase-nav index

# Index specific repository
codebase-nav -r /path/to/repo index --force

# View repository information
# Query your local codebase
codebase-nav query --interactive
codebase-nav query "How does authentication work?"
```

### GitHub Repository Analysis

```bash
# Analyze any GitHub repository
codebase-nav github https://github.com/owner/repository

# Search GitHub repositories
codebase-nav search-github "machine learning" --language python --stars ">100"

# Query a specific repository
codebase-nav github https://github.com/langchain-ai/langchain --query "How does the agent framework work?"

# Choose download method (zip is faster, clone includes git history)
codebase-nav github https://github.com/owner/repo --method zip
codebase-nav github https://github.com/owner/repo --method clone
```

### Additional Commands

```bash
# Check system status
codebase-nav info
```

## 📖 Usage Examples

### Local Repository Query

```bash
# Interactive mode for local code
codebase-nav query --interactive

# Single question about local code
codebase-nav query "How does authentication work in this codebase?"
```

### GitHub Analysis Examples

```bash
# Analyze a popular framework
codebase-nav github https://github.com/fastapi/fastapi

# Search for Python web frameworks with high stars
codebase-nav search-github "web framework" --language python --stars ">1000" --limit 5

# Quick analysis with immediate query
codebase-nav github https://github.com/django/django --query "How does the ORM work?"
```

### Python API

```python
from codebase_navigator.core import create_vectorstore
from codebase_navigator.agents import create_navigator_agent
from codebase_navigator.core.github_analyzer import create_github_session

# Local repository analysis
vectorstore = create_vectorstore("./vector_store")
vectorstore.index_repository("./my-project")

agent = create_navigator_agent(
    vectorstore=vectorstore,
    repo_path="./my-project"
)

response = agent.query("How do I use the authentication module?")
print(response.answer)

# GitHub repository analysis
github_session = create_github_session("https://github.com/owner/repo")
response = github_session.query("What is the main functionality of this project?")
print(response)

# Get code references
for citation in response.citations:
    print(f"{citation.path}:{citation.start_line}-{citation.end_line}")

# Apply patches if suggested
if response.proposed_patch:
    print(response.proposed_patch.diff)
```

### CLI Examples

```bash
# Get help with a specific API
codebase-nav query "Show me examples of using the User model"

# Understand complex code flows  
codebase-nav query "Explain the data flow from API request to database"

# Get optimization suggestions
codebase-nav refactor slow_function.py -t performance -c "memory usage" -c "database queries"

# Diagnose build failures
codebase-nav diagnose -e "ModuleNotFoundError: No module named 'custom_lib'" -f src/main.py

# Interactive exploration
codebase-nav query -i
❓ Question: How does the caching system work?
📋 Answer: The caching system uses Redis as the backend...
📖 Code References:
  • src/cache/redis_client.py:15-45
  • src/services/cache_service.py:23-67
```

## 🏗️ Architecture

### Core Components

```
codebase_navigator/
├── core/                  # Vector store and embeddings
│   ├── vectorstore.py    # ChromaDB vector store management
│   ├── embeddings.py     # Code chunking and embedding
│   └── repository.py     # Git repository analysis
├── tools/                # LangChain tools
│   ├── code_tools.py     # File access, search, linting
│   ├── tavily_tools.py   # Web search integration
│   └── patch_tools.py    # Unified diff generation
├── agents/               # LangChain agents
│   ├── navigator_agent.py # Main codebase navigator
│   └── response_models.py # Structured response schemas
└── cli.py               # Command line interface
```

### Supported Languages

- **Primary**: Python, JavaScript/TypeScript, Java, Go, Rust
- **Additional**: C/C++, PHP, Ruby, Scala, Kotlin, Swift, Dart
- **Config**: JSON, YAML, XML, SQL, Shell scripts
- **Docs**: Markdown, reStructuredText, HTML/CSS

## 🛠️ Advanced Features

### Custom Tool Integration

```python
from langchain.tools import BaseTool
from codebase_navigator.agents import create_navigator_agent

class CustomLintTool(BaseTool):
    name = "custom_lint"
    description = "Run custom linting rules"
    
    def _run(self, code: str) -> str:
        # Your custom logic
        return "Lint results"

# Add to agent
agent = create_navigator_agent(vectorstore, repo_path)
agent.tools.append(CustomLintTool())
```

### Structured Response Format

Every agent response follows this JSON schema:

```json
{
  "answer": "Developer-friendly explanation",
  "citations": [
    {"path": "file.py", "start_line": 10, "end_line": 20}
  ],
  "retrieved_sources": [
    {"title": "API Docs", "url": "https://docs.example.com"}
  ],
  "proposed_patch": {
    "status": "FINAL",
    "diff": "--- a/file.py\n+++ b/file.py\n..."
  },
  "tests": {
    "suggested": true,
    "commands": ["pytest tests/"],
    "new_tests": [{"path": "test_new.py", "purpose": "Test new feature"}]
  },
  "risk": {
    "level": "medium",
    "concerns": ["Breaking change", "Performance impact"],
    "roll_back": "git revert <commit>"
  }
}
```

### Vector Store Customization

```python
from codebase_navigator.core.embeddings import CodeChunker

# Custom chunking strategy
chunker = CodeChunker(
    chunk_size=1024,      # Larger chunks
    chunk_overlap=128     # More context overlap
)

# Custom ignore patterns
ignore_patterns = [
    "*.pyc", "__pycache__", ".git", "node_modules",
    "*.min.js", "dist/", "build/", ".env*"
]

vectorstore.index_repository(
    repo_path="./",
    ignore_patterns=ignore_patterns,
    force_reindex=True
)
```

## 🔒 Security & Privacy

- **API Keys**: Store in `.env` file, never commit to repository
- **Code Analysis**: Runs locally, only sends relevant chunks to LLM
- **Patch Generation**: Always review diffs before applying
- **Input Validation**: All user inputs are sanitized and validated
- **Secret Detection**: Automatically flags potential credentials in patches

## 🧪 Testing & Quality

```bash
# Run linting on generated patches
codebase-nav query "Optimize this function" | grep -A 20 "proposed_patch" | codebase-nav lint

# Test changes before applying
codebase-nav refactor myfile.py -t security --dry-run

# Validate patch syntax
codebase-nav query "Fix this bug" --validate-patch
```

## 📊 Performance & Scaling

### Recommendations

- **Small repos (<1000 files)**: Default settings work well
- **Medium repos (1K-10K files)**: Increase chunk size to 1024, use `text-embedding-3-large`
- **Large repos (>10K files)**: Consider splitting into modules, use async processing

### Optimization Tips

```python
# Use MMR for diverse results
retriever = vectorstore.get_retriever(
    search_kwargs={"k": 10, "fetch_k": 50}
)

# Filter by file type
vectorstore.search_code(
    "authentication logic",
    filter_by_language="python",
    filter_by_chunk_type="function_definition"
)

# Batch processing for large changes
for file_path in large_file_list:
    response = agent.suggest_refactor(file_path, "performance")
    # Process in batches
```

## 🔒 Security

⚠️ **Important**: Never commit your `.env` file or expose your API keys!

- The `.env` file is git-ignored by default
- Use `.env.example` as a template
- Keep your API keys secure and never share them publicly

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run the test suite: `pytest`
5. Submit a pull request

### Development Setup

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run linting
flake8 codebase_navigator/
black codebase_navigator/

# Type checking
mypy codebase_navigator/
```

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **LangChain** for the agent framework
- **Tavily** for high-quality web search
- **ChromaDB** for vector storage
- **OpenAI** for embeddings and language models

## 📞 Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/example/codebase-navigator/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/example/codebase-navigator/discussions)
- 📧 **Email**: support@example.com

---

**Built with ❤️ for developers who want to understand and improve their codebases using AI.**

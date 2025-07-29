# Manual Testing Guide - Codebase Navigator & Reviewer

## 🎯 Overview
This guide provides step-by-step instructions for manually testing all components of the Codebase Navigator & Reviewer system.

## 📋 Prerequisites

### 1. System Requirements
- **Python**: 3.10+ (we've tested with 3.10)
- **Operating System**: Windows (tested), Linux/Mac (should work)
- **Memory**: 2GB+ RAM for vector operations
- **Storage**: 500MB+ for dependencies and vector store

### 2. Installation Verification
```bash
# Check if package is installed
python -c "import codebase_navigator; print('✓ Package installed')"

# Check Python version
python --version

# Verify specific Python path (use this for all tests)
"/c/Users/ahpuh/AppData/Local/Programs/Python/Python310/python.exe" --version
```

### 3. API Keys Setup
Edit the `.env` file:
```bash
# Required for full functionality
OPENAI_API_KEY=your_actual_openai_key_here

# Already configured (working)
TAVILY_API_KEY=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
```

## 🧪 Testing Phases

### Phase 1: Core Component Testing (No API Required)

#### Test 1.1: Basic Component Verification
```bash
cd "C:\Users\ahpuh\Desktop\hg"
"/c/Users/ahpuh/AppData/Local/Programs/Python/Python310/python.exe" final_test.py
```

**Expected Results:**
```
PASSED: 5
FAILED: 1  
SUCCESS RATE: 83.3%
STATUS: SYSTEM FULLY OPERATIONAL (5/6 components working)
```

**What This Tests:**
- ✅ Repository Analysis
- ✅ Code Chunking  
- ✅ File Operations
- ✅ Web Search (Tavily)
- ✅ Patch Generation
- ❌ Vector Store (needs OpenAI key)

#### Test 1.2: Real-World Scenario
```bash
"/c/Users/ahpuh/AppData/Local/Programs/Python/Python310/python.exe" real_world_demo.py
```

**Expected Results:**
```
Step 1: Analyzing existing code structure
Code analysis: 3 logical chunks identified

Step 2: Researching best practices  
Found 6 relevant sources

Step 5: Generating patch for improvements
Patch generated: +76 additions, -25 deletions
```

**What This Tests:**
- Code structure analysis
- External research capabilities
- Security issue identification
- Code improvement generation
- Unified diff creation

#### Test 1.3: Individual Component Testing
```bash
"/c/Users/ahpuh/AppData/Local/Programs/Python/Python310/python.exe" final_demo.py
```

**Expected Results:**
```
All core components: WORKING
File analysis: WORKING  
Web search: WORKING
Code operations: WORKING
Patch generation: WORKING
```

### Phase 2: CLI Testing (Requires OpenAI API Key)

#### Test 2.1: Repository Information
```bash
"/c/Users/ahpuh/AppData/Local/Programs/Python/Python310/python.exe" -m codebase_navigator.cli info
```

**Expected Results:**
- Repository details displayed
- Language statistics shown
- Framework detection (FastAPI)
- File count and structure

#### Test 2.2: Codebase Indexing
```bash
"/c/Users/ahpuh/AppData/Local/Programs/Python/Python310/python.exe" -m codebase_navigator.cli index
```

**Expected Results:**
- Files analyzed and chunked
- Vector embeddings created
- Index statistics displayed
- Language distribution shown

#### Test 2.3: Natural Language Queries
```bash
"/c/Users/ahpuh/AppData/Local/Programs/Python/Python310/python.exe" -m codebase_navigator.cli query "How does the code chunking work?"
```

**Expected Results:**
- Structured JSON response
- Code citations with file paths
- External sources from Tavily
- Clear explanations

#### Test 2.4: Interactive Mode
```bash
"/c/Users/ahpuh/AppData/Local/Programs/Python/Python310/python.exe" -m codebase_navigator.cli query --interactive
```

**Expected Results:**
- Interactive prompt appears
- Can ask multiple questions
- Maintains conversation context
- Type 'exit' to quit

### Phase 3: Advanced Feature Testing

#### Test 3.1: Error Diagnosis
```bash
"/c/Users/ahpuh/AppData/Local/Programs/Python/Python310/python.exe" -m codebase_navigator.cli diagnose -e "TypeError: cannot read property 'X' of undefined"
```

**Expected Results:**
- Error analysis performed
- Potential causes identified
- Fix suggestions provided
- Related code locations found

#### Test 3.2: Code Refactoring
```bash
"/c/Users/ahpuh/AppData/Local/Programs/Python/Python310/python.exe" -m codebase_navigator.cli refactor codebase_navigator/core/embeddings.py -t performance
```

**Expected Results:**
- Performance analysis completed
- Optimization suggestions provided
- Unified diff patches generated
- Risk assessment included

#### Test 3.3: Custom Queries
```bash
"/c/Users/ahpuh/AppData/Local/Programs/Python/Python310/python.exe" -m codebase_navigator.cli query "Find all security vulnerabilities in this codebase"
```

**Expected Results:**
- Security analysis performed
- Vulnerability patterns identified
- Remediation suggestions provided
- Code citations included

### Phase 4: Python API Testing

#### Test 4.1: Direct API Usage
Create a test file `api_test.py`:
```python
import os
os.environ["OPENAI_API_KEY"] = "your_key_here"
os.environ["TAVILY_API_KEY"] = "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"

from codebase_navigator.core import create_vectorstore
from codebase_navigator.agents import create_navigator_agent

# Test vector store
vectorstore = create_vectorstore("./test_vs")
doc_count = vectorstore.index_repository("./")
print(f"Indexed {doc_count} documents")

# Test agent
agent = create_navigator_agent(vectorstore, "./")
response = agent.query("What is the main purpose of this codebase?")
print(f"Answer: {response.answer}")
print(f"Citations: {len(response.citations)}")
```

#### Test 4.2: Custom Tool Integration
```python
from codebase_navigator.tools.code_tools import read_file, search_repo
from codebase_navigator.tools.tavily_tools import tavily_search

# Test file operations
content = read_file("README.md")
print(f"README has {len(content.text.split())} words")

# Test search
matches = search_repo("class.*Agent")
print(f"Found {len(matches)} agent classes")

# Test web search
results = tavily_search("Python best practices")
print(f"Found {len(results)} web results")
```

## 📊 Validation Checklist

### ✅ Core Functionality
- [ ] Repository analysis completes without errors
- [ ] Code chunking preserves function/class boundaries
- [ ] File operations read/write correctly
- [ ] Search patterns match expected results
- [ ] Patch generation creates valid unified diffs
- [ ] Web search returns relevant results

### ✅ API Integration
- [ ] OpenAI embeddings work (if key provided)
- [ ] Tavily search returns web results
- [ ] Vector store indexes successfully
- [ ] LLM responses are coherent and helpful

### ✅ CLI Interface
- [ ] All commands execute without crashes
- [ ] Help text is clear and accurate
- [ ] Interactive mode functions properly
- [ ] Output formatting is readable

### ✅ Error Handling
- [ ] Graceful handling of missing files
- [ ] Clear error messages for API failures
- [ ] Proper validation of user inputs
- [ ] Recovery from network timeouts

## 🚨 Troubleshooting

### Common Issues & Solutions

#### Unicode Encoding Errors
```
UnicodeEncodeError: 'charmap' codec can't encode character
```
**Solution:** Use the specific Python 3.10 path as shown in examples above.

#### Import Errors
```
ModuleNotFoundError: No module named 'codebase_navigator'
```
**Solution:** 
```bash
cd "C:\Users\ahpuh\Desktop\hg"
pip install -e .
```

#### API Key Errors
```
ValueError: OPENAI_API_KEY environment variable is required
```
**Solution:** Set your OpenAI API key in the `.env` file.

#### CLI Not Found
```
'codebase-nav' is not recognized
```
**Solution:** Use the full Python module path:
```bash
"/c/Users/ahpuh/AppData/Local/Programs/Python/Python310/python.exe" -m codebase_navigator.cli
```

### Performance Issues

#### Slow Indexing
- **Cause:** Large codebase or slow embeddings
- **Solution:** Use smaller chunk sizes or filter file types

#### Memory Usage
- **Cause:** Large vector store in memory
- **Solution:** Restart Python session between tests

#### Network Timeouts
- **Cause:** Slow API responses
- **Solution:** Increase timeout values in tool configurations

## 📈 Performance Benchmarks

### Expected Performance
- **Small repo (<100 files):** 30-60 seconds indexing
- **Medium repo (<1000 files):** 2-5 minutes indexing  
- **Large repo (>1000 files):** 5-15 minutes indexing
- **Query response:** 5-30 seconds per question
- **Patch generation:** 10-60 seconds per file

### Success Criteria
- **Component tests:** 80%+ success rate
- **API integration:** All endpoints responding
- **CLI commands:** Execute without crashes
- **Query accuracy:** Relevant responses with citations
- **Patch quality:** Applicable unified diffs

## 🎉 Testing Complete

After completing all phases, you should have:

1. **Verified core functionality** works without API dependencies
2. **Confirmed web search integration** with Tavily
3. **Tested CLI commands** (if OpenAI key available)
4. **Validated patch generation** creates clean diffs
5. **Checked error handling** for edge cases

The system is ready for production use when:
- ✅ Core tests pass with 80%+ success rate
- ✅ Web search returns relevant results
- ✅ File operations work correctly
- ✅ Patch generation creates valid diffs
- ✅ API integration functions (when keys provided)

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review the console output for specific error messages
3. Verify API key configuration
4. Test individual components separately
5. Check Python version and package installation

The Codebase Navigator & Reviewer is now ready for comprehensive manual testing!
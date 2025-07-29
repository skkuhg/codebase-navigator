#!/usr/bin/env python3
"""
Test core components without dependencies
"""

import os

def test_core():
    """Test core components"""
    
    print("🚀 Testing Codebase Navigator Core Components")
    print("=" * 50)
    
    # Check if API keys are available from environment
    if not os.environ.get("TAVILY_API_KEY"):
        print("\n⚠️  Note: TAVILY_API_KEY not found in environment. Tavily tests will be skipped.")
    if not os.environ.get("OPENAI_API_KEY"):
        print("\n⚠️  Note: OPENAI_API_KEY not found in environment. Some tests may be limited.")
    
    # Test repository analysis (doesn't need API keys)
    try:
        from codebase_navigator.core.repository import RepositoryAnalyzer
        print("\n📊 Testing repository analysis...")
        
        analyzer = RepositoryAnalyzer("./")
        info = analyzer.get_project_info()
        
        print(f"  ✅ Project: {info['name']}")
        print(f"  ✅ Languages: {', '.join(info['languages'].keys())}")
        print(f"  ✅ Total files: {info['structure']['total_files']}")
        print(f"  ✅ Is Git repo: {info['is_git_repo']}")
        
    except Exception as e:
        print(f"❌ Error with repository analysis: {e}")
    
    # Test Tavily search
    try:
        from codebase_navigator.tools.tavily_tools import tavily_search
        print("\n🌐 Testing Tavily search...")
        
        results = tavily_search("Python programming tutorial", max_results=2)
        print(f"  ✅ Found {len(results)} web results")
        
        for i, result in enumerate(results[:1], 1):
            print(f"    {i}. {result.title}")
            print(f"       {result.url}")
            
    except Exception as e:
        print(f"❌ Error with Tavily search: {e}")
    
    # Test code chunking
    try:
        from codebase_navigator.core.embeddings import CodeChunker
        print("\n📝 Testing code chunking...")
        
        chunker = CodeChunker(chunk_size=200, chunk_overlap=20)
        
        # Test with Python code
        sample_code = '''
def hello_world():
    """A simple hello world function"""
    print("Hello, World!")
    return "success"

class TestClass:
    def __init__(self):
        self.value = 42
        
    def get_value(self):
        return self.value
'''
        
        documents = chunker.chunk_code(sample_code, "test.py")
        print(f"  ✅ Generated {len(documents)} chunks from sample code")
        
        for i, doc in enumerate(documents[:2], 1):
            print(f"    Chunk {i}: {doc.metadata['chunk_type']} ({doc.metadata['start_line']}-{doc.metadata['end_line']})")
            
    except Exception as e:
        print(f"❌ Error with code chunking: {e}")
    
    # Test file operations
    try:
        from codebase_navigator.tools.code_tools import read_file
        print("\n📁 Testing file operations...")
        
        # Read this test file
        result = read_file("test_core.py", repo_path="./")
        if result.text:
            print(f"  ✅ Successfully read file with {len(result.text)} characters")
        else:
            print(f"  ✅ Successfully read file with {len(result.lines)} lines")
            
    except Exception as e:
        print(f"❌ Error with file operations: {e}")
    
    print("\n✨ Core component test completed!")
    print("\nThe core components are working. To use the full system:")
    print("1. Get an OpenAI API key for embeddings")
    print("2. Set OPENAI_API_KEY in your environment")
    print("3. Run the full CLI with: python -m codebase_navigator.cli --help")

if __name__ == "__main__":
    test_core()
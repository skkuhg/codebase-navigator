"""
Command Line Interface for Codebase Navigator
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional
import click
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.align import Align
from rich.text import Text
from rich.columns import Columns
from rich.rule import Rule
from rich.tree import Tree
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.prompt import Prompt
from dotenv import load_dotenv

from .core import create_vectorstore, RepositoryAnalyzer
from .agents import create_navigator_agent, NavigatorResponse
from .core.github_analyzer import create_github_session, GitHubAnalyzer


# Load environment variables
load_dotenv()

console = Console()

# ASCII Art Banner
BANNER = """
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   ██████╗ ██████╗ ██████╗ ███████╗██████╗  █████╗ ███████╗███████╗           ║
║  ██╔════╝██╔═══██╗██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝           ║
║  ██║     ██║   ██║██║  ██║█████╗  ██████╔╝███████║███████╗█████╗             ║
║  ██║     ██║   ██║██║  ██║██╔══╝  ██╔══██╗██╔══██║╚════██║██╔══╝             ║
║  ╚██████╗╚██████╔╝██████╔╝███████╗██████╔╝██║  ██║███████║███████╗           ║
║   ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝           ║
║                                                                               ║
║   ███╗   ██╗ █████╗ ██╗   ██╗██╗ ██████╗  █████╗ ████████╗ ██████╗ ██████╗  ║
║   ████╗  ██║██╔══██╗██║   ██║██║██╔════╝ ██╔══██╗╚══██╔══╝██╔═══██╗██╔══██╗ ║
║   ██╔██╗ ██║███████║██║   ██║██║██║  ███╗███████║   ██║   ██║   ██║██████╔╝ ║
║   ██║╚██╗██║██╔══██║╚██╗ ██╔╝██║██║   ██║██╔══██║   ██║   ██║   ██║██╔══██╗ ║
║   ██║ ╚████║██║  ██║ ╚████╔╝ ██║╚██████╔╝██║  ██║   ██║   ╚██████╔╝██║  ██║ ║
║   ╚═╝  ╚═══╝╚═╝  ╚═╝  ╚═══╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝ ║
║                                                                               ║
║                        🤖 AI-Powered Code Analysis & Review                   ║
║                     LangChain + Tavily + Vector Embeddings                    ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

def show_banner():
    """Display the application banner"""
    console.print(BANNER, style="bold cyan")
    console.print()

def show_startup_info():
    """Show startup information with style"""
    startup_panel = Panel(
        "[bold green]🚀 Welcome to Codebase Navigator![/bold green]\n\n"
        "✨ Features:\n"
        "  🧭 [cyan]Intelligent Code Navigation[/cyan] - Semantic search across your codebase\n"
        "  🤖 [cyan]AI-Powered Analysis[/cyan] - LangChain agent for code understanding\n"
        "  🔍 [cyan]External Knowledge[/cyan] - Tavily integration for documentation\n"
        "  🛠️ [cyan]Patch Generation[/cyan] - Automated code improvements\n"
        "  📊 [cyan]Risk Assessment[/cyan] - Safety analysis for changes\n"
        "  💬 [cyan]Natural Language[/cyan] - Ask questions in plain English",
        title="[bold blue]🎯 System Ready[/bold blue]",
        border_style="blue",
        padding=(1, 2)
    )
    console.print(startup_panel)


@click.group()
@click.option('--repo-path', '-r', default='./', help='Path to repository root')
@click.option('--vector-store-path', '-v', default='./vector_store', help='Path to vector store')
@click.option('--verbose', '-V', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, repo_path: str, vector_store_path: str, verbose: bool):
    """
    🤖 Codebase Navigator & Reviewer - AI-powered code analysis
    
    Analyze local repositories or explore GitHub codebases with RAG-powered insights.
    """
    # Show banner on startup
    show_banner()
    show_startup_info()
    
    ctx.ensure_object(dict)
    ctx.obj['repo_path'] = Path(repo_path).absolute()
    ctx.obj['vector_store_path'] = Path(vector_store_path).absolute()
    ctx.obj['verbose'] = verbose
    
    # Validate repository path
    if not ctx.obj['repo_path'].exists():
        console.print(Panel(
            f"[red]❌ Repository path {repo_path} does not exist[/red]",
            title="[red]Error[/red]",
            border_style="red"
        ))
        sys.exit(1)


@cli.command()
@click.option('--force', '-f', is_flag=True, help='Force reindexing even if vector store exists')
@click.option('--chunk-size', default=512, help='Chunk size for code splitting')
@click.option('--chunk-overlap', default=64, help='Chunk overlap for context')
@click.pass_context
def index(ctx, force: bool, chunk_size: int, chunk_overlap: int):
    """🔍 Index the repository for semantic search"""
    repo_path = ctx.obj['repo_path']
    vector_store_path = ctx.obj['vector_store_path']
    
    # Show indexing header
    console.print(Rule(f"[bold blue]🔍 INDEXING REPOSITORY[/bold blue]", style="blue"))
    console.print(f"[cyan]📁 Repository:[/cyan] {repo_path}")
    console.print(f"[cyan]💾 Vector Store:[/cyan] {vector_store_path}")
    console.print()
    
    # Analyze repository first
    analyzer = RepositoryAnalyzer(str(repo_path))
    repo_info = analyzer.get_project_info()
    
    # Display repository info with enhanced styling
    repo_table = Table(title="📊 Repository Analysis", show_header=True, header_style="bold magenta")
    repo_table.add_column("🏷️ Property", style="cyan", min_width=15)
    repo_table.add_column("📋 Value", style="green")
    
    repo_table.add_row("Name", f"[bold]{repo_info['name']}[/bold]")
    repo_table.add_row("Languages", ", ".join(f"[yellow]{lang}[/yellow]" for lang in repo_info['languages'].keys()))
    repo_table.add_row("Frameworks", ", ".join(f"[blue]{fw}[/blue]" for fw in repo_info['frameworks']) or "[dim]None detected[/dim]")
    repo_table.add_row("Total Files", f"[bold green]{repo_info['structure']['total_files']}[/bold green]")
    repo_table.add_row("Git Repository", "[green]✅ Yes[/green]" if repo_info['is_git_repo'] else "[red]❌ No[/red]")
    
    console.print(repo_table)
    console.print()
    
    # Create vector store
    try:
        vectorstore = create_vectorstore(str(vector_store_path))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("🔄 Indexing files...", total=None)
            
            # Index repository
            doc_count = vectorstore.index_repository(
                str(repo_path),
                force_reindex=force
            )
            
            progress.update(task, description=f"✅ Indexed {doc_count} documents")
        
        # Success message with panel
        success_panel = Panel(
            f"[bold green]🎉 SUCCESS![/bold green]\n\n"
            f"📊 Indexed [bold cyan]{doc_count}[/bold cyan] document chunks\n"
            f"🚀 Ready for semantic queries!",
            title="[green]✅ Indexing Complete[/green]",
            border_style="green"
        )
        console.print(success_panel)
        
        # Display language statistics with enhanced styling
        lang_stats = vectorstore.get_language_stats()
        if lang_stats:
            console.print(Rule("[blue]📈 Language Distribution[/blue]", style="blue"))
            
            # Create columns for language stats
            lang_columns = []
            for lang, count in sorted(lang_stats.items(), key=lambda x: x[1], reverse=True):
                lang_columns.append(f"[yellow]{lang}[/yellow]: [bold green]{count}[/bold green] chunks")
            
            console.print(Columns(lang_columns, equal=True, expand=True))
            console.print()
                
    except Exception as e:
        error_panel = Panel(
            f"[red]❌ Error indexing repository:[/red]\n\n{str(e)}",
            title="[red]🚨 Error[/red]",
            border_style="red"
        )
        console.print(error_panel)
        sys.exit(1)


@cli.command()
@click.option('--model', '-m', default='gpt-4-turbo-preview', help='OpenAI model to use')
@click.option('--interactive', '-i', is_flag=True, help='Start interactive mode')
@click.argument('question', required=False)
@click.pass_context
def query(ctx, model: str, interactive: bool, question: Optional[str]):
    """🤖 Query the codebase with natural language AI analysis"""
    repo_path = ctx.obj['repo_path']
    vector_store_path = ctx.obj['vector_store_path']
    
    # Check if vector store exists
    if not vector_store_path.exists():
        error_panel = Panel(
            "[red]❌ Vector store not found![/red]\n\n"
            "[cyan]Setup Required:[/cyan]\n"
            "1️⃣ Run [bold green]codebase-nav index[/bold green] first\n"
            "2️⃣ Then you can query your codebase!\n\n"
            "[dim]💡 The index command analyzes your code for AI queries[/dim]",
            title="[red]🔧 Setup Needed[/red]",
            border_style="red"
        )
        console.print(error_panel)
        sys.exit(1)
    
    # Load vector store and create agent
    try:
        console.print(Rule("[bold cyan]🔄 INITIALIZING AI AGENT[/bold cyan]", style="cyan"))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[cyan]Loading vector store and initializing AI...[/cyan]"),
            console=console,
        ) as progress:
            progress.add_task("Loading", total=None)
            
            vectorstore = create_vectorstore(str(vector_store_path))
            
            if vectorstore.get_document_count() == 0:
                error_panel = Panel(
                    "[red]❌ Vector store is empty![/red]\n\n"
                    "[dim]Run [bold green]codebase-nav index --force[/bold green] to re-populate it.[/dim]",
                    title="[red]🗄️ Empty Database[/red]",
                    border_style="red"
                )
                console.print(error_panel)
                sys.exit(1)
            
            agent = create_navigator_agent(
                vectorstore=vectorstore,
                repo_path=str(repo_path),
                model_name=model,
                tavily_api_key=os.getenv('TAVILY_API_KEY')
            )
        
        # Success message
        ready_panel = Panel(
            f"[bold green]🎉 AI Agent Ready![/bold green]\n\n"
            f"🤖 [cyan]Model:[/cyan] [bold]{model}[/bold]\n"
            f"📊 [cyan]Indexed Documents:[/cyan] [bold green]{vectorstore.get_document_count()}[/bold green]\n"
            f"🌐 [cyan]Web Search:[/cyan] {'[green]✅ Enabled[/green]' if os.getenv('TAVILY_API_KEY') else '[yellow]⚠️ Limited[/yellow]'}\n\n"
            f"🚀 [dim]Ready to analyze your codebase![/dim]",
            title="[green]✅ System Online[/green]",
            border_style="green"
        )
        console.print(ready_panel)
        console.print()
        
        if interactive:
            _interactive_mode(agent)
        elif question:
            _single_query(agent, question)
        else:
            console.print(Panel(
                "[yellow]⚠️ No question provided![/yellow]\n\n"
                "[cyan]Usage options:[/cyan]\n"
                "🔹 [bold]codebase-nav query --interactive[/bold] - Start interactive mode\n"
                "🔹 [bold]codebase-nav query \"Your question here\"[/bold] - Single question\n\n"
                "[dim]💡 Try: \"How does authentication work in this codebase?\"[/dim]",
                title="[yellow]🤔 What would you like to know?[/yellow]",
                border_style="yellow"
            ))
            
    except Exception as e:
        error_panel = Panel(
            f"[red]❌ Failed to initialize AI agent:[/red]\n\n"
            f"[dim]Error:[/dim] {str(e)}\n\n"
            "[cyan]Troubleshooting:[/cyan]\n"
            "🔹 Check your [bold]OPENAI_API_KEY[/bold] environment variable\n"
            "🔹 Ensure the vector store is properly indexed\n"
            "🔹 Try re-running the [bold green]index[/bold green] command",
            title="[red]🚨 Initialization Error[/red]",
            border_style="red"
        )
        console.print(error_panel)
        sys.exit(1)


def _interactive_mode(agent):
    """🎯 Interactive query mode with enhanced UI"""
    console.print(Rule("[bold green]🤖 INTERACTIVE MODE ACTIVATED[/bold green]", style="green"))
    
    welcome_panel = Panel(
        "[bold green]🎉 Welcome to Interactive Mode![/bold green]\n\n"
        "🔹 Ask me anything about your codebase\n"
        "🔹 I can analyze code patterns, suggest improvements, and more\n"
        "🔹 Type [bold red]'exit'[/bold red], [bold red]'quit'[/bold red], or [bold red]'q'[/bold red] to stop\n\n"
        "[dim]💡 Example questions:[/dim]\n"
        "[dim]  • \"How does authentication work in this codebase?\"[/dim]\n"
        "[dim]  • \"Show me the main database models\"[/dim]\n"
        "[dim]  • \"What are the key API endpoints?\"[/dim]",
        title="[bold blue]🎯 Interactive Assistant[/bold blue]",
        border_style="blue",
        padding=(1, 2)
    )
    console.print(welcome_panel)
    console.print()
    
    question_count = 1
    
    while True:
        try:
            # Stylized prompt
            console.print(f"[bold blue]❓ Question #{question_count}[/bold blue]")
            question = Prompt.ask("[cyan]What would you like to know?[/cyan]", console=console)
            
            if question.lower() in ['exit', 'quit', 'q']:
                goodbye_panel = Panel(
                    "[bold yellow]👋 Thanks for using Codebase Navigator![/bold yellow]\n\n"
                    "🎯 Hope I helped you understand your code better!\n"
                    "🚀 Run me again anytime for more analysis.",
                    title="[yellow]Goodbye![/yellow]",
                    border_style="yellow"
                )
                console.print(goodbye_panel)
                break
            
            if not question.strip():
                console.print("[yellow]⚠️ Please enter a question or type 'exit' to quit[/yellow]")
                continue
            
            # Processing with enhanced progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold cyan]🔍 Analyzing your codebase...[/bold cyan]"),
                console=console,
            ) as progress:
                progress.add_task("Processing", total=None)
                response = agent.query(question)
            
            console.print(Rule(f"[bold green]📋 ANSWER #{question_count}[/bold green]", style="green"))
            _display_response(response)
            console.print(Rule("[dim]Ready for next question[/dim]", style="dim"))
            console.print()
            
            question_count += 1
            
        except KeyboardInterrupt:
            console.print("\n[yellow]👋 Interrupted - Goodbye![/yellow]")
            break
        except Exception as e:
            error_panel = Panel(
                f"[red]❌ Oops! Something went wrong:[/red]\n\n{str(e)}\n\n"
                "[dim]Please try rephrasing your question or check your setup.[/dim]",
                title="[red]🚨 Error[/red]",
                border_style="red"
            )
            console.print(error_panel)


def _single_query(agent, question: str):
    """🎯 Handle a single query with enhanced styling"""
    console.print(Rule(f"[bold cyan]🔍 ANALYZING QUERY[/bold cyan]", style="cyan"))
    console.print(f"[dim]Question:[/dim] {question}")
    console.print()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]🧠 AI is thinking...[/bold cyan]"),
        console=console,
    ) as progress:
        progress.add_task("Processing", total=None)
        response = agent.query(question)
    
    console.print(Rule("[bold green]📋 ANALYSIS COMPLETE[/bold green]", style="green"))
    _display_response(response)


def _display_response(response: NavigatorResponse):
    """🎨 Display a beautifully formatted response"""
    # Main answer with enhanced styling
    answer_panel = Panel(
        Markdown(response.answer),
        title="[bold blue]🤖 AI Analysis[/bold blue]",
        border_style="blue",
        padding=(1, 2)
    )
    console.print(answer_panel)
    
    # Citations with tree structure
    if response.citations:
        console.print(f"\n[bold cyan]📖 Code References Found ({len(response.citations)})[/bold cyan]")
        
        citation_tree = Tree("📁 [bold]Source Files[/bold]")
        for i, citation in enumerate(response.citations, 1):
            file_branch = citation_tree.add(f"[green]{citation.path}[/green]")
            file_branch.add(f"[dim]Lines: {citation.start_line}-{citation.end_line}[/dim]")
        
        console.print(citation_tree)
        console.print()
    
    # External sources with enhanced formatting
    if response.retrieved_sources:
        console.print(f"[bold cyan]🌐 External Documentation ({len(response.retrieved_sources)})[/bold cyan]")
        
        sources_table = Table(show_header=False, box=None, padding=(0, 1))
        sources_table.add_column("", style="cyan")
        sources_table.add_column("", style="blue")
        
        for source in response.retrieved_sources:
            sources_table.add_row("🔗", f"[link={source.url}]{source.title}[/link]")
        
        console.print(sources_table)
        console.print()
    
    # Proposed patch with enhanced diff display
    if response.proposed_patch:
        status_color = {
            "DRAFT": "yellow",
            "READY": "green", 
            "FINAL": "green"
        }.get(response.proposed_patch.status, "white")
        
        patch_panel = Panel(
            Syntax(
                response.proposed_patch.diff,
                "diff",
                theme="monokai",
                line_numbers=True,
                word_wrap=True
            ),
            title=f"[{status_color}]🔧 Proposed Changes ({response.proposed_patch.status})[/{status_color}]",
            border_style=status_color
        )
        console.print(patch_panel)
    
    # Test suggestions with enhanced formatting
    if response.tests and response.tests.suggested:
        test_content = "[bold yellow]🧪 Recommended Testing Strategy[/bold yellow]\n\n"
        
        if response.tests.commands:
            test_content += "🏃 [cyan]Commands to run:[/cyan]\n"
            for cmd in response.tests.commands:
                test_content += f"  [green]${cmd}[/green]\n"
            test_content += "\n"
        
        if response.tests.new_tests:
            test_content += "📝 [cyan]New tests to create:[/cyan]\n"
            for test in response.tests.new_tests:
                test_content += f"  📄 [yellow]{test['path']}[/yellow]: {test['purpose']}\n"
        
        test_panel = Panel(
            test_content.strip(),
            title="[yellow]🧪 Testing Recommendations[/yellow]",
            border_style="yellow"
        )
        console.print(test_panel)
    
    # Risk assessment with enhanced styling
    if response.risk:
        risk_colors = {
            "low": "green",
            "medium": "yellow", 
            "high": "red"
        }
        risk_color = risk_colors.get(response.risk.level, "white")
        
        risk_icons = {
            "low": "✅",
            "medium": "⚠️",
            "high": "🚨"
        }
        risk_icon = risk_icons.get(response.risk.level, "⚡")
        
        risk_content = f"[bold {risk_color}]{risk_icon} Risk Level: {response.risk.level.upper()}[/bold {risk_color}]\n\n"
        
        if response.risk.concerns:
            risk_content += "[cyan]🎯 Key Concerns:[/cyan]\n"
            for concern in response.risk.concerns:
                risk_content += f"  • {concern}\n"
            risk_content += "\n"
        
        risk_content += f"[cyan]🔄 Rollback Plan:[/cyan]\n  {response.risk.roll_back}"
        
        risk_panel = Panel(
            risk_content,
            title=f"[{risk_color}]{risk_icon} Risk Assessment[/{risk_color}]",
            border_style=risk_color
        )
        console.print(risk_panel)


@cli.command()
@click.option('--file-path', '-f', help='Specific file to analyze')
@click.option('--error-message', '-e', help='Error message to diagnose')
@click.option('--stack-trace', '-s', help='Stack trace file path')
@click.pass_context
def diagnose(ctx, file_path: Optional[str], error_message: Optional[str], stack_trace: Optional[str]):
    """Diagnose issues and suggest fixes"""
    if not error_message:
        console.print("[red]Error message is required for diagnosis[/red]")
        sys.exit(1)
    
    repo_path = ctx.obj['repo_path']
    vector_store_path = ctx.obj['vector_store_path']
    
    # Load vector store and create agent
    try:
        vectorstore = create_vectorstore(str(vector_store_path))
        agent = create_navigator_agent(
            vectorstore=vectorstore,
            repo_path=str(repo_path),
            tavily_api_key=os.getenv('TAVILY_API_KEY')
        )
        
        # Read stack trace if provided
        stack_trace_content = None
        if stack_trace and Path(stack_trace).exists():
            with open(stack_trace, 'r') as f:
                stack_trace_content = f.read()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("Diagnosing..."),
            console=console,
        ) as progress:
            progress.add_task("Processing", total=None)
            response = agent.diagnose_issue(
                error_message=error_message,
                file_path=file_path,
                stack_trace=stack_trace_content
            )
        
        _display_response(response)
        
    except Exception as e:
        console.print(f"[red]Error during diagnosis: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('file_path')
@click.option('--refactor-type', '-t', default='general', help='Type of refactoring (performance, readability, security)')
@click.option('--concerns', '-c', multiple=True, help='Specific concerns to address')
@click.pass_context
def refactor(ctx, file_path: str, refactor_type: str, concerns: tuple):
    """Suggest refactoring improvements for a file"""
    repo_path = ctx.obj['repo_path']
    vector_store_path = ctx.obj['vector_store_path']
    
    # Validate file exists
    full_path = repo_path / file_path
    if not full_path.exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        sys.exit(1)
    
    try:
        vectorstore = create_vectorstore(str(vector_store_path))
        agent = create_navigator_agent(
            vectorstore=vectorstore,
            repo_path=str(repo_path),
            tavily_api_key=os.getenv('TAVILY_API_KEY')
        )
        
        with Progress(
            SpinnerColumn(),
            TextColumn("Analyzing code..."),
            console=console,
        ) as progress:
            progress.add_task("Processing", total=None)
            response = agent.suggest_refactor(
                file_path=file_path,
                refactor_type=refactor_type,
                specific_concerns=list(concerns) if concerns else None
            )
        
        _display_response(response)
        
    except Exception as e:
        console.print(f"[red]Error during refactoring analysis: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context  
def info(ctx):
    """📊 Display comprehensive repository information"""
    repo_path = ctx.obj['repo_path']
    vector_store_path = ctx.obj['vector_store_path']
    
    console.print(Rule("[bold blue]📊 REPOSITORY ANALYSIS[/bold blue]", style="blue"))
    
    # Analyze repository
    analyzer = RepositoryAnalyzer(str(repo_path))
    repo_info = analyzer.get_project_info()
    
    # Main repository panel
    repo_panel = Panel(
        f"[bold cyan]📁 {repo_info['name']}[/bold cyan]\n"
        f"[dim]📍 Location:[/dim] {repo_info['path']}\n\n"
        f"[green]📈 Total Files:[/green] [bold]{repo_info['structure']['total_files']}[/bold]\n"
        f"[blue]🔧 Git Repo:[/blue] {'[green]✅ Yes[/green]' if repo_info['is_git_repo'] else '[red]❌ No[/red]'}",
        title="[bold blue]🏗️ Project Overview[/bold blue]",
        border_style="blue",
        padding=(1, 2)
    )
    console.print(repo_panel)
    
    # Languages breakdown with visual bars
    if repo_info['languages']:
        console.print(f"\n[bold magenta]💻 Programming Languages ({len(repo_info['languages'])})[/bold magenta]")
        
        lang_table = Table(show_header=True, header_style="bold magenta")
        lang_table.add_column("🏷️ Language", style="cyan", min_width=12)
        lang_table.add_column("📁 Files", style="green", justify="right", min_width=8)
        lang_table.add_column("📊 Distribution", style="yellow", min_width=20)
        
        total_files = sum(repo_info['languages'].values())
        for lang, count in sorted(repo_info['languages'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_files) * 100
            bar_length = int(percentage / 5)  # Scale bar to reasonable size
            bar = "█" * bar_length + "▒" * (20 - bar_length)
            
            lang_table.add_row(
                f"[yellow]{lang}[/yellow]",
                f"[bold green]{count}[/bold green]", 
                f"{bar} [dim]{percentage:.1f}%[/dim]"
            )
        
        console.print(lang_table)
    
    # Frameworks detection
    if repo_info['frameworks']:
        console.print(f"\n[bold green]🚀 Detected Frameworks ({len(repo_info['frameworks'])})[/bold green]")
        framework_columns = []
        for fw in repo_info['frameworks']:
            framework_columns.append(f"[blue]🔧 {fw}[/blue]")
        console.print(Columns(framework_columns, equal=True, expand=True))
    
    # Vector store status with enhanced styling
    console.print(f"\n[bold cyan]🗄️ Vector Store Status[/bold cyan]")
    
    if vector_store_path.exists():
        try:
            vectorstore = create_vectorstore(str(vector_store_path))
            doc_count = vectorstore.get_document_count()
            
            if doc_count > 0:
                status_panel = Panel(
                    f"[bold green]✅ READY FOR QUERIES[/bold green]\n\n"
                    f"📊 [cyan]Documents Indexed:[/cyan] [bold green]{doc_count}[/bold green]\n"
                    f"📍 [cyan]Storage Path:[/cyan] {vector_store_path}\n\n"
                    f"🚀 [dim]You can now use the 'query' command![/dim]",
                    title="[green]🎯 Vector Store Active[/green]",
                    border_style="green"
                )
                console.print(status_panel)
                
                # Show indexed language distribution
                lang_stats = vectorstore.get_language_stats()
                if lang_stats:
                    console.print(f"\n[bold blue]📈 Indexed Content Distribution[/bold blue]")
                    
                    stats_table = Table(show_header=True, header_style="bold blue")
                    stats_table.add_column("🏷️ Language", style="cyan")
                    stats_table.add_column("🧩 Chunks", style="green", justify="right")
                    stats_table.add_column("📊 Percentage", style="yellow", justify="right")
                    
                    total_chunks = sum(lang_stats.values())
                    for lang, count in sorted(lang_stats.items(), key=lambda x: x[1], reverse=True):
                        percentage = (count / total_chunks) * 100
                        stats_table.add_row(
                            f"[yellow]{lang}[/yellow]",
                            f"[bold green]{count}[/bold green]",
                            f"[dim]{percentage:.1f}%[/dim]"
                        )
                    
                    console.print(stats_table)
            else:
                warning_panel = Panel(
                    "[yellow]⚠️ Vector store exists but is empty[/yellow]\n\n"
                    "[dim]Run the 'index' command to populate it with your codebase.[/dim]",
                    title="[yellow]🔄 Needs Indexing[/yellow]",
                    border_style="yellow"
                )
                console.print(warning_panel)
                
        except Exception as e:
            error_panel = Panel(
                f"[red]❌ Vector store found but not accessible[/red]\n\n"
                f"[dim]Error:[/dim] {str(e)}\n\n"
                "[dim]You may need to re-index the repository.[/dim]",
                title="[red]🚨 Storage Error[/red]",
                border_style="red"
            )
            console.print(error_panel)
    else:
        setup_panel = Panel(
            "[red]❌ NO VECTOR STORE FOUND[/red]\n\n"
            "[cyan]Next steps:[/cyan]\n"
            "1️⃣ Run [bold green]codebase-nav index[/bold green] to analyze your code\n"
            "2️⃣ Then use [bold blue]codebase-nav query[/bold blue] to ask questions\n\n"
            "[dim]💡 This will enable AI-powered code analysis![/dim]",
            title="[red]🔧 Setup Required[/red]",
            border_style="red"
        )
        console.print(setup_panel)


@cli.command()
@click.argument('repo_url')
@click.option('--query', '-q', help='Query the repository after analysis')
@click.option('--method', '-m', default='download', type=click.Choice(['download', 'clone']), 
              help='Download method: download (ZIP, faster) or clone (full repo with git history)')
def github(repo_url, query, method):
    """🐙 Analyze a GitHub repository with AI-powered insights."""
    show_banner()
    
    console = Console()
    
    with console.status("[bold green]🔍 Analyzing GitHub repository...", spinner="dots"):
        try:
            # Parse and validate URL
            analyzer = GitHubAnalyzer()
            repo_owner, repo_name = analyzer.parse_github_url(repo_url)
            
            # Create analysis session
            session = create_github_session(repo_url, method=method)
            
            # Success banner
            panel = Panel(
                f"[bold green]✅ Successfully analyzed repository![/bold green]\n\n"
                f"[bold]Repository:[/bold] [cyan]{repo_owner}/{repo_name}[/cyan]\n"
                f"[bold]Method:[/bold] [yellow]{method}[/yellow]\n"
                f"[bold]Status:[/bold] [green]Ready for queries[/green]",
                title="[bold blue]🐙 GitHub Analysis Complete",
                border_style="green"
            )
            console.print("\n")
            console.print(panel)
            
            # Handle query if provided
            if query:
                console.print(f"\n[bold yellow]❓ Query:[/bold yellow] [white]{query}[/white]")
                with console.status("[bold cyan]🤖 Processing query...", spinner="dots"):
                    response = session.query(query)
                
                # Display response
                _display_github_response(response)
            else:
                # Interactive mode
                _github_interactive_mode(session, repo_owner, repo_name)
                
        except Exception as e:
            error_panel = Panel(
                f"[bold red]❌ Error analyzing repository:[/bold red]\n\n"
                f"[red]{str(e)}[/red]",
                title="[bold red]⚠️ Analysis Failed",
                border_style="red"
            )
            console.print("\n")
            console.print(error_panel)
            raise click.ClickException(f"Failed to analyze repository: {e}")


@cli.command()
@click.argument('search_term')
@click.option('--language', '-l', help='Filter by programming language')
@click.option('--stars', '-s', help='Minimum number of stars (e.g., ">100")')
@click.option('--limit', default=10, help='Number of results to show (default: 10)')
def search_github(search_term, language, stars, limit):
    """🔍 Search GitHub repositories and analyze them."""
    show_banner()
    
    console = Console()
    
    try:
        analyzer = GitHubAnalyzer()
        
        # Build search query
        query_parts = [search_term]
        if language:
            query_parts.append(f"language:{language}")
        if stars:
            query_parts.append(f"stars:{stars}")
        
        search_query = " ".join(query_parts)
        
        with console.status(f"[bold green]🔍 Searching GitHub for: {search_query}", spinner="dots"):
            repos = analyzer.search_repositories(search_query, limit=limit)
        
        if not repos:
            console.print("\n[bold yellow]No repositories found.[/bold yellow]")
            return
        
        # Display results
        console.print(f"\n[bold green]Found {len(repos)} repositories:[/bold green]\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Repository", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Stars", justify="right", style="yellow")
        table.add_column("Language", style="green")
        
        for repo in repos:
            table.add_row(
                repo['full_name'],
                repo.get('description', 'No description')[:80] + ('...' if len(repo.get('description', '')) > 80 else ''),
                str(repo.get('stargazers_count', 0)),
                repo.get('language', 'Unknown')
            )
        
        console.print(table)
        
        # Offer to analyze a repository
        if click.confirm("\nWould you like to analyze one of these repositories?"):
            repo_choice = Prompt.ask(
                "Enter the repository name (owner/repo)",
                choices=[repo['full_name'] for repo in repos],
                show_choices=False
            )
            
            # Analyze the chosen repository
            repo_url = f"https://github.com/{repo_choice}"
            ctx = click.get_current_context()
            ctx.invoke(github, repo_url=repo_url)
            
    except Exception as e:
        error_panel = Panel(
            f"[bold red]❌ Search failed:[/bold red]\n\n[red]{str(e)}[/red]",
            title="[bold red]⚠️ Search Error",
            border_style="red"
        )
        console.print("\n")
        console.print(error_panel)


def _github_interactive_mode(session, repo_owner, repo_name):
    """Interactive mode for GitHub repository queries."""
    console = Console()
    
    # Interactive mode banner
    panel = Panel(
        f"[bold cyan]🚀 Interactive GitHub Analysis Mode[/bold cyan]\n\n"
        f"[bold]Repository:[/bold] [cyan]{repo_owner}/{repo_name}[/cyan]\n"
        f"[dim]• Ask questions about the code structure, patterns, or implementation\n"
        f"• Type 'exit', 'quit', or press Ctrl+C to stop\n"
        f"• Use 'help' for example queries[/dim]",
        title="[bold green]🤖 AI Assistant Ready",
        border_style="cyan"
    )
    console.print("\n")
    console.print(panel)
    
    try:
        while True:
            # Get user input
            query = Prompt.ask(
                "\n[bold cyan]🐙 GitHub Query[/bold cyan]",
                default="",
                show_default=False
            )
            
            if not query or query.lower() in ['exit', 'quit', 'q']:
                console.print("\n[bold yellow]👋 Goodbye![/bold yellow]")
                break
                
            if query.lower() == 'help':
                _show_github_help()
                continue
            
            # Process query
            with console.status("[bold cyan]🤖 Analyzing repository...", spinner="dots"):
                response = session.query(query)
            
            # Display response
            _display_github_response(response)
            
    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]👋 Goodbye![/bold yellow]")


def _display_github_response(response):
    """Display GitHub analysis response with rich formatting."""
    console = Console()
    
    # Create response panel
    panel = Panel(
        f"[bold white]{response}[/bold white]",
        title="[bold green]🤖 AI Analysis",
        border_style="green",
        padding=(1, 2)
    )
    
    console.print("\n")
    console.print(panel)


def _show_github_help():
    """Show example GitHub queries."""
    console = Console()
    
    examples = [
        ("📁 Repository Structure", "What is the overall structure of this repository?"),
        ("🔧 Main Functionality", "What does this project do and how does it work?"),
        ("📝 Key Files", "What are the most important files in this codebase?"),
        ("🏗️ Architecture", "Explain the architecture and design patterns used"),
        ("🚀 Getting Started", "How do I set up and run this project?"),
        ("🔍 Specific Features", "How does [specific feature] work in this code?"),
        ("📊 Dependencies", "What are the main dependencies and technologies used?"),
        ("🧪 Testing", "How is testing implemented in this project?"),
    ]
    
    help_text = "\n".join([
        f"[bold cyan]• {title}:[/bold cyan] [white]{example}[/white]"
        for title, example in examples
    ])
    
    panel = Panel(
        help_text,
        title="[bold yellow]💡 Example Queries",
        border_style="yellow"
    )
    
    console.print("\n")
    console.print(panel)


def main():
    """Main CLI entry point"""
    cli()


if __name__ == '__main__':
    main()
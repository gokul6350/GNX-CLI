from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.markdown import Markdown

console = Console()

GNX_COLORS = ["#00FFFF", "#00E5FF", "#00CCFF", "#00B2FF", "#0099FF", "#0080FF"]

BANNER_ART = """
 ██████╗ ███╗   ██╗██╗  ██╗     ██████╗██╗     ██╗             
██╔════╝ ████╗  ██║╚██╗██╔╝    ██╔════╝██║     ██║             
██║  ███╗██╔██╗ ██║ ╚███╔╝     ██║     ██║     ██║             
██║   ██║██║╚██╗██║ ██╔██╗     ██║     ██║     ██║             
╚██████╔╝██║ ╚████║██╔╝ ██╗    ╚██████╗███████╗██║             
 ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝     ╚═════╝╚══════╝╚═╝             
"""

def show_banner():
    # Create a gradient effect text
    styled_text = Text()
    lines = BANNER_ART.split("\n")
    for i, line in enumerate(lines):
        if not line.strip():
            styled_text.append(line + "\n")
            continue
        color_idx = i % len(GNX_COLORS)
        styled_text.append(line + "\n", style=GNX_COLORS[color_idx])

    panel = Panel(
        Align.center(styled_text),
        border_style="bold blue",
        title="[bold white]GNX ENGINE[/bold white]",
        subtitle="[dim]Powered by Llama 4 Scout[/dim]"
    )
    console.print(panel)

def print_agent_response(text: str):
    """Print agent response with markdown rendering."""
    md = Markdown(text)
    console.print(Panel(md, title="[bold green]GNX[/bold green]", border_style="green"))

def print_tool_call(tool_name: str, args: str):
    """Print a tool call in real-time."""
    console.print(f"  [bold cyan]► {tool_name}[/bold cyan]([dim]{args}[/dim])")

def print_tool_result(result: str):
    """Print tool result in real-time."""
    # Truncate long results for display
    lines = result.split('\n')
    if len(lines) > 10:
        display_result = '\n'.join(lines[:10]) + f"\n    [dim]... ({len(lines) - 10} more lines)[/dim]"
    else:
        display_result = result
    
    for line in display_result.split('\n'):
        console.print(f"    [green]{line}[/green]")

def print_error(text: str):
    console.print(f"[bold red]Error:[/bold red] {text}")

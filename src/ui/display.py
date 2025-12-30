from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

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
        subtitle="[dim]Powered by gemma-3-27b-it[/dim]"
    )
    console.print(panel)

def print_agent_response(text: str):
    console.print(Panel(text, title="[bold green]GNX[/bold green]", border_style="green"))

def print_error(text: str):
    console.print(f"[bold red]Error:[/bold red] {text}")

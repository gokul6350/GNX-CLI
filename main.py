import os
import sys
from rich.prompt import Prompt
from src.gnx_engine.engine import GNXEngine
from src.ui.display import show_banner, print_agent_response, print_error, console

def main():
    show_banner()
    
    # Ensure API Key
    # Using the key provided in the prompt for demonstration
    if "GOOGLE_API_KEY" not in os.environ:
       os.environ["GOOGLE_API_KEY"] = "AIzaSyAZc84jW2KbLE2qFCas80BtaMftNA_18q8"

    try:
        engine = GNXEngine()
        console.print("[bold green]System Initialized. GNX Engine Online.[/bold green]")
    except Exception as e:
        print_error(f"Failed to initialize engine: {e}")
        return

    while True:
        try:
            user_input = Prompt.ask("[bold blue]GNX[/bold blue]")
            
            if not user_input.strip():
                continue
                
            if user_input.lower() in ["/exit", "exit", "/quit"]:
                console.print("[yellow]Shutting down...[/yellow]")
                break
                
            if user_input.startswith("/"):
                handle_command(user_input, engine)
                continue

            with console.status("[bold cyan]Thinking...[/bold cyan]", spinner="dots"):
                response = engine.run(user_input)
            
            print_agent_response(response)
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type /exit to quit.[/yellow]")
        except EOFError:
            break
        except Exception as e:
            print_error(str(e))

def handle_command(cmd_str, engine):
    cmd = cmd_str.split()[0].lower()
    if cmd == "/tools":
        console.print("[bold]Available Tools:[/bold]")
        from rich.table import Table
        table = Table(title="GNX Toolkit")
        table.add_column("Tool Name", style="cyan")
        table.add_column("Description", style="white")
        
        for tool in engine.tools:
            # Simple description truncation
            desc = tool.description.split("\n")[0]
            table.add_row(tool.name, desc)
        
        console.print(table)
    elif cmd == "/clear":
        os.system('cls' if os.name == 'nt' else 'clear')
        show_banner()
    else:
        console.print(f"[red]Unknown command: {cmd}[/red]")

if __name__ == "__main__":
    main()

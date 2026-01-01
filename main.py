import os
import sys
import json
import subprocess
from rich.prompt import Prompt
from src.gnx_engine.engine import GNXEngine
from src.ui.display import show_banner, print_agent_response, print_error, console
from src.utils.token_counter import create_token_report, count_messages_tokens

CHATS_DIR = "saved_chats"

def main():
    show_banner()
    
    # Ensure API Key
    if "GOOGLE_API_KEY" not in os.environ:
       os.environ["GOOGLE_API_KEY"] = "AIzaSyAZc84jW2KbLE2qFCas80BtaMftNA_18q8"

    try:
        engine = GNXEngine()
        console.print("[bold green]System Initialized. GNX Engine Online.[/bold green]")
        console.print("[cyan]✓ Computer Use & Mobile Use tools enabled[/cyan]")
            
    except Exception as e:
        print_error(f"Failed to initialize engine: {e}")
        return

    while True:
        try:
            user_input = Prompt.ask("[bold blue]GNX[/bold blue]")
            
            if not user_input.strip():
                continue
                
            if user_input.lower() in ["/exit", "exit", "/quit","/q","/E"]:
                console.print("[yellow]Shutting down...[/yellow]")
                break
            
            # Handle ! prefix for direct shell commands
            if user_input.startswith("!"):
                run_shell_command(user_input[1:].strip())
                continue
                
            if user_input.startswith("/"):
                handle_command(user_input, engine)
                continue

            # Run with live tool output
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
    elif cmd == "/help":
        from rich.table import Table
        table = Table(title="GNX Commands", show_header=True)
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="white")
        table.add_row("/help", "Show this help message")
        table.add_row("/tools", "List all available tools")
        table.add_row("/clear", "Clear the screen")
        table.add_row("/history", "Show chat history length")
        table.add_row("/tokens", "Show token usage & estimated costs")
        table.add_row("/reset", "Reset chat history")
        table.add_row("/save <name>", "Save current chat with a name")
        table.add_row("/resume <name>", "Resume a saved chat")
        table.add_row("/chats", "List all saved chats")
        table.add_row("!<cmd>", "Run shell command (e.g., !dir)")
        table.add_row("/exit", "Exit the CLI")
        console.print(table)
    elif cmd == "/history":
        count = len(engine.chat_history)
        console.print(f"[cyan]Chat history: {count} messages[/cyan]")
    elif cmd == "/reset":
        engine.chat_history = []
        console.print("[green]Chat history cleared.[/green]")
    elif cmd == "/save":
        # /save chatname
        parts = cmd_str.split(maxsplit=1)
        if len(parts) < 2:
            console.print("[red]Usage: /save <chatname>[/red]")
            return
        chat_name = parts[1].strip().replace(" ", "_")
        save_chat(engine, chat_name)
    elif cmd == "/resume":
        # /resume chatname
        parts = cmd_str.split(maxsplit=1)
        if len(parts) < 2:
            # List available chats
            list_saved_chats()
            return
        chat_name = parts[1].strip().replace(" ", "_")
        resume_chat(engine, chat_name)
    elif cmd == "/chats":
        list_saved_chats()
    elif cmd == "/tokens":
        show_token_stats(engine)
    else:
        console.print(f"[red]Unknown command: {cmd}[/red]")
        console.print("[dim]Type /help for available commands[/dim]")


def run_shell_command(cmd: str):
    """Execute a shell command directly."""
    if not cmd:
        console.print("[red]Usage: !<command>[/red]")
        return
    
    console.print(f"[dim]$ {cmd}[/dim]")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(f"[red]{result.stderr}[/red]")
        if result.returncode != 0:
            console.print(f"[dim]Exit code: {result.returncode}[/dim]")
    except Exception as e:
        console.print(f"[red]Error running command: {e}[/red]")


def save_chat(engine, chat_name: str):
    """Save current chat history to a file."""
    os.makedirs(CHATS_DIR, exist_ok=True)
    filepath = os.path.join(CHATS_DIR, f"{chat_name}.json")
    
    # Serialize chat history
    history_data = []
    for msg in engine.chat_history:
        history_data.append({
            "type": type(msg).__name__,
            "content": msg.content
        })
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(history_data, f, indent=2)
    
    console.print(f"[green]Chat saved to: {filepath}[/green]")


def resume_chat(engine, chat_name: str):
    """Resume a previously saved chat."""
    filepath = os.path.join(CHATS_DIR, f"{chat_name}.json")
    
    if not os.path.exists(filepath):
        console.print(f"[red]Chat not found: {chat_name}[/red]")
        list_saved_chats()
        return
    
    from langchain_core.messages import HumanMessage, AIMessage
    
    with open(filepath, 'r', encoding='utf-8') as f:
        history_data = json.load(f)
    
    # Reconstruct messages
    engine.chat_history = []
    for msg_data in history_data:
        if msg_data["type"] == "HumanMessage":
            engine.chat_history.append(HumanMessage(content=msg_data["content"]))
        elif msg_data["type"] == "AIMessage":
            engine.chat_history.append(AIMessage(content=msg_data["content"]))
    
    console.print(f"[green]Resumed chat: {chat_name} ({len(engine.chat_history)} messages)[/green]")


def list_saved_chats():
    """List all saved chats."""
    if not os.path.exists(CHATS_DIR):
        console.print("[dim]No saved chats found.[/dim]")
        return
    
    chats = [f.replace('.json', '') for f in os.listdir(CHATS_DIR) if f.endswith('.json')]
    
    if not chats:
        console.print("[dim]No saved chats found.[/dim]")
        return
    
    console.print("[bold]Saved Chats:[/bold]")
    for chat in chats:
        console.print(f"  [cyan]• {chat}[/cyan]")


def show_token_stats(engine):
    """Show token usage statistics for current session."""
    if not engine.chat_history:
        console.print("[yellow]No messages in chat history.[/yellow]")
        return
    
    token_count = count_messages_tokens(engine.chat_history)
    report = create_token_report(engine.chat_history, "Current Session")
    console.print(report)

if __name__ == "__main__":
    main()

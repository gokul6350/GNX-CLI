import os
import sys
import json
import subprocess
from dotenv import load_dotenv
from rich.prompt import Prompt
from src.gnx_engine.engine import GNXEngine, PROVIDERS
from src.ui.display import show_banner, print_agent_response, print_error, console
from src.utils.token_counter import create_token_report, count_messages_tokens

# Load environment variables from .env file
load_dotenv()

CHATS_DIR = "saved_chats"

def main():
    show_banner()
    
    # API keys are loaded from .env file via load_dotenv()
    try:
        engine = GNXEngine()
        config = engine.get_current_config()
        console.print("[bold green]System Initialized. GNX Engine Online.[/bold green]")
        console.print(f"[cyan]✓ Provider: {config['provider']} | Model: {config['model']}[/cyan]")
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
    parts = cmd_str.split()
    cmd = parts[0].lower()
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
    elif cmd == "/model":
        handle_model_command(parts, engine)
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
        table.add_row("/model", "Show current provider and model")
        table.add_row("/model provider groq", "Switch to Groq provider")
        table.add_row("/model provider gemini", "Switch to Gemini provider")
        table.add_row("/model list [provider]", "List available models")
        table.add_row("/model set <model_name>", "Set specific model")
        table.add_row("/clear", "Clear the screen")
        table.add_row("/history", "Show chat history length")
        table.add_row("/tokens", "Show token usage & estimated costs")
        table.add_row("/reset", "Reset chat history")
        table.add_row("/save <name>", "Save current chat with a name")
        table.add_row("/resume <name>", "Resume a saved chat")
        table.add_row("/chats", "List all saved chats")
        table.add_row("/memory", "Show memory OS stats and analytics")
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
    elif cmd == "/memory":
        # Show memory stats and analytics
        stats = engine.memory_os.get_stats()
        console.print("[bold]Memory OS Stats:[/bold]")
        console.print(f"  [cyan]Hot Tier:[/cyan] {stats['hot_size']} items")
        console.print(f"  [yellow]Warm Tier:[/yellow] {stats['warm_size']} memories")
        console.print(f"  [blue]Cold Tier:[/blue] {stats['cold_size']} archived")
        console.print(f"  [dim]Total:[/dim] {stats['total_memories']} long-term memories")
        
        # Show analytics if available
        if engine.memory_os.analytics:
            console.print("")
            engine.memory_os.print_analytics()
    else:
        console.print(f"[red]Unknown command: {cmd}[/red]")
        console.print("[dim]Type /help for available commands[/dim]")


def handle_model_command(parts, engine):
    """Handle /model subcommands for provider/model switching."""
    from rich.table import Table
    
    if len(parts) == 1:
        # Just /model - show current config
        config = engine.get_current_config()
        console.print(f"[bold]Current Configuration:[/bold]")
        console.print(f"  [cyan]Provider:[/cyan] {config['provider']}")
        console.print(f"  [cyan]Model:[/cyan] {config['model']}")
        console.print(f"  [dim]Available providers: {', '.join(config['available_providers'])}[/dim]")
        return
    
    subcmd = parts[1].lower()
    
    if subcmd == "provider":
        if len(parts) < 3:
            console.print("[red]Usage: /model provider <groq|gemini>[/red]")
            console.print(f"[dim]Available providers: {', '.join(PROVIDERS.keys())}[/dim]")
            return
        
        provider = parts[2].lower()
        model_name = parts[3] if len(parts) > 3 else None
        
        success, message = engine.switch_provider(provider, model_name)
        if success:
            console.print(f"[green]✓ {message}[/green]")
        else:
            console.print(f"[red]✗ {message}[/red]")
    
    elif subcmd == "list":
        # List available models for a provider
        provider = parts[2].lower() if len(parts) > 2 else engine.provider
        
        if provider not in PROVIDERS:
            console.print(f"[red]Unknown provider: {provider}[/red]")
            return
        
        models = engine.list_models(provider)
        table = Table(title=f"Available Models for {provider.upper()}")
        table.add_column("Model Name", style="cyan")
        table.add_column("Status", style="green")
        
        current_model = engine.model_name if provider == engine.provider else None
        for model in models:
            status = "← current" if model == current_model else ""
            table.add_row(model, status)
        
        console.print(table)
    
    elif subcmd == "set":
        if len(parts) < 3:
            console.print("[red]Usage: /model set <model_name>[/red]")
            console.print("[dim]Use '/model list' to see available models[/dim]")
            return
        
        model_name = parts[2]
        success, message = engine.switch_provider(engine.provider, model_name)
        if success:
            console.print(f"[green]✓ Model set to: {model_name}[/green]")
        else:
            console.print(f"[red]✗ {message}[/red]")
    
    else:
        console.print(f"[red]Unknown subcommand: {subcmd}[/red]")
        console.print("[dim]Usage: /model [provider <name>|list [provider]|set <model>][/dim]")


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

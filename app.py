import asyncio
import json
import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, FloatPrompt, IntPrompt, Confirm
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich import box

console = Console()

# Settings file
SETTINGS_FILE = Path(__file__).parent / "settings.json"

# Default settings
DEFAULT_SETTINGS = {
    "rpc_url": "https://mainnet.base.org",
    "private_key": "",
    "dry_run": True,
    "pair_index": 1,
    "pair_name": "BTC/USD",
    "position_size": 10.0,
    "leverage": 75,
    "take_profit_pnl": 0.80,
    "stop_loss_pnl": 0.80,
    "entry_offset_min": 0.25,
    "entry_offset_max": 1.0,
    "reposition_threshold": 1.0,
    "reposition_random": 0.2,
    "check_interval_min": 10,
    "check_interval_max": 30,
    "trading_start_hour": 8,
    "trading_end_hour": 24,
    "trading_hours_variance": 15,
}


def load_settings() -> dict:
    """Load settings from file or return defaults."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                saved = json.load(f)
                # Merge with defaults (in case new settings added)
                return {**DEFAULT_SETTINGS, **saved}
        except:
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict):
    """Save settings to file."""
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


def apply_settings_to_config(settings: dict):
    """Apply settings to config module."""
    import config
    config.RPC_URL = settings["rpc_url"]
    config.PRIVATE_KEY = settings["private_key"]
    config.DRY_RUN = settings["dry_run"]
    config.PAIR_INDEX = settings["pair_index"]
    config.PAIR_NAME = settings["pair_name"]
    config.POSITION_SIZE_USDC = settings["position_size"]
    config.LEVERAGE = settings["leverage"]
    config.TAKE_PROFIT_PNL = settings["take_profit_pnl"]
    config.STOP_LOSS_PNL = settings["stop_loss_pnl"]
    config.ENTRY_OFFSET_MIN = settings["entry_offset_min"] / 100
    config.ENTRY_OFFSET_MAX = settings["entry_offset_max"] / 100
    config.REPOSITION_THRESHOLD_PCT = settings["reposition_threshold"] / 100
    config.REPOSITION_RANDOM = settings["reposition_random"] / 100
    config.CHECK_INTERVAL_MIN = settings["check_interval_min"]
    config.CHECK_INTERVAL_MAX = settings["check_interval_max"]
    config.TRADING_START_HOUR = settings["trading_start_hour"]
    config.TRADING_END_HOUR = settings["trading_end_hour"]
    config.TRADING_HOURS_VARIANCE = settings["trading_hours_variance"]


def show_header():
    """Show app header."""
    console.clear()
    header = Text()
    header.append("  DELTA-NEUTRAL BOT  ", style="bold white on blue")
    header.append(" v3.0 ", style="bold black on yellow")
    console.print(Panel(header, box=box.DOUBLE))


def show_settings_table(settings: dict):
    """Display current settings in a nice table."""
    table = Table(title="Current Settings", box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Parameter", style="white", width=25)
    table.add_column("Value", style="green", width=20)
    table.add_column("Description", style="dim", width=35)

    # Mode
    mode = "[green]DRY RUN[/green]" if settings["dry_run"] else "[red]LIVE[/red]"
    table.add_row("Mode", mode, "Simulation or real trading")

    # Trading pair
    table.add_row("Pair", settings["pair_name"], f"Index: {settings['pair_index']}")

    # Position
    table.add_row("Position Size", f"${settings['position_size']:.1f} USDC", "Collateral per position")
    table.add_row("Leverage", f"{settings['leverage']}x", "1-150")

    # TP/SL
    table.add_row("Take Profit", f"{settings['take_profit_pnl']*100:.0f}%", "PnL to close with profit")
    table.add_row("Stop Loss", f"{settings['stop_loss_pnl']*100:.0f}%", "PnL to close with loss")

    # Entry
    table.add_row("Entry Offset", f"{settings['entry_offset_min']}% - {settings['entry_offset_max']}%", "Distance from current price")

    # Reposition
    table.add_row("Reposition", f"{settings['reposition_threshold']}% (±{settings['reposition_random']}%)", "When to cancel and replace")

    # Intervals
    table.add_row("Check Interval", f"{settings['check_interval_min']}-{settings['check_interval_max']}s", "Price check frequency")

    # Hours
    end_h = settings['trading_end_hour'] % 24
    table.add_row("Trading Hours", f"{settings['trading_start_hour']:02d}:00 - {end_h:02d}:00 MSK", f"±{settings['trading_hours_variance']} min variance")

    # Wallet
    pk = settings["private_key"]
    if pk:
        wallet_display = f"{pk[:6]}...{pk[-4:]}" if len(pk) > 10 else "***"
    else:
        wallet_display = "[red]NOT SET[/red]"
    table.add_row("Wallet", wallet_display, "Private key")

    console.print(table)


def show_menu() -> str:
    """Show main menu and get choice."""
    console.print()
    menu = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    menu.add_column(style="bold cyan", width=5)
    menu.add_column(style="white")

    menu.add_row("[1]", "Edit Position Settings")
    menu.add_row("[2]", "Edit Entry/Exit Settings")
    menu.add_row("[3]", "Edit Trading Hours")
    menu.add_row("[4]", "Edit Wallet/RPC")
    menu.add_row("[5]", "Toggle DRY RUN / LIVE mode")
    menu.add_row("[S]", "START BOT")
    menu.add_row("[Q]", "Quit")

    console.print(Panel(menu, title="Menu", box=box.ROUNDED))

    return Prompt.ask("Choose", choices=["1", "2", "3", "4", "5", "s", "S", "q", "Q"], default="s")


def edit_position_settings(settings: dict):
    """Edit position-related settings."""
    show_header()
    console.print(Panel("[bold]Position Settings[/bold]", style="cyan"))

    settings["position_size"] = FloatPrompt.ask(
        "Position Size (USDC)",
        default=settings["position_size"]
    )

    settings["leverage"] = IntPrompt.ask(
        "Leverage (1-150)",
        default=settings["leverage"]
    )
    if settings["leverage"] < 1:
        settings["leverage"] = 1
    elif settings["leverage"] > 150:
        settings["leverage"] = 150

    settings["take_profit_pnl"] = FloatPrompt.ask(
        "Take Profit PnL % (e.g. 80 for 80%)",
        default=settings["take_profit_pnl"] * 100
    ) / 100

    settings["stop_loss_pnl"] = FloatPrompt.ask(
        "Stop Loss PnL % (e.g. 80 for 80%)",
        default=settings["stop_loss_pnl"] * 100
    ) / 100

    save_settings(settings)
    console.print("[green]Saved![/green]")


def edit_entry_settings(settings: dict):
    """Edit entry/exit settings."""
    show_header()
    console.print(Panel("[bold]Entry/Exit Settings[/bold]", style="cyan"))

    settings["entry_offset_min"] = FloatPrompt.ask(
        "Entry Offset MIN % (e.g. 0.25)",
        default=settings["entry_offset_min"]
    )

    settings["entry_offset_max"] = FloatPrompt.ask(
        "Entry Offset MAX % (e.g. 1.0)",
        default=settings["entry_offset_max"]
    )

    settings["reposition_threshold"] = FloatPrompt.ask(
        "Reposition Threshold % (e.g. 2.7)",
        default=settings["reposition_threshold"]
    )

    settings["reposition_random"] = FloatPrompt.ask(
        "Reposition Random ± % (e.g. 0.5)",
        default=settings["reposition_random"]
    )

    settings["check_interval_min"] = IntPrompt.ask(
        "Check Interval MIN (seconds)",
        default=settings["check_interval_min"]
    )

    settings["check_interval_max"] = IntPrompt.ask(
        "Check Interval MAX (seconds)",
        default=settings["check_interval_max"]
    )

    save_settings(settings)
    console.print("[green]Saved![/green]")


def edit_trading_hours(settings: dict):
    """Edit trading hours."""
    show_header()
    console.print(Panel("[bold]Trading Hours (MSK)[/bold]", style="cyan"))

    settings["trading_start_hour"] = IntPrompt.ask(
        "Start Hour (0-23)",
        default=settings["trading_start_hour"]
    )

    settings["trading_end_hour"] = IntPrompt.ask(
        "End Hour (1-24, 24=midnight)",
        default=settings["trading_end_hour"]
    )

    settings["trading_hours_variance"] = IntPrompt.ask(
        "Variance ± minutes",
        default=settings["trading_hours_variance"]
    )

    save_settings(settings)
    console.print("[green]Saved![/green]")


def edit_wallet_settings(settings: dict):
    """Edit wallet and RPC settings."""
    show_header()
    console.print(Panel("[bold]Wallet & RPC[/bold]", style="cyan"))

    settings["rpc_url"] = Prompt.ask(
        "RPC URL",
        default=settings["rpc_url"]
    )

    console.print("[dim]Enter private key (with 0x prefix) or press Enter to keep current[/dim]")
    new_pk = Prompt.ask("Private Key", default="", password=True)
    if new_pk:
        settings["private_key"] = new_pk

    save_settings(settings)
    console.print("[green]Saved![/green]")


def toggle_mode(settings: dict):
    """Toggle between DRY RUN and LIVE."""
    settings["dry_run"] = not settings["dry_run"]
    mode = "DRY RUN" if settings["dry_run"] else "LIVE"
    save_settings(settings)
    console.print(f"[yellow]Mode switched to: {mode}[/yellow]")


async def run_bot(settings: dict):
    """Run the trading bot."""
    show_header()

    if not settings["private_key"]:
        console.print("[red]ERROR: Private key not set! Go to Menu -> Edit Wallet[/red]")
        Prompt.ask("Press Enter to continue")
        return

    if not settings["dry_run"]:
        if not Confirm.ask("[red]LIVE MODE! Real money will be used. Continue?[/red]"):
            return

    # Apply settings
    apply_settings_to_config(settings)

    # Show startup info
    mode_style = "green" if settings["dry_run"] else "red bold"
    mode_text = "DRY RUN" if settings["dry_run"] else "LIVE TRADING"

    info = Table(show_header=False, box=box.SIMPLE)
    info.add_column(width=20)
    info.add_column()
    info.add_row("Mode:", f"[{mode_style}]{mode_text}[/{mode_style}]")
    info.add_row("Pair:", settings["pair_name"])
    info.add_row("Position:", f"${settings['position_size']} x {settings['leverage']}x")
    info.add_row("Entry:", f"{settings['entry_offset_min']}% - {settings['entry_offset_max']}%")

    console.print(Panel(info, title="Starting Bot", box=box.ROUNDED))
    console.print()
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    console.print()

    # Import and run main
    from main import main
    await main()


def main_menu():
    """Main application loop."""
    settings = load_settings()

    # Load private key from config if not in settings
    if not settings["private_key"]:
        import config
        if hasattr(config, 'PRIVATE_KEY') and config.PRIVATE_KEY:
            settings["private_key"] = config.PRIVATE_KEY
            save_settings(settings)

    while True:
        show_header()
        show_settings_table(settings)

        choice = show_menu()

        if choice == "1":
            edit_position_settings(settings)
        elif choice == "2":
            edit_entry_settings(settings)
        elif choice == "3":
            edit_trading_hours(settings)
        elif choice == "4":
            edit_wallet_settings(settings)
        elif choice == "5":
            toggle_mode(settings)
        elif choice.lower() == "s":
            try:
                asyncio.run(run_bot(settings))
            except KeyboardInterrupt:
                console.print("\n[yellow]Bot stopped[/yellow]")
                Prompt.ask("Press Enter to continue")
        elif choice.lower() == "q":
            console.print("[cyan]Goodbye![/cyan]")
            break

        # Small pause to see messages
        import time
        time.sleep(0.5)


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[cyan]Goodbye![/cyan]")

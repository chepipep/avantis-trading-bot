import customtkinter as ctk
import json
import asyncio
import threading
from pathlib import Path
from datetime import datetime, timedelta, timezone

SETTINGS_FILE = Path(__file__).parent / "settings.json"
MSK = timezone(timedelta(hours=3))

# Dark theme + soft yellow
COLORS = {
    "bg": "#1a1a1a",
    "card": "#242424",
    "border": "#333333",
    "input": "#2a2a2a",

    "primary": "#f0c674",
    "primary_dark": "#d4a84a",

    "text": "#e8e8e8",
    "text_secondary": "#a0a0a0",
    "text_dim": "#666666",

    "danger": "#e06060",
}

DEFAULT_SETTINGS = {
    "rpc_url": "https://mainnet.base.org",
    "private_key": "",
    "license_key": "",
    "dry_run": True,
    "pair_name": "BTC/USD",
    "pair_index": 1,
    "position_size": 10.0,
    "leverage": 75,
    "take_profit_pnl": 80,
    "stop_loss_pnl": 80,
    "entry_offset_min": 0.25,
    "entry_offset_max": 1.0,
    "reposition_threshold": 1.0,
    "deposit_variance": 5.0,
    "deposit_step": 0.5,
    "check_interval_min": 10,
    "check_interval_max": 30,
    "trading_start_hour": 13,
    "trading_end_hour": 4,
    "trading_variance": 15,
}


def load_settings():
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE) as f:
                return {**DEFAULT_SETTINGS, **json.load(f)}
        except:
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


class Card(ctk.CTkFrame):
    def __init__(self, master, title="", **kwargs):
        super().__init__(master, fg_color=COLORS["card"], corner_radius=12,
                        border_width=1, border_color=COLORS["border"], **kwargs)
        if title:
            tf = ctk.CTkFrame(self, fg_color="transparent")
            tf.pack(fill="x", padx=16, pady=(12, 8))
            ctk.CTkFrame(tf, width=6, height=6, corner_radius=3,
                        fg_color=COLORS["primary"]).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(tf, text=title, font=ctk.CTkFont(size=11, weight="bold"),
                        text_color=COLORS["text_secondary"]).pack(side="left")


class StatBox(ctk.CTkFrame):
    def __init__(self, master, label, value, color=None, **kwargs):
        super().__init__(master, fg_color=COLORS["card"], corner_radius=10,
                        border_width=1, border_color=COLORS["border"], **kwargs)
        self.color = color or COLORS["primary"]
        ctk.CTkLabel(self, text=label, font=ctk.CTkFont(size=9),
                    text_color=COLORS["text_dim"]).pack(pady=(8, 1))
        self.value_label = ctk.CTkLabel(self, text=value,
            font=ctk.CTkFont(size=15, weight="bold"), text_color=self.color)
        self.value_label.pack(pady=(0, 8))

    def set_value(self, value, color=None):
        self.value_label.configure(text=value)
        if color:
            self.value_label.configure(text_color=color)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.bot_running = False
        self.bot_thread = None
        self.pending_orders = []
        self.open_trades = []
        self.license_valid = False

        self.title("Delta-Neutral Bot")
        self.geometry("880x780")
        self.configure(fg_color=COLORS["bg"])
        ctk.set_appearance_mode("dark")

        # Check license first
        if not self.check_license():
            self.show_activation_screen()
            return

        self.create_main_ui()

    def create_main_ui(self):
        # Scrollable container for small windows
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=24, pady=20)

        self.create_header(scroll)
        self.create_pair_panel(scroll)
        self.create_stats(scroll)
        self.create_orders_panel(scroll)
        self.create_cards(scroll)
        self.create_log(scroll)
        self.create_footer(scroll)
        self.load_pk_from_config()

        # Check orders on startup
        self.after(500, self.check_orders_async)

    def check_license(self) -> bool:
        from license import validate_key
        key = self.settings.get("license_key", "")
        is_valid, msg = validate_key(key)
        self.license_valid = is_valid
        return is_valid

    def show_activation_screen(self):
        # Clear window
        for w in self.winfo_children():
            w.destroy()

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.place(relx=0.5, rely=0.5, anchor="center")

        # Logo
        logo_frame = ctk.CTkFrame(frame, fg_color=COLORS["card"],
                                  corner_radius=16, width=80, height=80,
                                  border_width=2, border_color=COLORS["primary"])
        logo_frame.pack(pady=(0, 20))
        logo_frame.pack_propagate(False)
        ctk.CTkLabel(logo_frame, text="DN", font=ctk.CTkFont(size=28, weight="bold"),
                    text_color=COLORS["primary"]).place(relx=0.5, rely=0.5, anchor="center")

        # Title
        ctk.CTkLabel(frame, text="Delta-Neutral Bot",
                    font=ctk.CTkFont(size=24, weight="bold"),
                    text_color=COLORS["text"]).pack(pady=(0, 5))

        ctk.CTkLabel(frame, text="Enter your license key to activate",
                    font=ctk.CTkFont(size=12),
                    text_color=COLORS["text_secondary"]).pack(pady=(0, 20))

        # Key input
        self.license_entry = ctk.CTkEntry(frame, width=320, height=45,
                                          corner_radius=10,
                                          fg_color=COLORS["input"],
                                          border_color=COLORS["border"],
                                          text_color=COLORS["text"],
                                          font=ctk.CTkFont(size=14),
                                          placeholder_text="XXXX-XXXX-XXXX-XXXX")
        self.license_entry.pack(pady=(0, 10))

        # Status label
        self.activation_status = ctk.CTkLabel(frame, text="",
                                              font=ctk.CTkFont(size=11),
                                              text_color=COLORS["danger"])
        self.activation_status.pack(pady=(0, 10))

        # Activate button
        ctk.CTkButton(frame, text="Activate", width=320, height=42,
                     font=ctk.CTkFont(size=14, weight="bold"),
                     corner_radius=10, fg_color=COLORS["primary"],
                     hover_color=COLORS["primary_dark"],
                     text_color=COLORS["bg"],
                     command=self.activate_license).pack(pady=(0, 15))

        # Buy link
        buy_frame = ctk.CTkFrame(frame, fg_color="transparent")
        buy_frame.pack()
        ctk.CTkLabel(buy_frame, text="Don't have a key?",
                    font=ctk.CTkFont(size=11),
                    text_color=COLORS["text_dim"]).pack(side="left")
        ctk.CTkButton(buy_frame, text="Buy License", width=80, height=24,
                     font=ctk.CTkFont(size=11), corner_radius=6,
                     fg_color="transparent", hover_color=COLORS["card"],
                     text_color=COLORS["primary"],
                     command=self.open_buy_link).pack(side="left", padx=(5, 0))

    def activate_license(self):
        from license import validate_key
        key = self.license_entry.get().strip().upper()

        is_valid, msg = validate_key(key)

        if is_valid:
            self.settings["license_key"] = key
            save_settings(self.settings)
            self.license_valid = True
            self.activation_status.configure(text="License activated!", text_color="#4CAF50")

            # Reload UI
            self.after(1000, self._reload_main_ui)
        else:
            self.activation_status.configure(text=msg, text_color=COLORS["danger"])

    def _reload_main_ui(self):
        for w in self.winfo_children():
            w.destroy()
        self.create_main_ui()

    def open_buy_link(self):
        import webbrowser
        webbrowser.open("https://t.me/Chepoop")

    def create_header(self, parent):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", pady=(0, 14))

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left")

        logo = ctk.CTkFrame(left, fg_color=COLORS["card"],
                           corner_radius=10, width=36, height=36,
                           border_width=1, border_color=COLORS["primary"])
        logo.pack(side="left", padx=(0, 10))
        logo.pack_propagate(False)
        ctk.CTkLabel(logo, text="DN", font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=COLORS["primary"]).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(left, text="Delta", font=ctk.CTkFont(size=22, weight="bold"),
                    text_color=COLORS["text"]).pack(side="left")
        ctk.CTkLabel(left, text="Neutral", font=ctk.CTkFont(size=22, weight="bold"),
                    text_color=COLORS["primary"]).pack(side="left", padx=(2, 0))

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right")

        self.mode_var = ctk.StringVar(value="DRY RUN" if self.settings["dry_run"] else "LIVE")
        self.mode_btn = ctk.CTkSegmentedButton(
            right, values=["DRY RUN", "LIVE"],
            variable=self.mode_var, command=self.on_mode_change,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=COLORS["border"],
            selected_color=COLORS["primary"],
            selected_hover_color=COLORS["primary_dark"],
            unselected_color=COLORS["card"],
            text_color=COLORS["bg"],
            corner_radius=8
        )
        self.mode_btn.pack()

    def create_pair_panel(self, parent):
        from pairs import PAIR_NAMES, get_pair_index

        pair_card = Card(parent, title="TRADING PAIR")
        pair_card.pack(fill="x", pady=(0, 10))

        content = ctk.CTkFrame(pair_card, fg_color="transparent")
        content.pack(fill="x", padx=16, pady=(0, 12))

        # Row with selector and price
        row = ctk.CTkFrame(content, fg_color="transparent")
        row.pack(fill="x")

        # Pair selector
        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left")

        ctk.CTkLabel(left, text="Pair", font=ctk.CTkFont(size=10),
                    text_color=COLORS["text_secondary"]).pack(anchor="w")

        self.pair_var = ctk.StringVar(value=self.settings.get("pair_name", "BTC/USD"))
        self.pair_selector = ctk.CTkComboBox(
            left, values=PAIR_NAMES, variable=self.pair_var,
            width=140, height=34, corner_radius=8,
            fg_color=COLORS["input"], border_color=COLORS["border"],
            button_color=COLORS["primary"], button_hover_color=COLORS["primary_dark"],
            dropdown_fg_color=COLORS["card"], dropdown_hover_color=COLORS["border"],
            text_color=COLORS["text"], font=ctk.CTkFont(size=12),
            command=self.on_pair_change
        )
        self.pair_selector.pack(pady=(3, 0))

        # Current price display
        right = ctk.CTkFrame(row, fg_color="transparent")
        right.pack(side="right")

        ctk.CTkLabel(right, text="Current Price", font=ctk.CTkFont(size=10),
                    text_color=COLORS["text_secondary"]).pack(anchor="e")

        self.price_label = ctk.CTkLabel(
            right, text="Loading...",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["primary"]
        )
        self.price_label.pack(anchor="e", pady=(3, 0))

        # Start price updates
        self.update_price()

    def on_pair_change(self, value):
        from pairs import get_pair_index
        self.settings["pair_name"] = value
        try:
            self.settings["pair_index"] = get_pair_index(value)
        except:
            self.settings["pair_index"] = 1
        save_settings(self.settings)
        self.update_price()
        self.log(f"Pair changed to {value}")

    def update_price(self):
        thread = threading.Thread(target=self._fetch_price, daemon=True)
        thread.start()
        # Schedule next update in 5 seconds
        self.after(5000, self.update_price)

    def _fetch_price(self):
        try:
            from pairs import get_pair_price
            import asyncio

            pair = self.settings.get("pair_name", "BTC/USD")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            price = loop.run_until_complete(get_pair_price(pair))
            loop.close()

            if price > 0:
                if price >= 1000:
                    price_str = f"${price:,.2f}"
                elif price >= 1:
                    price_str = f"${price:.2f}"
                else:
                    price_str = f"${price:.6f}"

                self.after(0, lambda: self.price_label.configure(text=price_str))
        except Exception as e:
            self.after(0, lambda: self.price_label.configure(text="Error"))

    def create_stats(self, parent):
        stats = ctk.CTkFrame(parent, fg_color="transparent")
        stats.pack(fill="x", pady=(0, 14))

        mode = "DRY" if self.settings["dry_run"] else "LIVE"
        mode_color = COLORS["primary"] if self.settings["dry_run"] else COLORS["danger"]

        self.stat_mode = StatBox(stats, "MODE", mode, mode_color)
        self.stat_mode.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.stat_leverage = StatBox(stats, "LEVERAGE", f"{self.settings['leverage']}x")
        self.stat_leverage.pack(side="left", fill="x", expand=True, padx=5)

        self.stat_position = StatBox(stats, "POSITION", f"${self.settings['position_size']:.0f}")
        self.stat_position.pack(side="left", fill="x", expand=True, padx=5)

        self.stat_entry = StatBox(stats, "ENTRY",
            f"{self.settings['entry_offset_min']}-{self.settings['entry_offset_max']}%")
        self.stat_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))

    def create_orders_panel(self, parent):
        self.orders_card = Card(parent, title="OPEN ORDERS")
        self.orders_card.pack(fill="x", pady=(0, 10))

        content = ctk.CTkFrame(self.orders_card, fg_color="transparent")
        content.pack(fill="x", padx=16, pady=(0, 12))

        # Status row
        status_row = ctk.CTkFrame(content, fg_color="transparent")
        status_row.pack(fill="x", pady=(0, 8))

        self.orders_status_label = ctk.CTkLabel(
            status_row, text="Checking...",
            font=ctk.CTkFont(size=11), text_color=COLORS["text_secondary"]
        )
        self.orders_status_label.pack(side="left")

        # Buttons row
        btn_row = ctk.CTkFrame(content, fg_color="transparent")
        btn_row.pack(fill="x")

        self.check_orders_btn = ctk.CTkButton(
            btn_row, text="Check Orders", width=100, height=32,
            font=ctk.CTkFont(size=11), corner_radius=8,
            fg_color=COLORS["border"], hover_color=COLORS["card"],
            text_color=COLORS["text"], command=self.check_orders_async
        )
        self.check_orders_btn.pack(side="left", padx=(0, 8))

        self.cancel_orders_btn = ctk.CTkButton(
            btn_row, text="Cancel All", width=100, height=32,
            font=ctk.CTkFont(size=11), corner_radius=8,
            fg_color=COLORS["danger"], hover_color="#c04040",
            text_color=COLORS["text"], command=self.cancel_all_orders_async,
            state="disabled"
        )
        self.cancel_orders_btn.pack(side="left", padx=(0, 8))

        self.open_orders_btn = ctk.CTkButton(
            btn_row, text="Open Orders", width=110, height=32,
            font=ctk.CTkFont(size=11, weight="bold"), corner_radius=8,
            fg_color=COLORS["primary"], hover_color=COLORS["primary_dark"],
            text_color=COLORS["bg"], command=self.open_orders_async
        )
        self.open_orders_btn.pack(side="left")

        # Orders list
        self.orders_list_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.orders_list_frame.pack(fill="x", pady=(8, 0))

    def check_orders_async(self):
        if not self.settings.get("private_key"):
            self.orders_status_label.configure(text="No wallet configured")
            return

        self.orders_status_label.configure(text="Checking...")
        self.check_orders_btn.configure(state="disabled")

        thread = threading.Thread(target=self._check_orders_thread, daemon=True)
        thread.start()

    def _check_orders_thread(self):
        try:
            self.apply_settings_to_config()
            from trader import AvantisTrader
            import config

            trader = AvantisTrader(config.RPC_URL, config.PRIVATE_KEY)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            trades, pending = loop.run_until_complete(trader.get_open_trades())
            loop.close()

            self.open_trades = trades
            self.pending_orders = pending

            self.after(0, self._update_orders_ui)
        except Exception as e:
            self.after(0, lambda: self._orders_error(str(e)))

    def _update_orders_ui(self):
        self.check_orders_btn.configure(state="normal")

        # Clear old list
        for w in self.orders_list_frame.winfo_children():
            w.destroy()

        n_trades = len(self.open_trades)
        n_pending = len(self.pending_orders)

        if n_trades == 0 and n_pending == 0:
            self.orders_status_label.configure(text="No open orders or positions")
            self.cancel_orders_btn.configure(state="disabled")
            return

        status_parts = []
        if n_trades > 0:
            status_parts.append(f"{n_trades} position(s)")
        if n_pending > 0:
            status_parts.append(f"{n_pending} pending order(s)")

        self.orders_status_label.configure(text=" | ".join(status_parts))
        self.cancel_orders_btn.configure(state="normal" if n_pending > 0 else "disabled")

        # Show pending orders
        for order in self.pending_orders:
            self._add_order_row(order)

        # Show open trades
        for trade in self.open_trades:
            self._add_trade_row(trade)

    def _add_order_row(self, order):
        row = ctk.CTkFrame(self.orders_list_frame, fg_color=COLORS["card"],
                          corner_radius=8, height=58, border_width=1,
                          border_color=COLORS["primary"])
        row.pack(fill="x", pady=3)
        row.pack_propagate(False)

        # Cancel button (X) on the left
        cancel_btn = ctk.CTkButton(
            row, text="✕", width=32, height=32,
            font=ctk.CTkFont(size=14, weight="bold"), corner_radius=6,
            fg_color=COLORS["danger"], hover_color="#c04040",
            text_color=COLORS["text"],
            command=lambda o=order: self.cancel_single_order_async(o)
        )
        cancel_btn.pack(side="left", padx=(8, 0))

        # Left side - status and side
        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", padx=(8, 0), pady=8)

        side = "LONG" if order.buy else "SHORT"
        side_color = "#4CAF50" if order.buy else "#F44336"

        top_left = ctk.CTkFrame(left, fg_color="transparent")
        top_left.pack(anchor="w")
        ctk.CTkLabel(top_left, text="PENDING", font=ctk.CTkFont(size=10, weight="bold"),
                    text_color=COLORS["primary"]).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(top_left, text=side, font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=side_color).pack(side="left")

        # Price and leverage
        price = getattr(order, 'price', getattr(order, 'openPrice', 0))
        leverage = getattr(order, 'leverage', 0)
        bottom_left = ctk.CTkFrame(left, fg_color="transparent")
        bottom_left.pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(bottom_left, text=f"Entry: ${price:,.2f}",
                    font=ctk.CTkFont(size=11), text_color=COLORS["text"]).pack(side="left")
        ctk.CTkLabel(bottom_left, text=f"  {leverage}x",
                    font=ctk.CTkFont(size=11, weight="bold"), text_color=COLORS["primary"]).pack(side="left")

        # Right side - TP/SL and collateral
        right = ctk.CTkFrame(row, fg_color="transparent")
        right.pack(side="right", padx=(0, 12), pady=8)

        collateral = getattr(order, 'open_collateral', getattr(order, 'openCollateral', 0))
        tp = getattr(order, 'tp', 0)
        sl = getattr(order, 'sl', 0)

        top_right = ctk.CTkFrame(right, fg_color="transparent")
        top_right.pack(anchor="e")
        ctk.CTkLabel(top_right, text=f"${collateral:.1f}",
                    font=ctk.CTkFont(size=13, weight="bold"),
                    text_color=COLORS["text"]).pack(side="right")

        bottom_right = ctk.CTkFrame(right, fg_color="transparent")
        bottom_right.pack(anchor="e", pady=(2, 0))
        ctk.CTkLabel(bottom_right, text=f"TP: ${tp:,.0f}",
                    font=ctk.CTkFont(size=10), text_color="#4CAF50").pack(side="left", padx=(0, 8))
        ctk.CTkLabel(bottom_right, text=f"SL: ${sl:,.0f}",
                    font=ctk.CTkFont(size=10), text_color="#F44336").pack(side="left")

    def _add_trade_row(self, trade):
        row = ctk.CTkFrame(self.orders_list_frame, fg_color=COLORS["card"],
                          corner_radius=8, height=58, border_width=1,
                          border_color="#4CAF50")
        row.pack(fill="x", pady=3)
        row.pack_propagate(False)

        # Left side - status and side
        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", padx=(12, 0), pady=8)

        side = "LONG" if getattr(trade, 'buy', getattr(trade, 'is_long', False)) else "SHORT"
        side_color = "#4CAF50" if side == "LONG" else "#F44336"

        top_left = ctk.CTkFrame(left, fg_color="transparent")
        top_left.pack(anchor="w")
        ctk.CTkLabel(top_left, text="OPEN", font=ctk.CTkFont(size=10, weight="bold"),
                    text_color="#4CAF50").pack(side="left", padx=(0, 8))
        ctk.CTkLabel(top_left, text=side, font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=side_color).pack(side="left")

        # Price and leverage
        price = getattr(trade, 'open_price', getattr(trade, 'openPrice', 0))
        leverage = getattr(trade, 'leverage', 0)
        bottom_left = ctk.CTkFrame(left, fg_color="transparent")
        bottom_left.pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(bottom_left, text=f"Entry: ${price:,.2f}",
                    font=ctk.CTkFont(size=11), text_color=COLORS["text"]).pack(side="left")
        ctk.CTkLabel(bottom_left, text=f"  {leverage}x",
                    font=ctk.CTkFont(size=11, weight="bold"), text_color=COLORS["primary"]).pack(side="left")

        # Right side - TP/SL and collateral
        right = ctk.CTkFrame(row, fg_color="transparent")
        right.pack(side="right", padx=(0, 12), pady=8)

        collateral = getattr(trade, 'collateral_in_trade', getattr(trade, 'collateralInTrade', 0))
        tp = getattr(trade, 'tp', 0)
        sl = getattr(trade, 'sl', 0)

        top_right = ctk.CTkFrame(right, fg_color="transparent")
        top_right.pack(anchor="e")
        ctk.CTkLabel(top_right, text=f"${collateral:.1f}",
                    font=ctk.CTkFont(size=13, weight="bold"),
                    text_color=COLORS["text"]).pack(side="right")

        bottom_right = ctk.CTkFrame(right, fg_color="transparent")
        bottom_right.pack(anchor="e", pady=(2, 0))
        ctk.CTkLabel(bottom_right, text=f"TP: ${tp:,.0f}",
                    font=ctk.CTkFont(size=10), text_color="#4CAF50").pack(side="left", padx=(0, 8))
        ctk.CTkLabel(bottom_right, text=f"SL: ${sl:,.0f}",
                    font=ctk.CTkFont(size=10), text_color="#F44336").pack(side="left")

    def _orders_error(self, msg):
        self.check_orders_btn.configure(state="normal")
        self.orders_status_label.configure(text=f"Error: {msg[:40]}...")
        self.log(f"Orders check error: {msg}")

    def cancel_single_order_async(self, order):
        """Cancel a single pending order."""
        self.orders_status_label.configure(text="Cancelling order...")
        thread = threading.Thread(
            target=self._cancel_single_order_thread,
            args=(order,), daemon=True
        )
        thread.start()

    def _cancel_single_order_thread(self, order):
        try:
            self.apply_settings_to_config()
            from trader import AvantisTrader
            import config

            trader = AvantisTrader(config.RPC_URL, config.PRIVATE_KEY)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            loop.run_until_complete(trader.cancel_order(
                pair_index=order.pairIndex,
                trade_index=order.index,
                dry_run=config.DRY_RUN
            ))

            loop.close()

            side = "LONG" if order.buy else "SHORT"
            self.after(0, lambda: self.log(f"Cancelled {side} order #{order.index}"))
            self.after(0, self.check_orders_async)

        except Exception as e:
            self.after(0, lambda: self.log(f"Cancel error: {e}"))
            self.after(0, lambda: self._orders_error(str(e)))

    def cancel_all_orders_async(self):
        if not self.pending_orders:
            return

        self.cancel_orders_btn.configure(state="disabled")
        self.orders_status_label.configure(text="Cancelling...")

        thread = threading.Thread(target=self._cancel_orders_thread, daemon=True)
        thread.start()

    def _cancel_orders_thread(self):
        try:
            self.apply_settings_to_config()
            from trader import AvantisTrader
            import config
            import random

            trader = AvantisTrader(config.RPC_URL, config.PRIVATE_KEY)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            for order in self.pending_orders:
                try:
                    loop.run_until_complete(trader.cancel_order(
                        pair_index=order.pairIndex,
                        trade_index=order.index,
                        dry_run=config.DRY_RUN
                    ))
                    self.after(0, lambda: self.log(f"Cancelled order #{order.index}"))
                    loop.run_until_complete(asyncio.sleep(random.uniform(1, 2)))
                except Exception as e:
                    self.after(0, lambda e=e: self.log(f"Cancel error: {e}"))

            loop.close()
            self.after(0, self.check_orders_async)
        except Exception as e:
            self.after(0, lambda: self._orders_error(str(e)))

    def open_orders_async(self):
        if not self.settings.get("private_key"):
            self.log("ERROR: No private key!")
            return

        self.open_orders_btn.configure(state="disabled")
        self.orders_status_label.configure(text="Opening orders...")
        self.log("Opening LONG + SHORT limit orders...")

        thread = threading.Thread(target=self._open_orders_thread, daemon=True)
        thread.start()

    def _open_orders_thread(self):
        try:
            import random
            self.apply_settings_to_config()
            from trader import AvantisTrader
            from price import get_btc_price
            from strategy import calc_tp_sl_price
            import config

            trader = AvantisTrader(config.RPC_URL, config.PRIVATE_KEY)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Get current price
            anchor_price = loop.run_until_complete(get_btc_price())
            self.after(0, lambda: self.log(f"Anchor price: ${anchor_price:.2f}"))

            # Random offset
            offset = random.uniform(config.ENTRY_OFFSET_MIN, config.ENTRY_OFFSET_MAX)

            # Random direction
            direction = random.choice(["ABOVE", "BELOW"])
            if direction == "ABOVE":
                entry_price = anchor_price * (1 + offset)
            else:
                entry_price = anchor_price * (1 - offset)

            self.after(0, lambda: self.log(f"Entry: ${entry_price:.2f} ({direction}, {offset*100:.2f}%)"))

            # Calculate TP/SL
            long_tp, long_sl = calc_tp_sl_price(
                entry_price, config.LEVERAGE,
                config.TAKE_PROFIT_PNL, config.STOP_LOSS_PNL, True
            )
            short_tp, short_sl = calc_tp_sl_price(
                entry_price, config.LEVERAGE,
                config.TAKE_PROFIT_PNL, config.STOP_LOSS_PNL, False
            )

            # Vary collateral
            variance = getattr(config, 'DEPOSIT_VARIANCE', 0.05)
            step = getattr(config, 'DEPOSIT_STEP', 0.5)
            collateral = config.POSITION_SIZE_USDC * (1 + random.uniform(-variance, variance))
            collateral = round(collateral / step) * step

            # Place LONG order
            loop.run_until_complete(trader.place_limit_order(
                pair_index=config.PAIR_INDEX,
                is_long=True,
                collateral=collateral,
                leverage=config.LEVERAGE,
                limit_price=entry_price,
                tp_price=long_tp,
                sl_price=long_sl,
                direction=direction,
                dry_run=config.DRY_RUN
            ))
            self.after(0, lambda: self.log(f"LONG order placed"))

            if not config.DRY_RUN:
                loop.run_until_complete(asyncio.sleep(random.uniform(2, 4)))

            # Place SHORT order
            loop.run_until_complete(trader.place_limit_order(
                pair_index=config.PAIR_INDEX,
                is_long=False,
                collateral=collateral,
                leverage=config.LEVERAGE,
                limit_price=entry_price,
                tp_price=short_tp,
                sl_price=short_sl,
                direction=direction,
                dry_run=config.DRY_RUN
            ))
            self.after(0, lambda: self.log(f"SHORT order placed"))

            loop.close()

            self.after(0, lambda: self.open_orders_btn.configure(state="normal"))
            self.after(0, self.check_orders_async)
            self.after(0, lambda: self.log("Orders placed successfully!"))

        except Exception as e:
            self.after(0, lambda: self.open_orders_btn.configure(state="normal"))
            self.after(0, lambda: self.log(f"Open orders error: {e}"))
            self.after(0, lambda: self._orders_error(str(e)))

    def create_cards(self, parent):
        cards = ctk.CTkFrame(parent, fg_color="transparent")
        cards.pack(fill="x", pady=(0, 10))
        cards.grid_columnconfigure((0, 1), weight=1)

        pos = Card(cards, title="POSITION")
        pos.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        pi = ctk.CTkFrame(pos, fg_color="transparent")
        pi.pack(fill="x", padx=16, pady=(0, 12))

        r0 = ctk.CTkFrame(pi, fg_color="transparent")
        r0.pack(fill="x", pady=(0, 8))
        r0.grid_columnconfigure((0, 1, 2), weight=1)
        self._field_grid(r0, "Size", "position_size", 0)
        self._field_grid(r0, "Var %", "deposit_variance", 1)
        self._field_grid(r0, "Step", "deposit_step", 2)

        self._field(pi, "Leverage", "leverage", int)

        r = ctk.CTkFrame(pi, fg_color="transparent")
        r.pack(fill="x")
        r.grid_columnconfigure((0, 1), weight=1)
        self._field_grid(r, "TP %", "take_profit_pnl", 0)
        self._field_grid(r, "SL %", "stop_loss_pnl", 1)

        trade = Card(cards, title="TRADING")
        trade.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        ti = ctk.CTkFrame(trade, fg_color="transparent")
        ti.pack(fill="x", padx=16, pady=(0, 12))

        r1 = ctk.CTkFrame(ti, fg_color="transparent")
        r1.pack(fill="x", pady=(0, 8))
        r1.grid_columnconfigure((0, 1), weight=1)
        self._field_grid(r1, "Entry Min %", "entry_offset_min", 0)
        self._field_grid(r1, "Entry Max %", "entry_offset_max", 1)

        self._field(ti, "Reposition %", "reposition_threshold")

        # Trading hours section
        hours_frame = ctk.CTkFrame(ti, fg_color="transparent")
        hours_frame.pack(fill="x", pady=(8, 0))

        ctk.CTkLabel(hours_frame, text="Trading Hours (MSK)",
                    font=ctk.CTkFont(size=10),
                    text_color=COLORS["text_secondary"]).pack(anchor="w")

        hours_row = ctk.CTkFrame(hours_frame, fg_color="transparent")
        hours_row.pack(fill="x", pady=(3, 0))

        self.start_hour_entry = ctk.CTkEntry(hours_row, width=50, height=34, corner_radius=8,
                        fg_color=COLORS["input"], border_color=COLORS["border"],
                        text_color=COLORS["text"], font=ctk.CTkFont(size=12),
                        justify="center")
        self.start_hour_entry.insert(0, str(self.settings["trading_start_hour"]))
        self.start_hour_entry.pack(side="left")
        self.start_hour_entry.bind("<FocusOut>", lambda e: self._save_hours())

        ctk.CTkLabel(hours_row, text=" : 00  —  ", font=ctk.CTkFont(size=12),
                    text_color=COLORS["text"]).pack(side="left")

        self.end_hour_entry = ctk.CTkEntry(hours_row, width=50, height=34, corner_radius=8,
                        fg_color=COLORS["input"], border_color=COLORS["border"],
                        text_color=COLORS["text"], font=ctk.CTkFont(size=12),
                        justify="center")
        self.end_hour_entry.insert(0, str(self.settings["trading_end_hour"]))
        self.end_hour_entry.pack(side="left")
        self.end_hour_entry.bind("<FocusOut>", lambda e: self._save_hours())

        ctk.CTkLabel(hours_row, text=" : 00   ±", font=ctk.CTkFont(size=12),
                    text_color=COLORS["text"]).pack(side="left")

        self.variance_entry = ctk.CTkEntry(hours_row, width=40, height=34, corner_radius=8,
                        fg_color=COLORS["input"], border_color=COLORS["border"],
                        text_color=COLORS["text"], font=ctk.CTkFont(size=12),
                        justify="center")
        self.variance_entry.insert(0, str(self.settings.get("trading_variance", 15)))
        self.variance_entry.pack(side="left")
        self.variance_entry.bind("<FocusOut>", lambda e: self._save_hours())

        ctk.CTkLabel(hours_row, text=" min", font=ctk.CTkFont(size=11),
                    text_color=COLORS["text_secondary"]).pack(side="left")

        # Preview label
        self.hours_preview = ctk.CTkLabel(hours_frame, text="",
                    font=ctk.CTkFont(size=10),
                    text_color=COLORS["primary"])
        self.hours_preview.pack(anchor="w", pady=(4, 0))
        self._update_hours_preview()

    def _field(self, parent, label, key, cast=float):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=10),
                    text_color=COLORS["text_secondary"]).pack(anchor="w")
        e = ctk.CTkEntry(f, height=34, corner_radius=8,
                        fg_color=COLORS["input"], border_color=COLORS["border"],
                        text_color=COLORS["text"], font=ctk.CTkFont(size=12))
        e.insert(0, str(self.settings[key]))
        e.pack(fill="x", pady=(3, 0))
        e.bind("<FocusOut>", lambda ev, k=key, en=e, c=cast: self._save(k, en, c))

    def _field_grid(self, parent, label, key, col, cast=float):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 3, 3 if col == 0 else 0))
        ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=10),
                    text_color=COLORS["text_secondary"]).pack(anchor="w")
        e = ctk.CTkEntry(f, height=34, corner_radius=8,
                        fg_color=COLORS["input"], border_color=COLORS["border"],
                        text_color=COLORS["text"], font=ctk.CTkFont(size=12))
        e.insert(0, str(self.settings[key]))
        e.pack(fill="x", pady=(3, 0))
        e.bind("<FocusOut>", lambda ev, k=key, en=e, c=cast: self._save(k, en, c))

    def _save(self, key, entry, cast):
        try:
            self.settings[key] = cast(entry.get())
            save_settings(self.settings)
            self.update_stats()
        except:
            pass

    def _save_hours(self):
        try:
            self.settings["trading_start_hour"] = int(self.start_hour_entry.get())
            self.settings["trading_end_hour"] = int(self.end_hour_entry.get())
            self.settings["trading_variance"] = int(self.variance_entry.get())
            save_settings(self.settings)
            self._update_hours_preview()
        except:
            pass

    def _update_hours_preview(self):
        try:
            start = self.settings["trading_start_hour"]
            end = self.settings["trading_end_hour"]
            var = self.settings.get("trading_variance", 15)

            # Calculate range with variance
            start_min = (start * 60 - var) % 1440
            start_max = (start * 60 + var) % 1440
            end_min = (end * 60 - var) % 1440
            end_max = (end * 60 + var) % 1440

            def fmt(mins):
                h = (mins // 60) % 24
                m = mins % 60
                return f"{h:02d}:{m:02d}"

            preview = f"Range: {fmt(start_min)}-{fmt(start_max)} to {fmt(end_min)}-{fmt(end_max)}"
            self.hours_preview.configure(text=preview)
        except:
            pass

    def create_log(self, parent):
        log = Card(parent, title="LOG")
        log.pack(fill="both", expand=True, pady=(0, 10))
        self.log_text = ctk.CTkTextbox(
            log, height=100, corner_radius=8,
            fg_color=COLORS["input"], text_color=COLORS["text"],
            font=ctk.CTkFont(family="Consolas", size=10),
            border_width=1, border_color=COLORS["border"]
        )
        self.log_text.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.log("Delta-Neutral Bot v4.1")
        self.log("Ready...")

    def create_footer(self, parent):
        footer = ctk.CTkFrame(parent, fg_color="transparent")
        footer.pack(fill="x")
        self.start_btn = ctk.CTkButton(
            footer, text="START BOT", command=self.toggle_bot,
            font=ctk.CTkFont(size=13, weight="bold"), height=42,
            corner_radius=10, fg_color=COLORS["primary"],
            hover_color=COLORS["primary_dark"], text_color=COLORS["bg"]
        )
        self.start_btn.pack(fill="x")

        wallet_row = ctk.CTkFrame(footer, fg_color="transparent")
        wallet_row.pack(fill="x", pady=(10, 0))

        self.wallet_label = ctk.CTkLabel(wallet_row, text="",
            font=ctk.CTkFont(size=11), text_color=COLORS["text_secondary"])
        self.wallet_label.pack(side="left")

        self.edit_wallet_btn = ctk.CTkButton(
            wallet_row, text="Edit Wallet", width=90, height=28,
            font=ctk.CTkFont(size=11, weight="bold"), corner_radius=6,
            fg_color=COLORS["border"], hover_color=COLORS["card"],
            text_color=COLORS["primary"], command=self.show_wallet_dialog
        )
        self.edit_wallet_btn.pack(side="right")
        self.update_wallet_label()

    def log(self, msg):
        ts = datetime.now(MSK).strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{ts}] {msg}\n")
        self.log_text.see("end")

    def on_mode_change(self, value):
        self.settings["dry_run"] = (value == "DRY RUN")
        save_settings(self.settings)
        self.stat_mode.set_value("DRY" if self.settings["dry_run"] else "LIVE",
            COLORS["primary"] if self.settings["dry_run"] else COLORS["danger"])
        self.log(f"Mode: {value}")

    def update_stats(self):
        self.stat_leverage.set_value(f"{self.settings['leverage']}x")
        self.stat_position.set_value(f"${self.settings['position_size']:.0f}")
        self.stat_entry.set_value(f"{self.settings['entry_offset_min']}-{self.settings['entry_offset_max']}%")

    def update_wallet_label(self):
        pk = self.settings.get("private_key", "")
        self.wallet_label.configure(text=f"Wallet: {pk[:6]}...{pk[-4:]}" if pk else "No wallet")

    def show_wallet_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit Wallet")
        dialog.geometry("420x160")
        dialog.configure(fg_color=COLORS["bg"])
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        # Center dialog
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 420) // 2
        y = self.winfo_y() + (self.winfo_height() - 160) // 2
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(dialog, text="Private Key",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["text_secondary"]).pack(anchor="w", padx=20, pady=(20, 5))

        pk_entry = ctk.CTkEntry(dialog, height=38, corner_radius=8,
            fg_color=COLORS["input"], border_color=COLORS["border"],
            text_color=COLORS["text"], font=ctk.CTkFont(size=12),
            show="*", placeholder_text="Enter private key...")
        pk_entry.pack(fill="x", padx=20)
        if self.settings.get("private_key"):
            pk_entry.insert(0, self.settings["private_key"])

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)

        def save_pk():
            new_pk = pk_entry.get().strip()
            if new_pk:
                self.settings["private_key"] = new_pk
                save_settings(self.settings)
                self.update_wallet_label()
                self.log("Wallet updated")
            dialog.destroy()

        ctk.CTkButton(btn_frame, text="Cancel", width=80, height=34,
            font=ctk.CTkFont(size=11), corner_radius=8,
            fg_color=COLORS["border"], hover_color=COLORS["card"],
            text_color=COLORS["text_secondary"],
            command=dialog.destroy).pack(side="right", padx=(8, 0))
        ctk.CTkButton(btn_frame, text="Save", width=80, height=34,
            font=ctk.CTkFont(size=11, weight="bold"), corner_radius=8,
            fg_color=COLORS["primary"], hover_color=COLORS["primary_dark"],
            text_color=COLORS["bg"], command=save_pk).pack(side="right")

    def load_pk_from_config(self):
        if not self.settings.get("private_key"):
            try:
                import config
                if hasattr(config, 'PRIVATE_KEY') and config.PRIVATE_KEY:
                    self.settings["private_key"] = config.PRIVATE_KEY
                    save_settings(self.settings)
                    self.update_wallet_label()
            except:
                pass

    def toggle_bot(self):
        self.stop_bot() if self.bot_running else self.start_bot()

    def start_bot(self):
        if not self.settings.get("private_key"):
            self.log("ERROR: No private key!")
            return
        if not self.settings["dry_run"]:
            self.log("WARNING: LIVE mode!")

        self.bot_running = True
        self.start_btn.configure(text="STOP BOT", fg_color=COLORS["danger"], hover_color="#c04040")
        self.apply_settings_to_config()
        self.bot_thread = threading.Thread(target=self.run_bot_thread, daemon=True)
        self.bot_thread.start()
        self.log("Bot started!")

    def stop_bot(self):
        self.bot_running = False
        self.start_btn.configure(text="START BOT", fg_color=COLORS["primary"],
                                hover_color=COLORS["primary_dark"])
        self.log("Bot stopped!")

    def apply_settings_to_config(self):
        import config
        config.RPC_URL = self.settings["rpc_url"]
        config.PRIVATE_KEY = self.settings["private_key"]
        config.DRY_RUN = self.settings["dry_run"]
        config.PAIR_INDEX = self.settings["pair_index"]
        config.PAIR_NAME = self.settings["pair_name"]
        config.POSITION_SIZE_USDC = self.settings["position_size"]
        config.LEVERAGE = self.settings["leverage"]
        config.TAKE_PROFIT_PNL = self.settings["take_profit_pnl"] / 100
        config.STOP_LOSS_PNL = self.settings["stop_loss_pnl"] / 100
        config.ENTRY_OFFSET_MIN = self.settings["entry_offset_min"] / 100
        config.ENTRY_OFFSET_MAX = self.settings["entry_offset_max"] / 100
        config.REPOSITION_THRESHOLD_PCT = self.settings["reposition_threshold"] / 100
        config.DEPOSIT_VARIANCE = self.settings.get("deposit_variance", 5.0) / 100
        config.DEPOSIT_STEP = self.settings.get("deposit_step", 0.5)
        config.CHECK_INTERVAL_MIN = self.settings["check_interval_min"]
        config.CHECK_INTERVAL_MAX = self.settings["check_interval_max"]
        config.TRADING_START_HOUR = self.settings["trading_start_hour"]
        config.TRADING_END_HOUR = self.settings["trading_end_hour"]
        config.TRADING_HOURS_VARIANCE = self.settings.get("trading_variance", 15)

    def run_bot_thread(self):
        import sys, io
        class R(io.StringIO):
            def __init__(s, cb): super().__init__(); s.cb = cb
            def write(s, m):
                if m.strip(): s.cb(m.strip())
                return len(m)
            def flush(s): pass

        old = sys.stdout
        sys.stdout = R(lambda m: self.after(0, lambda: self.log(m)))
        try:
            from main import main
            asyncio.run(main())
        except Exception as e:
            self.after(0, lambda: self.log(f"Error: {e}"))
        finally:
            sys.stdout = old
            self.after(0, self.stop_bot)


if __name__ == "__main__":
    App().mainloop()

# Delta-Neutral Trading Bot for Avantis

Automated delta-neutral trading bot for [Avantis DEX](https://avantis.fi/) on Base network.

## What is Delta-Neutral?

The bot opens **LONG** and **SHORT** positions simultaneously at the same price. When price moves, one position hits Take Profit while the other hits Stop Loss - but with proper settings, you profit regardless of direction.

## Features

- GUI interface with dark theme
- Automatic LONG + SHORT limit orders
- Configurable TP/SL percentages
- DRY RUN mode for testing
- Real-time order monitoring
- Auto-repositioning when price moves

## Screenshots

![Bot Interface](https://via.placeholder.com/800x500/1a1a1a/f0c674?text=Delta-Neutral+Bot)

---

## Purchase License

**Price: $30** (one-time payment, lifetime license)

**Contact:** [@Chepoop](https://t.me/Chepoop) on Telegram

### What you get:
- Lifetime license key
- Setup assistance
- Updates

---

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/avantis-trading-bot.git
cd avantis-trading-bot
```

### 2. Install dependencies
```bash
pip install avantis_trader_sdk customtkinter
```

### 3. Setup license file
```bash
# Rename the public license file
mv license_public.py license.py
```

### 4. Run the bot
```bash
python gui.py
```

### 5. Activate
Enter your license key in the activation screen.

### 6. Configure
After activation, click "Edit" to add your wallet private key.

---

## Settings

| Setting | Description |
|---------|-------------|
| `position_size` | Collateral in USDC per position |
| `leverage` | Leverage multiplier (1-150) |
| `take_profit_pnl` | Take profit % (e.g., 80 = +80% PnL) |
| `stop_loss_pnl` | Stop loss % (e.g., 80 = -80% PnL) |
| `entry_offset_min/max` | Entry price offset from current price |
| `dry_run` | Set to `false` for live trading |

---

## Support

Telegram: [@Chepoop](https://t.me/Chepoop)

---

## Disclaimer

This software is for educational purposes only. Trading cryptocurrencies involves significant risk. Use at your own risk.

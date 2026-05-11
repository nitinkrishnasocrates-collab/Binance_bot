# Binance Futures Trading Bot

A production-grade CLI-based trading bot for Binance USDT-M Futures supporting multiple order types including market, limit, stop-limit, OCO, TWAP, and grid trading strategies.

## 🎯 Features

### Core Orders (Mandatory)
- **Market Orders**: Execute immediately at market price
- **Limit Orders**: Execute at specified price or better

### Advanced Orders (Bonus)
- **Stop-Limit Orders**: Trigger limit orders when stop price is hit
- **OCO Orders**: Take-profit and stop-loss orders that cancel each other
- **TWAP Orders**: Split large orders into smaller slices over time
- **Grid Trading**: Automated buy-low/sell-high within a price range

### Additional Features
- ✅ Comprehensive input validation
- ✅ Structured logging with file rotation
- ✅ Error handling and recovery
- ✅ Testnet support for safe testing
- ✅ Account information and balance tracking
- ✅ Real-time price checking

## 📋 Project Structure

```
binance_bot_project/
├── src/
│   ├── __init__.py              # Package initialization
│   ├── config.py                # Configuration and constants
│   ├── logger.py                # Logging system
│   ├── validator.py             # Input validation
│   ├── api_client.py            # Binance API client
│   ├── market_orders.py         # Market and Limit orders
│   ├── limit_orders.py          # Limit order alias
│   ├── bot.py                   # Main CLI interface
│   └── advanced/
│       ├── stop_limit.py        # Stop-Limit orders
│       ├── oco.py               # OCO orders
│       ├── twap.py              # TWAP strategy
│       └── grid_trading.py      # Grid trading strategy
├── logs/                         # Log files directory
├── .env.example                 # Environment configuration template
├── requirements.txt             # Python dependencies
├── README.md                    # This file
└── report.pdf                   # Analysis and screenshots (optional)
```

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Extract the project
unzip binance_bot.zip
cd binance_bot_project

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Credentials

```bash
# Copy and edit environment file
cp .env.example .env

# Edit .env with your credentials
# For TESTNET (default, safer):
TESTNET_MODE=True
TESTNET_API_KEY=your-testnet-key
TESTNET_API_SECRET=your-testnet-secret

# For LIVE trading (use with caution):
TESTNET_MODE=False
BINANCE_API_KEY=your-live-key
BINANCE_API_SECRET=your-live-secret
```

**Get API Keys:**
- **Testnet**: https://testnet.binancefuture.com (Recommended for testing)
- **Live**: https://binance.com (Use with caution)

### 3. Get Testnet API Key

1. Go to https://testnet.binancefuture.com
2. Create account or login
3. Account → API Management
4. Create new key with Futures trading enabled
5. Copy API Key and Secret to `.env` file

## 📖 Usage Guide

### Running the Bot

```bash
# Show help
python src/bot.py --help

# Check account info
python src/bot.py account

# Get current price
python src/bot.py price BTCUSDT
```

### Core Orders

#### Market Orders

```bash
# Market buy 0.01 BTC
python src/bot.py market_buy BTCUSDT 0.01

# Market sell 0.01 BTC
python src/bot.py market_sell BTCUSDT 0.01
```

Market orders execute immediately at the best available price in the order book.

#### Limit Orders

```bash
# Buy 0.01 BTC at 35,000 USDT
python src/bot.py limit_buy BTCUSDT 0.01 35000

# Sell 0.01 BTC at 40,000 USDT
python src/bot.py limit_sell BTCUSDT 0.01 40000
```

Limit orders are placed in the order book and wait for the specified price.

### Advanced Orders

#### Stop-Limit Orders

```bash
# Stop-loss order: Sell 0.01 BTC if price drops to 32,000 (stop) 
# and execute the sell at 31,500 (limit)
python src/bot.py stop_limit BTCUSDT SELL 0.01 32000 31500

# Entry order: Buy 0.01 BTC if price drops to 32,000 (stop)
# and execute at 31,500 (limit)
python src/bot.py stop_limit BTCUSDT BUY 0.01 32000 31500
```

**Use Cases:**
- Risk management with automatic stop losses
- Entry on dips using stop triggers
- Precise exit prices

#### OCO Orders (One-Cancels-the-Other)

```bash
# OCO order: Buy 0.01 BTC, set take-profit at 40,000 and stop-loss at 32,000
# When either hits, the other automatically cancels
python src/bot.py oco BTCUSDT BUY 0.01 40000 32000
```

**How it works:**
1. Opens position with buy order
2. Places take-profit limit order at 40,000
3. Places stop-loss order at 32,000
4. Whichever fills first cancels the other
5. Perfect for hands-off trading

**Use Cases:**
- Automated profit taking
- Risk management (automatic stop loss)
- No need to monitor position constantly

#### TWAP Orders (Time-Weighted Average Price)

```bash
# Split 1 BTC order into 10 slices, execute every 30 seconds
python src/bot.py twap BTCUSDT BUY 1.0 --slices 10 --interval 30

# Custom: 20 slices over 5 minutes (15 second intervals)
python src/bot.py twap BTCUSDT SELL 2.0 --slices 20 --interval 15
```

**How it works:**
1. Splits large order into smaller chunks
2. Executes chunks at regular time intervals
3. Reduces market impact and achieves average price
4. Prevents large price slippage

**Use Cases:**
- Executing large orders without moving market
- Minimizing market impact
- Averaging entry/exit prices
- Stealth execution

#### Grid Trading

```bash
# Create grid from 30,000 to 40,000 with 10 levels
# Total 1 BTC deployed across all levels
python src/bot.py grid BTCUSDT BUY 1.0 40000 30000 --levels 10

# For a sell grid (shorting)
python src/bot.py grid BTCUSDT SELL 1.0 40000 30000 --levels 15
```

**How it works:**
1. Divides price range into equal levels
2. Places buy orders below, sell orders above
3. As price oscillates, orders execute
4. Each buy-sell pair locks in profit
5. Fully automated, no monitoring needed

**Use Cases:**
- Ranging (sideways) markets
- Passive income from volatility
- No directional bias needed
- Highly volatile altcoins

**Grid Example:**
- Price range: 30,000 - 40,000
- 10 levels = 1,000 USDT per level
- Buy at: 30,000, 31,000, 32,000... 38,000
- Sell at: 31,000, 32,000, 33,000... 40,000
- Each cycle locks in ~1% profit per level

## 📊 Logging

All trading activities are logged to `logs/bot.log` with the following information:

- **Order placements**: Order ID, type, symbol, quantity, price
- **Order executions**: Filled quantity, average price, execution time
- **Errors**: Detailed error messages with stack traces
- **API calls**: Request/response details for debugging

View logs:
```bash
# Real-time log monitoring
tail -f logs/bot.log

# Search for specific orders
grep "BTCUSDT" logs/bot.log

# View only errors
grep "ERROR" logs/bot.log
```

## ⚙️ Configuration

Edit `src/config.py` to customize:

```python
# API Configuration
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")

# Trading Parameters
DEFAULT_LEVERAGE = 1
MAX_LEVERAGE = 125
DEFAULT_POSITION_MODE = "One-way"

# Validation
MIN_NOTIONAL = 10  # Minimum order value in USDT
PRICE_PRECISION = 4  # Decimal places for prices
QUANTITY_PRECISION = 3  # Decimal places for quantity

# Grid Trading
GRID_MAX_LEVELS = 100
GRID_MIN_LEVELS = 2

# TWAP
TWAP_MIN_INTERVAL = 1  # Minimum 1 second
TWAP_MAX_INTERVAL = 3600  # Maximum 1 hour
```

## 🔒 Security Best Practices

1. **Never commit `.env` file**
   ```bash
   echo ".env" >> .gitignore
   ```

2. **Use API Key Restrictions** (Highly Recommended)
   - Enable IP Whitelisting
   - Restrict to Futures Trading only
   - Disable Withdrawal permissions
   - Set spending limits

3. **Use Testnet First**
   - Test all strategies on testnet
   - Verify order logic before live trading
   - Paper trade to validate strategies

4. **Start Small**
   - Begin with tiny position sizes
   - Test each order type individually
   - Scale up gradually after successful testing

## 🧪 Testing & Validation

### Test Market Order
```bash
python src/bot.py market_buy BTCUSDT 0.001
```

### Test Limit Order
```bash
python src/bot.py limit_buy BTCUSDT 0.001 1000
```

### Test Stop-Limit
```bash
python src/bot.py stop_limit BTCUSDT BUY 0.001 1000 999
```

### Check Logs
```bash
tail -n 50 logs/bot.log
```

## 🚨 Error Handling

The bot includes robust error handling:

- **Validation Errors**: Invalid inputs are caught before API calls
- **API Errors**: Binance API errors are logged and displayed clearly
- **Rate Limiting**: Automatic rate limit management
- **Network Errors**: Graceful handling of connection failures
- **Partial Fills**: Handles market slippage and partial order fills

All errors are logged with full context for debugging.

## 📝 Examples

### Example 1: Simple Buy & Sell

```bash
# Buy 0.01 BTC at market
python src/bot.py market_buy BTCUSDT 0.01

# Check price
python src/bot.py price BTCUSDT

# Sell 0.01 BTC at limit price
python src/bot.py limit_sell BTCUSDT 0.01 40000
```

### Example 2: Automated Risk Management (OCO)

```bash
# Open position with automatic profit taking and stop loss
# Buy 0.5 BTC
# If price goes to 42,000 → Sell (take profit)
# If price drops to 32,000 → Sell (stop loss)
python src/bot.py oco BTCUSDT BUY 0.5 42000 32000
```

### Example 3: Large Order Execution (TWAP)

```bash
# Need to buy 10 BTC without moving market
# Split into 20 orders of 0.5 BTC each
# Execute every 20 seconds
python src/bot.py twap BTCUSDT BUY 10 --slices 20 --interval 20
```

### Example 4: Ranging Market (Grid)

```bash
# BTC trading between 35,000 and 45,000
# Deploy 2 BTC as grid across 20 levels
# Each buy-sell cycle locks in profit
python src/bot.py grid BTCUSDT BUY 2.0 45000 35000 --levels 20
```

## 🔧 Troubleshooting

### Issue: "Invalid API Key"
**Solution**: Verify API key and secret in `.env` file are correct

### Issue: "Insufficient Balance"
**Solution**: Add balance to Binance account or reduce order size

### Issue: "Order validation failed"
**Solution**: 
- Check order size meets minimum notional (10 USDT)
- Verify price precision (4 decimal places)
- Check quantity precision (3 decimal places)

### Issue: "Rate limit exceeded"
**Solution**: Bot has built-in rate limiting, but wait a moment before retrying

### Issue: No logs appearing
**Solution**: Check `logs/` directory exists and is writable

## 📚 Additional Resources

- **Binance Futures API Docs**: https://binance-docs.github.io/apidocs/futures/en/
- **Binance Testnet**: https://testnet.binancefuture.com
- **API Rate Limits**: https://binance-docs.github.io/apidocs/futures/en/#limits
- **Order Types**: https://binance-docs.github.io/apidocs/futures/en/#new-order-trade

## 🤝 Contributing

Suggestions for improvements:
- Additional order types (Iceberg, Post-Only)
- Risk management features
- Performance metrics dashboard
- Webhook support for alerts

## 📄 License

This project is provided as-is for educational purposes.

## ⚠️ Disclaimer

**Trading cryptocurrency carries risk. This bot is provided for educational purposes.**

- **Start on Testnet**: Always test on testnet first
- **Small Position Sizes**: Begin with minimal amounts
- **Understand Order Types**: Know what each order does before using
- **Monitor Activity**: Don't run unattended in production without safeguards
- **Risk Management**: Always use stop losses with real money

## 🆘 Support

For issues or questions:
1. Check `logs/bot.log` for error details
2. Review API documentation
3. Test on testnet first
4. Verify API key permissions
5. Check account balance and leverage

---

**Happy Trading! Remember: Risk management is more important than profits.**

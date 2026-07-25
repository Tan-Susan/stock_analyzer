# StockAnalyzer

A multi-agent US stock analysis engine. Technical and fundamental analysis agents run in parallel, producing buy/sell/hold signals via weighted voting, complete with target price, stop-loss, and actionable recommendations.

**简体中文** | [English](README_EN.md)

---

## Quick Start

### 1. Clone and Install

<details>
<summary><b>Windows</b></summary>

```powershell
git clone https://github.com/Tan-Susan/stock_analyzer.git
cd stock_analyzer
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -e .
```

</details>

<details>
<summary><b>macOS / Linux</b></summary>

```bash
git clone https://github.com/Tan-Susan/stock_analyzer.git
cd stock_analyzer
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

</details>

> `pip install -e .` installs in editable mode and pulls all dependencies from `requirements.txt` and `pyproject.toml`.

### 2. Configure API Key

The project uses [Alpha Vantage](https://www.alphavantage.co/support/#api-key) as its data source (free signup, 25 calls/day).

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
ALPHA_VANTAGE_API_KEY=your_key_here
```

Everything else is optional:

```env
# LLM-assisted analysis (optional)
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://api.openai.com/v1

# Investment preferences (optional)
DEFAULT_INVESTMENT_AMOUNT=10000
RISK_TOLERANCE=moderate  # conservative / moderate / aggressive
```

### 3. Analyze Stocks

**Command line (simplest):**

```bash
python analyze.py AAPL            # single stock
python analyze.py AAPL TSLA NVDA   # batch
python analyze.py                 # interactive input
```

**Python API:**

```python
from stock_analyzer import StockAnalyzerEngine

engine = StockAnalyzerEngine()

# Single stock
result = engine.analyze("AAPL")
print(result["decision"]["signal_type"])   # buy / sell / hold
print(result["decision"]["confidence"])    # confidence %
print(result["decision"]["reasoning"])     # detailed reasoning

# Batch analysis
batch = engine.analyze_batch(["AAPL", "GOOGL", "MSFT"])
for symbol, confidence in batch["recommendations"]["buy"]:
    print(f"{symbol}: buy signal, confidence {confidence:.1f}%")
```

**Web API:**

<details>
<summary><b>Windows</b></summary>

```powershell
pip install -e ".[api]"
uvicorn stock_analyzer.api.server:create_app --factory --host 0.0.0.0 --port 8000
```

</details>

<details>
<summary><b>macOS / Linux</b></summary>

```bash
pip install -e ".[api]"
uvicorn stock_analyzer.api.server:create_app --factory --host 0.0.0.0 --port 8000
```

</details>

Available endpoints:

```
POST /analyze             Analyze a single stock
POST /analyze/batch        Batch analysis
POST /portfolio/analyze     Portfolio analysis
GET  /market/overview      Market overview
POST /backtest             Strategy backtesting
GET  /health               Health check
```

Example:

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL"}'
```

---

## Output Reference

| Field | Description |
|-------|-------------|
| `signal_type` | `buy` / `sell` / `hold` |
| `confidence` | 0-100 confidence score |
| `target_price` | Suggested target price |
| `stop_loss` | Suggested stop-loss price |
| `reasoning` | Detailed weighted-vote reasoning from all agents |
| `operation_guide` | Actionable trade recommendations (position sizing, stop-loss) |

---

## Agent Architecture

```
  Technical Agent (40%)          Fundamental Agent (40%)
  MACD / RSI / Bollinger /        PE / PB / ROE /
  KDJ / MA / OBV / ATR            Revenue Growth / Margins /
  DMI / CCI / WR / PSY             Debt Ratio / Cash Flow
          \                         /
           \                       /
            --- Weighted Coordinator ---
                    |
              ML Predictor (20%)
              Random Forest + MLP
                    |
            Operation Guide Agent
           (position sizing & risk control)
```

---

## Project Structure

```
stock_analyzer/
  agents/       Agents (technical, fundamental, ML predictor, operation guide)
  core/         Data fetching (Alpha Vantage), analyzers, main engine
  api/          FastAPI service
  config/       Configuration
  ml/           ML prediction models
examples/       Example scripts
tests/          Test suite
```

---

## Development

```bash
pytest tests/ -v
pip install -e ".[dev]" && black stock_analyzer/
```

## Disclaimer

This project is for educational and research purposes only. It does not constitute any investment advice. Invest at your own risk.

## License

[MIT](LICENSE)

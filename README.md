# StockAnalyzer

基于多智能体协作的美股智能分析引擎。技术分析智能体和基本面分析智能体并行分析，通过加权投票生成买入/卖出/观望信号，并附带目标价、止损位和操作建议。

[English](README_EN.md) | **简体中文**

---

## 快速开始

### 1. 克隆并安装

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

> `pip install -e .` 会以开发模式安装，同时自动安装 `requirements.txt` 和 `pyproject.toml` 中的依赖。

### 2. 配置 API Key

项目使用 [Alpha Vantage](https://www.alphavantage.co/support/#api-key) 作为数据源（免费注册即可，每日 25 次调用）。

```bash
cp .env.example .env
```

编辑 `.env`，至少填入一行：

```env
ALPHA_VANTAGE_API_KEY=your_key_here
```

其余配置项均为可选项：

```env
# LLM 辅助分析（可选）
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://api.openai.com/v1

# 投资偏好（可选）
DEFAULT_INVESTMENT_AMOUNT=10000
RISK_TOLERANCE=moderate  # conservative / moderate / aggressive
```

### 3. 分析股票

**命令行（最简单）：**

```bash
python analyze.py AAPL            # 分析单只
python analyze.py AAPL TSLA NVDA   # 批量分析
python analyze.py                 # 交互式输入
```

**Python 代码：**

```python
from stock_analyzer import StockAnalyzerEngine

engine = StockAnalyzerEngine()

# 单只分析
result = engine.analyze("AAPL")
print(result["decision"]["signal_type"])   # buy / sell / hold
print(result["decision"]["confidence"])    # 置信度百分比
print(result["decision"]["reasoning"])     # 决策理由

# 批量分析
batch = engine.analyze_batch(["AAPL", "GOOGL", "MSFT"])
for symbol, confidence in batch["recommendations"]["buy"]:
    print(f"{symbol}: 买入信号 置信度 {confidence:.1f}%")
```

**Web API：**

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

启动后访问：

```
POST /analyze       单只股票分析
POST /analyze/batch  批量分析
POST /portfolio/analyze  组合分析
GET  /market/overview   市场概览
GET  /health         健康检查
```

示例：

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL"}'
```

---

## 输出说明

| 字段 | 说明 |
|------|------|
| `signal_type` | `buy` / `sell` / `hold` |
| `confidence` | 0-100 置信度 |
| `target_price` | 建议目标价 |
| `stop_loss` | 建议止损价 |
| `reasoning` | 各智能体加权投票的详细理由 |
| `operation_guide` | 具体操作建议（仓位、止损策略等） |

---

## 智能体架构

```
  技术分析智能体 (40%)          基本面分析智能体 (40%)
  MACD / RSI / 布林带 /         PE / PB / ROE /
  KDJ / 均线 / OBV / ATR        营收增长 / 毛利率 /
  DMI / CCI / WR / PSY          负债率 / 现金流
          \                         /
           \                       /
            --- 加权投票协调器 ---
                    |
              ML 预测智能体 (20%)
              随机森林 + MLP
                    |
            操作指导智能体
           （生成仓位和风控建议）
```

---

## 项目结构

```
stock_analyzer/
  agents/       智能体（技术分析、基本面分析、ML预测、操作指导）
  core/         数据获取（Alpha Vantage）、分析器、主引擎
  api/          FastAPI 服务
  config/       配置管理
  ml/           机器学习预测模型
examples/       示例脚本
tests/          测试用例
```

---

## 开发

```bash
pytest tests/ -v
pip install -e ".[dev]" && black stock_analyzer/
```

## 免责声明

本项目仅供教育和研究目的，不构成任何投资建议。投资有风险，入市需谨慎。

## 许可证

[MIT](LICENSE)

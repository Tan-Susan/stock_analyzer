"""
在 cmd 里运行: python tests/diagnose_mu.py
精确定位 analyze("MU") 每一步的状态
"""
import sys, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 60)
print("MU 分析诊断 - 逐步排查")
print("=" * 60)

# 第1步: 确认 API Key
print("\n[1] 检查 Twelve Data API Key")
from stock_analyzer.config.settings import get_settings
key = get_settings().twelve_data_api_key
if key and key != "03c67d13497049d58c5f03a129020b17":
    print(f"  OK - key: {key[:8]}...{key[-4:]}")
else:
    print(f"  错误 - key 无效或未配置: {key}")

# 第2步: 直接测试 Twelve Data (绕过所有项目代码)
print("\n[2] 直接调 Twelve Data API (requests)")
import requests
try:
    r = requests.get("https://api.twelvedata.com/time_series",
        params={"symbol":"MU","interval":"1day","apikey":key,"outputsize":1,"format":"JSON"},
        timeout=15)
    print(f"  HTTP {r.status_code}")
    if r.status_code == 429:
        print(f"  >>> Twelve Data 限流! 这就是原因")
    elif r.json().get("status") == "error":
        print(f"  >>> API 错误: {r.json().get('message')}")
    else:
        print(f"  OK - 返回 {len(r.json().get('values',[]))} 条")
except Exception as e:
    print(f"  异常: {e}")

# 第3步: 直接测试 yfinance
print("\n[3] 直接调 yfinance (绕过所有项目代码)")
try:
    import yfinance as yf
    info = yf.Ticker("MU").info
    name = info.get("shortName", "N/A")
    print(f"  OK - {name}")
except Exception as e:
    err_msg = str(e)
    print(f"  失败: {err_msg[:200]}")
    if "Too Many" in err_msg or "Rate limit" in err_msg or "429" in err_msg:
        print(f"  >>> yfinance 限流! 这就是原因")

# 第4步: 测试项目 DataFetcher.get_stock_data
print("\n[4] DataFetcher.get_stock_data('MU')")
from stock_analyzer.core.data_fetcher import DataFetcher
fetcher = DataFetcher()
try:
    df = fetcher.get_stock_data("MU", period="1mo")
    print(f"  OK - {len(df)} 行")
except Exception as e:
    print(f"  失败: {e}")
    traceback.print_exc()

# 第5步: 测试项目 DataFetcher.get_stock_info
print("\n[5] DataFetcher.get_stock_info('MU')  <-- 你看到的报错来自这里")
try:
    info = fetcher.get_stock_info("MU")
    if "error" in info:
        print(f"  失败(但有返回): {info.get('error','')}")
    else:
        print(f"  OK - {info.get('name')}")
except Exception as e:
    print(f"  失败: {e}")

# 第6步: 完整 engine.analyze
print("\n[6] 完整 engine.analyze('MU')")
from stock_analyzer import StockAnalyzerEngine
engine = StockAnalyzerEngine()
result = engine.analyze("MU")
print(f"  success: {result.get('success')}")
if result.get("success"):
    d = result.get("decision", {})
    print(f"  signal: {d.get('signal_type')} confidence: {d.get('confidence')}")
else:
    print(f"  error: {result.get('error')}")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)

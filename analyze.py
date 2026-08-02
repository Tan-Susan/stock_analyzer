<<<<<<< HEAD
"""
StockAnalyzer AI 一键分析工具
用法:
    python analyze.py AAPL        # 分析单只股票
    python analyze.py AAPL TSLA   # 分析多只股票
    python analyze.py             # 交互式输入
"""
import sys
from stock_analyzer import StockAnalyzerEngine


def print_divider(char="=", width=70):
    print(char * width)


def print_section(title):
    print_divider("-", 70)
    print(f"  {title}")
    print_divider("-", 70)


def analyze_stock(symbol: str, engine: StockAnalyzerEngine):
    """分析一只股票并打印完整报告"""
    print_divider("=")
    print(f"  正在分析: {symbol}")
    print_divider("=")

    result = engine.analyze(symbol)

    if not result.get("success"):
        print(f"[错误] 分析失败: {result.get('error', '未知错误')}")
        return

    # 1. 综合决策
    decision = result.get("decision", {})
    signal = decision.get("signal_type", "hold").upper()
    confidence = decision.get("confidence", 0)

    signal_emoji = {"BUY": "🟢 买入", "SELL": "🔴 卖出", "HOLD": "🟡 观望"}.get(signal, "⚪ 未知")

    print_section("综合决策")
    print(f"  信号: {signal_emoji}")
    print(f"  置信度: {confidence:.1f}%")
    print(f"  目标价: {decision.get('target_price') or 'N/A'}")
    print(f"  止损价: {decision.get('stop_loss') or 'N/A'}")

    # 2. 各智能体信号
    print_section("各智能体分析结果")
    signals = result.get("individual_signals", {})
    for name, sig in signals.items():
        emoji = {"buy": "🟢", "sell": "🔴", "hold": "🟡"}.get(sig.signal_type, "⚪")
        print(f"  {emoji} {name}: {sig.signal_type.upper()} (置信度 {sig.confidence:.1f}%)")
        # 提取具体决策依据（以 "-" 开头的行是各指标/维度详情）
        reasoning = sig.reasoning or ""
        detail_lines = [
            line.strip().lstrip("-").strip()
            for line in reasoning.split("\n")
            if line.strip().startswith("-")
        ]
        for line in detail_lines[:4]:
            if len(line) > 90:
                line = line[:87] + "..."
            print(f"      • {line}")
        print()

    # 3. 基本面概览
    print_section("基本面概览")
    info = result.get("stock_info", {})
    print(f"  公司: {info.get('name', symbol)}")
    print(f"  行业: {info.get('sector', 'N/A')} / {info.get('industry', 'N/A')}")
    print(f"  PE:   {info.get('pe_ratio') or 'N/A'}")
    print(f"  PB:   {info.get('pb_ratio') or 'N/A'}")
    print(f"  ROE:  {info.get('roe') or 'N/A'}")
    print(f"  毛利率: {info.get('gross_margins') or 'N/A'}")
    print(f"  营收增长: {info.get('revenue_growth') or 'N/A'}")
    print(f"  数据源: {info.get('data_source', 'N/A')}")

    # 4. 操作指导
    print_section("操作指导")
    guide_text = result.get("operation_guide_text", "")
    for line in guide_text.split("\n"):
        if line.strip():
            print(f"  {line}")

    print_divider("=")
    print()


def main():
    # 初始化引擎（只初始化一次）
    print("正在初始化 StockAnalyzer AI 引擎...")
    engine = StockAnalyzerEngine()
    print("引擎就绪！\n")

    if len(sys.argv) > 1:
        # 命令行参数模式: python analyze.py AAPL TSLA
        symbols = sys.argv[1:]
    else:
        # 交互式模式
        user_input = input("请输入股票代码（多个用空格分隔，输入 q 退出）: ").strip()
        if user_input.lower() in ("q", "quit", "exit"):
            print("再见！")
            return
        symbols = user_input.split()

    if not symbols:
        print("未输入股票代码，退出。")
        return

    for symbol in symbols:
        symbol = symbol.strip().upper()
        if not symbol:
            continue
        try:
            analyze_stock(symbol, engine)
        except Exception as e:
            print(f"[错误] 分析 {symbol} 时出错: {e}\n")

    print("分析完成！")


if __name__ == "__main__":
    main()
=======
"""
StockAnalyzer AI 一键分析工具
用法:
    python analyze.py AAPL        # 分析单只股票
    python analyze.py AAPL TSLA   # 分析多只股票
    python analyze.py             # 交互式输入
"""
import sys
from stock_analyzer import StockAnalyzerEngine


def print_divider(char="=", width=70):
    print(char * width)


def print_section(title):
    print_divider("-", 70)
    print(f"  {title}")
    print_divider("-", 70)


def analyze_stock(symbol: str, engine: StockAnalyzerEngine):
    """分析一只股票并打印完整报告"""
    print_divider("=")
    print(f"  正在分析: {symbol}")
    print_divider("=")

    result = engine.analyze(symbol)

    if not result.get("success"):
        print(f"[错误] 分析失败: {result.get('error', '未知错误')}")
        return

    # 1. 综合决策
    decision = result.get("decision", {})
    signal = decision.get("signal_type", "hold").upper()
    confidence = decision.get("confidence", 0)

    signal_emoji = {"BUY": "🟢 买入", "SELL": "🔴 卖出", "HOLD": "🟡 观望"}.get(signal, "⚪ 未知")

    print_section("综合决策")
    print(f"  信号: {signal_emoji}")
    print(f"  置信度: {confidence:.1f}%")
    print(f"  目标价: {decision.get('target_price') or 'N/A'}")
    print(f"  止损价: {decision.get('stop_loss') or 'N/A'}")

    # 2. 各智能体信号
    print_section("各智能体分析结果")
    signals = result.get("individual_signals", {})
    for name, sig in signals.items():
        emoji = {"buy": "🟢", "sell": "🔴", "hold": "🟡"}.get(sig.signal_type, "⚪")
        print(f"  {emoji} {name}: {sig.signal_type.upper()} (置信度 {sig.confidence:.1f}%)")
        # 提取具体决策依据（以 "-" 开头的行是各指标/维度详情）
        reasoning = sig.reasoning or ""
        detail_lines = [
            line.strip().lstrip("-").strip()
            for line in reasoning.split("\n")
            if line.strip().startswith("-")
        ]
        for line in detail_lines[:4]:
            if len(line) > 90:
                line = line[:87] + "..."
            print(f"      • {line}")
        print()

    # 3. 基本面概览
    print_section("基本面概览")
    info = result.get("stock_info", {})
    print(f"  公司: {info.get('name', symbol)}")
    print(f"  行业: {info.get('sector', 'N/A')} / {info.get('industry', 'N/A')}")
    print(f"  PE:   {info.get('pe_ratio') or 'N/A'}")
    print(f"  PB:   {info.get('pb_ratio') or 'N/A'}")
    print(f"  ROE:  {info.get('roe') or 'N/A'}")
    print(f"  毛利率: {info.get('gross_margins') or 'N/A'}")
    print(f"  营收增长: {info.get('revenue_growth') or 'N/A'}")
    print(f"  数据源: {info.get('data_source', 'N/A')}")

    # 4. 操作指导
    print_section("操作指导")
    guide_text = result.get("operation_guide_text", "")
    for line in guide_text.split("\n"):
        if line.strip():
            print(f"  {line}")

    print_divider("=")
    print()


def main():
    # 初始化引擎（只初始化一次）
    print("正在初始化 StockAnalyzer AI 引擎...")
    engine = StockAnalyzerEngine()
    print("引擎就绪！\n")

    if len(sys.argv) > 1:
        # 命令行参数模式: python analyze.py AAPL TSLA
        symbols = sys.argv[1:]
    else:
        # 交互式模式
        user_input = input("请输入股票代码（多个用空格分隔，输入 q 退出）: ").strip()
        if user_input.lower() in ("q", "quit", "exit"):
            print("再见！")
            return
        symbols = user_input.split()

    if not symbols:
        print("未输入股票代码，退出。")
        return

    for symbol in symbols:
        symbol = symbol.strip().upper()
        if not symbol:
            continue
        try:
            analyze_stock(symbol, engine)
        except Exception as e:
            print(f"[错误] 分析 {symbol} 时出错: {e}\n")

    print("分析完成！")


if __name__ == "__main__":
    main()
>>>>>>> 9499a60678460588353065030d55c19c2df72747

"""
StockAnalyzer AI 快速入门示例
"""
from stock_analyzer import StockAnalyzerEngine


def analyze_single_stock():
    """分析单只股票"""
    print("=" * 60)
    print("示例1: 分析单只股票")
    print("=" * 60)

    # 初始化引擎
    engine = StockAnalyzerEngine()

    # 分析苹果股票
    result = engine.analyze("AAPL")

    if result["success"]:
        print(f"\n📊 股票代码: {result['symbol']}")
        print(f"🎯 综合建议: {result['decision']['signal_type'].upper()}")
        print(f"🎉 置信度: {result['decision']['confidence']}%")

        if result["decision"]["target_price"]:
            print(f"🎯 目标价: ${result['decision']['target_price']}")
        if result["decision"]["stop_loss"]:
            print(f"🛑 止损价: ${result['decision']['stop_loss']}")

        print(f"\n💡 决策理由:\n{result['decision']['reasoning']}")

        # 打印各智能体信号
        print("\n🔍 各智能体分析结果:")
        for agent_name, signal in result["individual_signals"].items():
            emoji = "🟢" if signal.signal_type == "buy" else "🔴" if signal.signal_type == "sell" else "🟡"
            print(f"  {emoji} {agent_name}: {signal.signal_type.upper()} (置信度: {signal.confidence}%)")
    else:
        print(f"❌ 分析失败: {result['error']}")


def analyze_multiple_stocks():
    """批量分析多只股票"""
    print("\n" + "=" * 60)
    print("示例2: 批量分析多只股票")
    print("=" * 60)

    engine = StockAnalyzerEngine()

    # 分析科技巨头
    symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "META"]
    batch_result = engine.analyze_batch(symbols)

    print(f"\n📊 分析完成: {batch_result['summary']['success']}/{batch_result['summary']['total']} 只股票")

    # 打印买入推荐
    if batch_result["recommendations"]["buy"]:
        print("\n🟢 买入推荐 (按置信度排序):")
        for symbol, confidence in batch_result["recommendations"]["buy"]:
            print(f"  • {symbol}: 置信度 {confidence}%")

    # 打印卖出推荐
    if batch_result["recommendations"]["sell"]:
        print("\n🔴 卖出推荐 (按置信度排序):")
        for symbol, confidence in batch_result["recommendations"]["sell"]:
            print(f"  • {symbol}: 置信度 {confidence}%")

    # 打印观望推荐
    if batch_result["recommendations"]["hold"]:
        print("\n🟡 观望推荐:")
        for symbol, confidence in batch_result["recommendations"]["hold"]:
            print(f"  • {symbol}: 置信度 {confidence}%")


def market_overview():
    """获取市场概览"""
    print("\n" + "=" * 60)
    print("示例3: 市场概览")
    print("=" * 60)

    engine = StockAnalyzerEngine()
    overview = engine.get_market_overview()

    if overview["success"]:
        print("\n🌐 全球市场指数:")
        for symbol, data in overview["indices"].items():
            emoji = "🟢" if data["change_pct"] > 0 else "🔴"
            print(f"  {emoji} {symbol}: {data['price']:.2f} ({data['change_pct']:+.2f}%)")
    else:
        print(f"❌ 获取市场概览失败: {overview.get('error')}")


def portfolio_analysis():
    """投资组合分析"""
    print("\n" + "=" * 60)
    print("示例4: 投资组合分析")
    print("=" * 60)

    engine = StockAnalyzerEngine()

    # 模拟持仓
    holdings = [
        {"symbol": "AAPL", "quantity": 100, "cost_basis": 150.0},
        {"symbol": "GOOGL", "quantity": 50, "cost_basis": 100.0},
        {"symbol": "MSFT", "quantity": 75, "cost_basis": 300.0},
    ]

    portfolio = engine.get_portfolio_analysis(holdings)

    print(f"\n💼 投资组合总览:")
    print(f"  总市值: ${portfolio['total_value']:,.2f}")
    print(f"  总盈亏: ${portfolio['total_gain_loss']:,.2f}")
    print(f"  收益率: {portfolio['return_pct']:.2f}%")

    print(f"\n📊 持仓分析:")
    for holding in portfolio["holdings"]:
        symbol = holding["symbol"]
        decision = holding["decision"]
        signal = decision.get("signal_type", "hold").upper()
        emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "🟡"
        print(f"  {emoji} {symbol}: {signal} (置信度: {decision.get('confidence', 0)}%)")


if __name__ == "__main__":
    print("🚀 StockAnalyzer AI 快速入门示例")
    print("=" * 60)

    try:
        analyze_single_stock()
        analyze_multiple_stocks()
        market_overview()
        portfolio_analysis()

        print("\n" + "=" * 60)
        print("✅ 所有示例运行完成")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()

"""
StockAnalyzer AI - 基于多智能体的个人财富管理与投资决策引擎

StockAnalyzer AI 是一款开源的智能投资分析工具，通过多智能体协作系统
为个人投资者提供专业的技术分析、基本面分析和市场情绪分析。

Example:
    >>> from stock_analyzer import StockAnalyzerEngine
    >>> engine = StockAnalyzerEngine()
    >>> result = engine.analyze("AAPL")
    >>> print(result['decision']['signal_type'])
    'buy'
"""

__version__ = "0.1.0"
__author__ = "StockAnalyzer Team"
__license__ = "MIT"

from stock_analyzer.core.engine import StockAnalyzerEngine, batch_analyze, quick_analyze

__all__ = [
    "StockAnalyzerEngine",
    "quick_analyze",
    "batch_analyze",
]

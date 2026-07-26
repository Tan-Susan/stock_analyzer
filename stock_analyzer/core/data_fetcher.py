"""
数据获取模块 - 基于 Alpha Vantage 获取美股数据
"""
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests
from stock_analyzer.config.settings import get_settings

logger = logging.getLogger(__name__)


def safe_float(val) -> float:
    """安全将值转为 float, None/空字符串/无效值返回 0"""
    if val is None or val == "" or val == "None":
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


class AlphaVantageDataSource:
    """Alpha Vantage 数据源 - 提供美股历史行情和基本面数据

    免费版: 25次/天, 注册: https://www.alphavantage.co/support/#api-key
    提供 TIME_SERIES_DAILY (历史K线) 和 OVERVIEW (公司基本面) 端点
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_stock_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """
        获取美股历史K线数据 (TIME_SERIES_DAILY 端点)

        Args:
            symbol: 股票代码 (如: AAPL)
            period: 时间周期 (1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: 时间间隔 (1d, 1wk, 1mo)

        Returns:
            DataFrame包含OHLCV数据
        """
        interval_map = {
            "1d": "TIME_SERIES_DAILY",
            "1wk": "TIME_SERIES_WEEKLY",
            "1mo": "TIME_SERIES_MONTHLY",
        }
        function = interval_map.get(interval, "TIME_SERIES_DAILY")

        params = {
            "function": function,
            "symbol": symbol,
            "apikey": self.api_key,
            "outputsize": "full",
        }

        try:
            logger.info(f"从 Alpha Vantage 获取历史数据: {symbol}")
            response = requests.get(self.BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            if "Error Message" in data or "Note" in data:
                err = data.get("Note", data.get("Error Message", "Unknown"))
                raise ValueError(f"Alpha Vantage API 错误: {err}")

            time_series_key = next(
                (k for k in data.keys() if "Time Series" in k), None
            )
            if not time_series_key:
                raise ValueError(f"无法获取 {symbol} 的历史数据")

            time_series = data[time_series_key]
            rows = []
            for date_str, values in time_series.items():
                rows.append({
                    "Date": pd.to_datetime(date_str),
                    "Open": float(values.get("1. open", 0)),
                    "High": float(values.get("2. high", 0)),
                    "Low": float(values.get("3. low", 0)),
                    "Close": float(values.get("4. close", 0)),
                    "Volume": int(float(values.get("5. volume", 0))),
                })

            df = pd.DataFrame(rows)
            df = df.set_index("Date")
            df = df.sort_index()

            period_days = self._parse_period_to_days(period)
            if period_days:
                cutoff = datetime.now() - timedelta(days=period_days)
                df = df[df.index >= cutoff]

            return df
        except Exception as e:
            logger.error(f"从 Alpha Vantage 获取 {symbol} 历史数据失败: {e}")
            raise

    @staticmethod
    def _parse_period_to_days(period: str) -> int:
        mapping = {
            "1mo": 30, "3mo": 90, "6mo": 180,
            "1y": 365, "2y": 730, "5y": 1825, "10y": 3650,
            "ytd": datetime.now().timetuple().tm_yday,
            "max": 3650,
        }
        return mapping.get(period, 365)

    def get_company_overview(self, symbol: str) -> Dict:
        """获取公司基本面概览 (OVERVIEW 端点)"""
        params = {
            "function": "OVERVIEW",
            "symbol": symbol,
            "apikey": self.api_key,
        }
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            if "Error Message" in data or "Note" in data:
                return {}
            return data
        except Exception:
            return {}

    def get_stock_info(self, symbol: str) -> Dict:
        """
        获取股票基本信息 - 合并基本面和估值数据

        Args:
            symbol: 股票代码 (如: AAPL)

        Returns:
            股票信息字典
        """
        overview = self.get_company_overview(symbol)

        if not overview or not overview.get("Symbol"):
            return {
                "symbol": symbol,
                "name": symbol,
                "error": "未找到股票信息",
            }

        return {
            "symbol": symbol,
            "name": overview.get("Name", symbol),
            "sector": overview.get("Sector", "N/A"),
            "industry": overview.get("Industry", "N/A"),
            "description": overview.get("Description", "N/A"),
            "website": "N/A",
            "exchange": overview.get("Exchange", "N/A"),

            # 估值指标
            "market_cap": safe_float(overview.get("MarketCapitalization")),
            "pe_ratio": safe_float(overview.get("PERatio")),
            "forward_pe": safe_float(overview.get("ForwardPE")),
            "peg_ratio": safe_float(overview.get("PEGRatio")),
            "pb_ratio": safe_float(overview.get("PriceToBookRatio")),
            "ps_ratio": safe_float(overview.get("PriceToSalesRatioTTM")),
            "ev_to_ebitda": safe_float(overview.get("EVToEBITDA")),
            "dividend_yield": safe_float(overview.get("DividendYield")),

            # 盈利能力指标
            "roe": safe_float(overview.get("ReturnOnEquityTTM")),
            "roa": safe_float(overview.get("ReturnOnAssetsTTM")),
            "gross_margins": safe_float(overview.get("GrossProfitMarginTTM")),
            "profit_margins": safe_float(overview.get("OperatingMarginTTM")),
            "net_margins": safe_float(overview.get("NetProfitMarginTTM")),

            # 成长指标
            "revenue_growth": safe_float(overview.get("QuarterlyRevenueGrowthYOY")),
            "earnings_growth": safe_float(overview.get("QuarterlyEarningsGrowthYOY")),
            "eps": safe_float(overview.get("EPS")),

            # 财务健康指标
            "debt_to_equity": safe_float(overview.get("DebtToEquity")),
            "current_ratio": safe_float(overview.get("CurrentRatio")),
            "free_cashflow": safe_float(overview.get("FreeCashFlow")),
            "operating_cashflow": safe_float(overview.get("OperatingCashFlowTTM")),
            "beta": safe_float(overview.get("Beta")) or 1.0,

            # 行情数据
            "fifty_two_week_high": safe_float(overview.get("52WeekHigh")),
            "fifty_two_week_low": safe_float(overview.get("52WeekLow")),
            "average_volume": safe_float(overview.get("AverageDailyVolume")),
            "analyst_target_price": safe_float(overview.get("AnalystTargetPrice")),

            "data_source": "alpha_vantage",
        }


class DataFetcher:
    """美股金融数据获取器 - 基于 Alpha Vantage"""

    def __init__(self):
        """初始化数据获取器"""
        self.settings = get_settings()
        self.cache_dir = Path(self.settings.data_cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._alpha_vantage = None

    def _get_alpha_vantage(self) -> AlphaVantageDataSource:
        if self._alpha_vantage is None:
            key = self.settings.alpha_vantage_api_key
            if not key:
                raise ValueError(
                    "未配置 Alpha Vantage API Key，请在 .env 中设置 ALPHA_VANTAGE_API_KEY"
                )
            self._alpha_vantage = AlphaVantageDataSource(api_key=key)
        return self._alpha_vantage

    def _fetch_with_retry(self, func, max_retries=3, base_delay=2):
        """带重试的数据获取"""
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                error_msg = str(e)
                if "Too Many Requests" in error_msg or "Rate limited" in error_msg or "429" in error_msg:
                    if attempt < max_retries - 1:
                        delay = base_delay * (attempt + 1)
                        logger.warning(f"请求被限流，{delay}秒后重试 (第{attempt + 1}/{max_retries}次)")
                        time.sleep(delay)
                        continue
                raise

    def get_stock_data(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        获取股票历史数据

        Args:
            symbol: 股票代码 (如: AAPL)
            period: 时间周期
            interval: 时间间隔
            use_cache: 是否使用缓存

        Returns:
            DataFrame包含OHLCV数据
        """
        cache_file = self.cache_dir / f"{symbol}_{period}_{interval}.csv"

        # 优先使用缓存
        if use_cache and cache_file.exists():
            cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - cache_time < timedelta(hours=1):
                logger.info(f"使用缓存数据: {symbol}")
                return pd.read_csv(cache_file, index_col=0, parse_dates=True)

        # 从 Alpha Vantage 获取
        try:
            def _do_fetch():
                return self._get_alpha_vantage().get_stock_data(symbol, period=period, interval=interval)

            data = self._fetch_with_retry(_do_fetch)
            if data.empty:
                raise ValueError(f"无法获取 {symbol} 的数据")
            if use_cache:
                data.to_csv(cache_file)
            return data
        except Exception as av_err:
            logger.warning(f"Alpha Vantage 获取失败: {av_err}")
            # 限流时使用模拟数据
            error_msg = str(av_err)
            if "Too Many Requests" in error_msg or "Rate limited" in error_msg or "429" in error_msg:
                logger.warning(f"API限流，使用模拟数据: {symbol}")
            try:
                from stock_analyzer.core.demo_data import DemoDataGenerator
                generator = DemoDataGenerator()
                data = generator.generate_stock_data(symbol, days=365)
                if not data.empty:
                    return data
            except ImportError:
                pass
            logger.error(f"获取 {symbol} 数据失败: {av_err}")
            raise

    def get_stock_info(self, symbol: str) -> Dict:
        """
        获取股票基本信息

        Args:
            symbol: 股票代码 (如: AAPL)

        Returns:
            股票信息字典
        """
        return self._get_alpha_vantage().get_stock_info(symbol)

    def get_market_indices(self, market: str = "us") -> Dict[str, pd.DataFrame]:
        """
        获取主要美股市场指数数据

        Args:
            market: 市场类型 ('us', 'global')

        Returns:
            dict: {指数名称: DataFrame}
        """
        index_map = {
            "us": {
                "SPY": "S&P 500 ETF",
                "DIA": "Dow Jones ETF",
                "QQQ": "NASDAQ ETF",
            },
            "global": {
                "SPY": "S&P 500 ETF",
                "QQQ": "NASDAQ ETF",
                "EEM": "Emerging Markets",
            },
        }

        symbols = index_map.get(market, index_map["us"])
        results = {}

        for symbol, name in symbols.items():
            try:
                df = self.get_stock_data(symbol, period="1mo", interval="1d")
                if not df.empty:
                    results[name] = df
            except Exception as e:
                logger.debug(f"获取 {name}({symbol}) 失败: {e}")

        return results

    def get_multiple_stocks(
        self,
        symbols: List[str],
        period: str = "1y",
        interval: str = "1d",
    ) -> Dict[str, pd.DataFrame]:
        """
        批量获取多只股票数据

        Args:
            symbols: 股票代码列表
            period: 时间周期
            interval: 时间间隔

        Returns:
            字典，key为股票代码，value为DataFrame
        """
        results = {}
        for i, symbol in enumerate(symbols):
            try:
                results[symbol] = self.get_stock_data(symbol, period=period, interval=interval)
                # 添加延迟避免限流
                if i < len(symbols) - 1:
                    time.sleep(1)
            except Exception as e:
                logger.error(f"获取 {symbol} 数据失败: {e}")
                results[symbol] = pd.DataFrame()
        return results

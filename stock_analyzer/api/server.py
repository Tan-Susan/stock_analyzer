"""
StockAnalyzer AI FastAPI Web 服务
提供股票分析、投资组合分析、市场概览等 RESTful API
"""
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from stock_analyzer.core.engine import StockAnalyzerEngine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic 请求/响应模型
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    symbol: str = Field(..., description="股票代码，如 AAPL")
    include_technical: bool = Field(True, description="是否包含技术分析")
    include_fundamental: bool = Field(True, description="是否包含基本面分析")


class AnalyzeResponse(BaseModel):
    symbol: str
    success: bool
    error: Optional[str] = None
    decision: Optional[Dict[str, Any]] = None
    individual_signals: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    technical_analysis: Optional[Dict[str, Any]] = None
    fundamental_analysis: Optional[Dict[str, Any]] = None
    stock_info: Optional[Dict[str, Any]] = None


class BatchAnalyzeRequest(BaseModel):
    symbols: List[str] = Field(..., description="股票代码列表")


class BatchAnalyzeResponse(BaseModel):
    results: Dict[str, Any]
    recommendations: Dict[str, List]
    summary: Dict[str, Any]


class Holding(BaseModel):
    symbol: str = Field(..., description="股票代码")
    quantity: float = Field(..., description="持仓数量")
    cost_basis: float = Field(0.0, description="成本价")


class PortfolioAnalyzeRequest(BaseModel):
    holdings: List[Holding] = Field(..., description="持仓列表")


class PortfolioAnalyzeResponse(BaseModel):
    holdings: List[Dict[str, Any]]
    total_value: float
    total_gain_loss: float
    return_pct: float


class MarketOverviewResponse(BaseModel):
    success: bool
    indices: Dict[str, Any]
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# 依赖注入
# ---------------------------------------------------------------------------

_engine: Optional[StockAnalyzerEngine] = None


def get_engine() -> StockAnalyzerEngine:
    """获取全局 StockAnalyzerEngine 实例（单例）"""
    global _engine
    if _engine is None:
        _engine = StockAnalyzerEngine()
    return _engine


# ---------------------------------------------------------------------------
# 生命周期管理
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期事件"""
    logger.info("StockAnalyzer API 服务启动")
    # 预热引擎
    get_engine()
    yield
    logger.info("StockAnalyzer API 服务关闭")


# ---------------------------------------------------------------------------
# 创建 FastAPI 应用
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用"""
    app = FastAPI(
        title="StockAnalyzer AI API",
        description="智能投资分析 Web API 服务",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------------
    # 路由
    # -----------------------------------------------------------------------

    @app.get("/health", response_model=Dict[str, str])
    async def health_check():
        """健康检查端点"""
        return {"status": "ok", "service": "stock_analyzer-ai"}

    @app.post("/analyze", response_model=AnalyzeResponse)
    async def analyze_stock(
        request: AnalyzeRequest,
        engine: StockAnalyzerEngine = Depends(get_engine),
    ):
        """分析单只股票"""
        try:
            result = engine.analyze(
                symbol=request.symbol,
                include_technical=request.include_technical,
                include_fundamental=request.include_fundamental,
            )
            return AnalyzeResponse(**result)
        except Exception as e:
            logger.error(f"分析 {request.symbol} 失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/analyze/batch", response_model=BatchAnalyzeResponse)
    async def analyze_batch(
        request: BatchAnalyzeRequest,
        engine: StockAnalyzerEngine = Depends(get_engine),
    ):
        """批量分析多只股票"""
        try:
            result = engine.analyze_batch(request.symbols)
            return BatchAnalyzeResponse(**result)
        except Exception as e:
            logger.error(f"批量分析失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/portfolio/analyze", response_model=PortfolioAnalyzeResponse)
    async def analyze_portfolio(
        request: PortfolioAnalyzeRequest,
        engine: StockAnalyzerEngine = Depends(get_engine),
    ):
        """投资组合分析"""
        try:
            holdings = [h.model_dump() for h in request.holdings]
            result = engine.get_portfolio_analysis(holdings)
            return PortfolioAnalyzeResponse(**result)
        except Exception as e:
            logger.error(f"投资组合分析失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/market/overview", response_model=MarketOverviewResponse)
    async def market_overview(
        engine: StockAnalyzerEngine = Depends(get_engine),
    ):
        """获取市场概览"""
        try:
            result = engine.get_market_overview()
            return MarketOverviewResponse(**result)
        except Exception as e:
            logger.error(f"获取市场概览失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return app

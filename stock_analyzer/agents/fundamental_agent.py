"""
基本面分析智能体 - 基于公司基本面数据生成交易信号
"""
from typing import Any, Dict

import pandas as pd

from stock_analyzer.agents.base_agent import AgentSignal, BaseAgent


class FundamentalAgent(BaseAgent):
    """
    基本面分析智能体

    基于公司财务数据、估值指标、成长性等基本面因素
    分析并生成中长期投资建议

    采用多因子评分模型，从盈利能力(30%)、估值(25%)、
    成长(20%)、财务健康+现金流(25%) 四个维度综合评分
    """

    def __init__(self):
        super().__init__(
            name="FundamentalAnalyst",
            description="基于基本面分析生成中长期投资建议"
        )

    def analyze(self, symbol: str, data: Dict[str, Any]) -> AgentSignal:
        """
        基本面分析并生成信号

        Args:
            symbol: 股票代码
            data: 必须包含 'stock_info' (Dict) 和 'historical_data' (DataFrame)

        Returns:
            AgentSignal
        """
        if not self.validate_data(data, ["stock_info", "historical_data"]):
            return AgentSignal(
                agent_name=self.name,
                signal_type="hold",
                confidence=0,
                reasoning="缺少基本面数据，无法进行分析"
            )

        stock_info = data["stock_info"]
        historical_data = data["historical_data"]

        # 四维度多因子评分
        dimension_scores = self._calculate_dimension_scores(stock_info, historical_data)

        # 加权综合评分
        overall_score = (
            dimension_scores["profitability_score"] * 0.30 +
            dimension_scores["valuation_score"] * 0.25 +
            dimension_scores["growth_score"] * 0.20 +
            dimension_scores["financial_health_score"] * 0.25
        )
        overall_score = max(0.0, min(100.0, overall_score))

        # 基于评分生成信号: >=70 buy, <=35 sell, 中间 hold
        if overall_score >= 70:
            signal_type = "buy"
        elif overall_score <= 35:
            signal_type = "sell"
        else:
            signal_type = "hold"

        # 置信度: 数据充分度 + 信号偏离中性的程度
        base_conf = abs(overall_score - 50) * 2
        all_values = [
            dimension_scores.get("roe"), dimension_scores.get("gross_margins"),
            dimension_scores.get("profit_margins"), dimension_scores.get("pe_ratio"),
            dimension_scores.get("pb_ratio"), dimension_scores.get("dividend_yield"),
            dimension_scores.get("return_1m"), dimension_scores.get("return_3m"),
            dimension_scores.get("revenue_growth"), dimension_scores.get("debt_to_equity"),
            dimension_scores.get("current_ratio"),
        ]
        valid_count = sum(1 for v in all_values if v is not None and v != 0)
        total_count = len(all_values)
        data_coverage = valid_count / total_count if total_count > 0 else 0
        data_bonus = data_coverage * 20
        if signal_type == "hold":
            hold_conf = 35 + data_coverage * 25
            confidence = max(base_conf, hold_conf)
        else:
            confidence = base_conf + data_bonus
        confidence = max(20, min(95, confidence))

        # 生成理由
        if signal_type == "buy":
            reasoning = self._generate_buy_reason(overall_score, dimension_scores, stock_info)
        elif signal_type == "sell":
            reasoning = self._generate_sell_reason(overall_score, dimension_scores, stock_info)
        else:
            reasoning = self._generate_hold_reason(overall_score, dimension_scores, stock_info)

        # 计算目标价
        current_price = historical_data["Close"].iloc[-1]
        if signal_type == "buy":
            # 基于综合评分调整目标价幅度
            upside = 0.10 + (overall_score - 70) / 100 * 0.20  # 10%-30%上涨空间
            target_price = current_price * (1 + upside)
            stop_loss = current_price * 0.90
        elif signal_type == "sell":
            downside = 0.10 + (35 - overall_score) / 100 * 0.15  # 10%-25%下跌空间
            target_price = current_price * (1 - downside)
            stop_loss = current_price * 1.10
        else:
            target_price = None
            stop_loss = None

        return AgentSignal(
            agent_name=self.name,
            signal_type=signal_type,
            confidence=round(confidence, 2),
            reasoning=reasoning,
            target_price=round(target_price, 2) if target_price else None,
            stop_loss=round(stop_loss, 2) if stop_loss else None,
            time_horizon="long",
            metadata={
                "overall_score": round(overall_score, 2),
                "profitability_score": round(dimension_scores["profitability_score"], 2),
                "valuation_score": round(dimension_scores["valuation_score"], 2),
                "growth_score": round(dimension_scores["growth_score"], 2),
                "financial_health_score": round(dimension_scores["financial_health_score"], 2),
                "roe": dimension_scores.get("roe"),
                "gross_margins": dimension_scores.get("gross_margins"),
                "profit_margins": dimension_scores.get("profit_margins"),
                "pe_ratio": dimension_scores.get("pe_ratio"),
                "pb_ratio": dimension_scores.get("pb_ratio"),
                "dividend_yield": dimension_scores.get("dividend_yield"),
                "debt_to_equity": dimension_scores.get("debt_to_equity"),
            }
        )

    def _score_metric(self, value, good, bad, reverse=False):
        """
        阈值线性映射评分 0-100

        Args:
            value: 实际值
            good: 优秀阈值
            bad: 较差阈值
            reverse: True表示反向指标(越小越好)
        """
        if value is None or value == 0:
            return 50  # 缺失数据中性分

        if reverse:
            # 反向指标: 值越小分越高
            if value <= good:
                return 100
            if value >= bad:
                return 0
            return (bad - value) / (bad - good) * 100
        else:
            # 正向指标: 值越大分越高
            if value >= good:
                return 100
            if value <= bad:
                return 0
            return (value - bad) / (good - bad) * 100

    def _calculate_dimension_scores(self, stock_info: Dict, historical_data: pd.DataFrame) -> Dict[str, float]:
        """
        计算四维度评分

        Returns:
            包含各维度评分和关键指标值的字典
        """
        # ====== 1. 盈利能力(30%权重) ======
        roe = stock_info.get("returnOnEquity") or stock_info.get("roe", 0)
        gross_margins = stock_info.get("grossMargins", 0)
        profit_margins = stock_info.get("profitMargins", 0)

        roe_score = self._score_metric(roe, good=20, bad=10)
        gross_score = self._score_metric(gross_margins, good=0.40, bad=0.15)
        profit_score = self._score_metric(profit_margins, good=0.20, bad=0.05)

        profitability_score = (roe_score + gross_score + profit_score) / 3

        # ====== 2. 估值(25%权重) ======
        pe = stock_info.get("trailingPE") or stock_info.get("pe_ratio", 0)
        pb = stock_info.get("priceToBook") or stock_info.get("pb_ratio", 0)
        div_yield = stock_info.get("dividendYield", 0)

        pe_score = self._score_metric(pe, good=12, bad=35, reverse=True)
        pb_score = self._score_metric(pb, good=1.5, bad=5, reverse=True)
        div_score = self._score_metric(div_yield, good=0.04, bad=0.005)

        valuation_score = (pe_score + pb_score + div_score) / 3

        # ====== 3. 成长(20%权重) ======
        # 从历史数据计算近1月、近3月涨幅
        close = historical_data["Close"]
        n = len(close)
        if n >= 22:
            return_1m = (close.iloc[-1] - close.iloc[-22]) / close.iloc[-22] * 100
        else:
            return_1m = None

        if n >= 66:
            return_3m = (close.iloc[-1] - close.iloc[-66]) / close.iloc[-66] * 100
        else:
            return_3m = None

        revenue_growth = stock_info.get("revenueGrowth", 0)
        # revenueGrowth 可能是小数形式(如 0.20 表示 20%)，统一转为百分比
        if isinstance(revenue_growth, (int, float)) and abs(revenue_growth) < 1:
            revenue_growth_pct = revenue_growth * 100
        else:
            revenue_growth_pct = revenue_growth

        r1m_score = self._score_metric(return_1m, good=10, bad=-5)
        r3m_score = self._score_metric(return_3m, good=25, bad=-15)
        rev_score = self._score_metric(revenue_growth_pct, good=20, bad=0)

        growth_score = (r1m_score + r3m_score + rev_score) / 3

        # ====== 4. 财务健康+现金流(25%权重) ======
        debt_to_equity = stock_info.get("debtToEquity", 0)
        current_ratio = stock_info.get("currentRatio", 0)
        fcf = stock_info.get("freeCashflow", 0)
        net_income = stock_info.get("netIncome", 0)

        # 资产负债率(debtToEquity): 反向，<30 得100，>80 得0
        dte_score = self._score_metric(debt_to_equity, good=30, bad=80, reverse=True)
        # 流动比率: 正向，>2.5 得100，<1 得0
        cr_score = self._score_metric(current_ratio, good=2.5, bad=1.0)
        # FCF/利润比: 正向指标
        if net_income and net_income != 0 and fcf is not None:
            fcf_ratio = fcf / net_income
            fcf_score = self._score_metric(fcf_ratio, good=1.0, bad=0.3)
        else:
            fcf_score = 50

        financial_health_score = (dte_score + cr_score + fcf_score) / 3

        return {
            "profitability_score": profitability_score,
            "valuation_score": valuation_score,
            "growth_score": growth_score,
            "financial_health_score": financial_health_score,
            # 保存关键指标值供推理使用
            "roe": roe,
            "gross_margins": gross_margins,
            "profit_margins": profit_margins,
            "pe_ratio": pe,
            "pb_ratio": pb,
            "dividend_yield": div_yield,
            "debt_to_equity": debt_to_equity,
            "return_1m": return_1m,
            "return_3m": return_3m,
            "revenue_growth": revenue_growth_pct,
        }

    def _generate_buy_reason(self, overall_score: float, scores: Dict, stock_info: Dict) -> str:
        """生成买入理由"""
        reasons = [f"基本面多因子综合评分 {overall_score:.1f}/100，建议买入:"]

        # 盈利能力亮点
        if scores["profitability_score"] >= 70:
            reasons.append(f"- 盈利能力出色(评分{scores['profitability_score']:.0f})，ROE={scores.get('roe', 0):.1f}%")
        elif scores["profitability_score"] >= 50:
            reasons.append(f"- 盈利能力良好(评分{scores['profitability_score']:.0f})")

        # 估值亮点
        if scores["valuation_score"] >= 70:
            pe = scores.get("pe_ratio", 0)
            pb = scores.get("pb_ratio", 0)
            reasons.append(f"- 估值具有吸引力(评分{scores['valuation_score']:.0f})，PE={pe:.1f}, PB={pb:.2f}")

        # 成长亮点
        if scores["growth_score"] >= 60:
            r1m = scores.get("return_1m")
            r3m = scores.get("return_3m")
            parts = []
            if r1m is not None:
                parts.append(f"近1月{r1m:.1f}%")
            if r3m is not None:
                parts.append(f"近3月{r3m:.1f}%")
            if parts:
                reasons.append(f"- 成长性良好(评分{scores['growth_score']:.0f})，{', '.join(parts)}")

        # 财务健康亮点
        if scores["financial_health_score"] >= 70:
            dte = scores.get("debt_to_equity", 0)
            reasons.append(f"- 财务状况健康(评分{scores['financial_health_score']:.0f})，资产负债率={dte:.0f}%")

        return "\n".join(reasons)

    def _generate_sell_reason(self, overall_score: float, scores: Dict, stock_info: Dict) -> str:
        """生成卖出理由"""
        reasons = [f"基本面多因子综合评分 {overall_score:.1f}/100，建议卖出或规避:"]

        # 盈利能力问题
        if scores["profitability_score"] <= 40:
            reasons.append(f"- 盈利能力偏弱(评分{scores['profitability_score']:.0f})，ROE={scores.get('roe', 0):.1f}%")

        # 估值问题
        if scores["valuation_score"] <= 40:
            pe = scores.get("pe_ratio", 0)
            pb = scores.get("pb_ratio", 0)
            reasons.append(f"- 估值偏高(评分{scores['valuation_score']:.0f})，PE={pe:.1f}, PB={pb:.2f}")

        # 成长性问题
        if scores["growth_score"] <= 40:
            reasons.append(f"- 成长性不足(评分{scores['growth_score']:.0f})")

        # 财务风险
        if scores["financial_health_score"] <= 40:
            dte = scores.get("debt_to_equity", 0)
            reasons.append(f"- 财务风险较高(评分{scores['financial_health_score']:.0f})，资产负债率={dte:.0f}%")

        return "\n".join(reasons)

    def _generate_hold_reason(self, overall_score: float, scores: Dict, stock_info: Dict) -> str:
        """生成观望理由"""
        reasons = [f"基本面多因子综合评分 {overall_score:.1f}/100，建议观望:"]

        # 列出各维度评分概况
        reasons.append(f"- 盈利能力: {scores['profitability_score']:.0f} | 估值: {scores['valuation_score']:.0f} | "
                       f"成长: {scores['growth_score']:.0f} | 财务健康: {scores['financial_health_score']:.0f}")

        # 找出最强和最弱维度
        dims = {
            "盈利能力": scores["profitability_score"],
            "估值": scores["valuation_score"],
            "成长": scores["growth_score"],
            "财务健康": scores["financial_health_score"],
        }
        best = max(dims, key=dims.get)
        worst = min(dims, key=dims.get)
        if best != worst:
            reasons.append(f"- 最强维度: {best}({dims[best]:.0f}), 最弱维度: {worst}({dims[worst]:.0f})")

        return "\n".join(reasons)

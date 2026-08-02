<<<<<<< HEAD
"""
操作指导智能体 - 将分析信号转化为风险控制后的执行建议
"""
from typing import Any, Dict, Optional

from stock_analyzer.agents.base_agent import AgentSignal, BaseAgent


class OperationGuideAgent(BaseAgent):
    """
    操作指导智能体

    不直接参与买/卖投票，而是在技术、基本面、情绪分析完成后，
    基于对冲基金常用的风险预算、分批建仓、止损和风险敞口控制方法，
    给出更可执行的操作建议。
    """

    RISK_PROFILE = {
        "conservative": {
            "max_position": 0.08,
            "initial_fraction": 0.30,
            "risk_per_trade": 0.005,
            "hedge_ratio": 0.60,
            "label": "保守型",
        },
        "moderate": {
            "max_position": 0.12,
            "initial_fraction": 0.40,
            "risk_per_trade": 0.010,
            "hedge_ratio": 0.40,
            "label": "稳健型",
        },
        "aggressive": {
            "max_position": 0.18,
            "initial_fraction": 0.50,
            "risk_per_trade": 0.015,
            "hedge_ratio": 0.25,
            "label": "进取型",
        },
    }

    def __init__(self, risk_tolerance: str = "moderate", portfolio_value: float = 10000.0):
        super().__init__(
            name="OperationGuide",
            description="基于风险预算、分批交易和对冲思路生成执行建议"
        )
        self.risk_tolerance = risk_tolerance if risk_tolerance in self.RISK_PROFILE else "moderate"
        self.portfolio_value = portfolio_value

    def analyze(self, symbol: str, data: Dict[str, Any]) -> AgentSignal:
        """生成操作指导建议"""
        final_decision = data.get("final_decision", {})
        signals = data.get("individual_signals", {})
        historical_data = data.get("historical_data")
        stock_info = data.get("stock_info", {})

        signal_type = final_decision.get("signal_type", "hold")
        confidence = float(final_decision.get("confidence", 0) or 0)
        target_price = final_decision.get("target_price")
        stop_loss = final_decision.get("stop_loss")

        current_price = self._get_current_price(historical_data, stock_info)
        volatility = self._estimate_volatility(historical_data)
        atr_pct = self._estimate_atr_pct(historical_data)
        risk_cfg = self.RISK_PROFILE[self.risk_tolerance]

        consensus = self._calculate_consensus(signals)
        position_plan = self._position_plan(
            signal_type=signal_type,
            confidence=confidence,
            volatility=volatility,
            consensus=consensus,
            current_price=current_price,
            stop_loss=stop_loss,
            risk_cfg=risk_cfg,
        )
        hedge_plan = self._hedge_plan(
            signal_type=signal_type,
            confidence=confidence,
            volatility=volatility,
            stock_info=stock_info,
            risk_cfg=risk_cfg,
        )
        execution_plan = self._execution_plan(
            signal_type=signal_type,
            current_price=current_price,
            target_price=target_price,
            stop_loss=stop_loss,
            atr_pct=atr_pct,
            position_plan=position_plan,
        )

        reasoning = self._build_reasoning(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            current_price=current_price,
            volatility=volatility,
            atr_pct=atr_pct,
            consensus=consensus,
            risk_cfg=risk_cfg,
            position_plan=position_plan,
            hedge_plan=hedge_plan,
            execution_plan=execution_plan,
        )

        guide_confidence = min(95, max(25, confidence + consensus["agreement"] * 20))
        return AgentSignal(
            agent_name=self.name,
            signal_type="guide",
            confidence=round(guide_confidence, 2),
            reasoning=reasoning,
            target_price=target_price,
            stop_loss=stop_loss,
            time_horizon="execution",
            metadata={
                "risk_profile": risk_cfg["label"],
                "current_price": current_price,
                "volatility_annualized": round(volatility, 4),
                "atr_pct": round(atr_pct, 4),
                "consensus": consensus,
                "position_plan": position_plan,
                "hedge_plan": hedge_plan,
                "execution_plan": execution_plan,
            },
        )

    def _get_current_price(self, historical_data, stock_info: Dict[str, Any]) -> Optional[float]:
        if historical_data is not None and not historical_data.empty:
            return float(historical_data["Close"].iloc[-1])
        for key in ("close", "regularMarketPrice", "current_price"):
            value = stock_info.get(key)
            if value:
                return float(value)
        return None

    def _estimate_volatility(self, historical_data) -> float:
        """估算年化波动率"""
        if historical_data is None or historical_data.empty or len(historical_data) < 30:
            return 0.30
        returns = historical_data["Close"].pct_change().dropna()
        if returns.empty:
            return 0.30
        return float(returns.tail(60).std() * (252 ** 0.5))

    def _estimate_atr_pct(self, historical_data) -> float:
        """估算 ATR 占价格比例，用于挂单区间和止损距离"""
        if historical_data is None or historical_data.empty or len(historical_data) < 15:
            return 0.03
        df = historical_data.tail(15).copy()
        high_low = df["High"] - df["Low"]
        high_close = (df["High"] - df["Close"].shift(1)).abs()
        low_close = (df["Low"] - df["Close"].shift(1)).abs()
        true_range = high_low.combine(high_close, max).combine(low_close, max)
        atr = float(true_range.tail(14).mean())
        price = float(df["Close"].iloc[-1])
        return max(0.005, min(0.12, atr / price)) if price > 0 else 0.03

    def _calculate_consensus(self, signals: Dict[str, AgentSignal]) -> Dict[str, Any]:
        buy = sum(1 for s in signals.values() if s.signal_type == "buy")
        sell = sum(1 for s in signals.values() if s.signal_type == "sell")
        hold = sum(1 for s in signals.values() if s.signal_type == "hold")
        total = max(1, len(signals))
        agreement = max(buy, sell, hold) / total
        conflict = buy > 0 and sell > 0
        return {
            "buy_count": buy,
            "sell_count": sell,
            "hold_count": hold,
            "agreement": round(agreement, 3),
            "conflict": conflict,
        }

    def _position_plan(
        self,
        signal_type: str,
        confidence: float,
        volatility: float,
        consensus: Dict[str, Any],
        current_price: Optional[float],
        stop_loss: Optional[float],
        risk_cfg: Dict[str, Any],
    ) -> Dict[str, Any]:
        """基于风险预算计算建议仓位"""
        if signal_type == "sell":
            target_position_pct = 0.0
        elif signal_type == "hold":
            target_position_pct = min(risk_cfg["max_position"] * 0.35, 0.05)
        else:
            confidence_factor = max(0.25, min(1.0, confidence / 80))
            consensus_factor = 0.70 if consensus["conflict"] else max(0.65, consensus["agreement"])
            volatility_factor = 1.0
            if volatility > 0.55:
                volatility_factor = 0.55
            elif volatility > 0.40:
                volatility_factor = 0.75
            elif volatility < 0.25:
                volatility_factor = 1.10
            target_position_pct = risk_cfg["max_position"] * confidence_factor * consensus_factor * volatility_factor

        target_position_pct = max(0.0, min(risk_cfg["max_position"], target_position_pct))

        # 如果有明确止损，用单笔风险预算约束仓位
        risk_budget_position_pct = None
        if current_price and stop_loss and current_price > 0 and stop_loss > 0:
            stop_distance = abs(current_price - stop_loss) / current_price
            if stop_distance > 0:
                risk_budget_position_pct = risk_cfg["risk_per_trade"] / stop_distance
                target_position_pct = min(target_position_pct, risk_budget_position_pct)

        target_amount = self.portfolio_value * target_position_pct
        initial_amount = target_amount * risk_cfg["initial_fraction"]
        shares = int(target_amount / current_price) if current_price else 0
        initial_shares = int(initial_amount / current_price) if current_price else 0

        return {
            "target_position_pct": round(target_position_pct * 100, 2),
            "max_position_pct": round(risk_cfg["max_position"] * 100, 2),
            "initial_position_pct": round(target_position_pct * risk_cfg["initial_fraction"] * 100, 2),
            "target_amount": round(target_amount, 2),
            "initial_amount": round(initial_amount, 2),
            "estimated_shares": shares,
            "initial_shares": initial_shares,
            "risk_budget_position_pct": round(risk_budget_position_pct * 100, 2) if risk_budget_position_pct else None,
        }

    def _hedge_plan(
        self,
        signal_type: str,
        confidence: float,
        volatility: float,
        stock_info: Dict[str, Any],
        risk_cfg: Dict[str, Any],
    ) -> Dict[str, Any]:
        """生成对冲建议"""
        beta = float(stock_info.get("beta") or 1.0)
        sector = stock_info.get("sector", "N/A")

        if signal_type == "buy":
            hedge_ratio = risk_cfg["hedge_ratio"]
            if confidence >= 70 and volatility < 0.35:
                hedge_ratio *= 0.6
            elif volatility > 0.50:
                hedge_ratio *= 1.3
            hedge_ratio = min(0.80, max(0.10, hedge_ratio))
            hedge_text = (
                f"如已有较高科技/半导体敞口，可用指数ETF空头或看跌期权对冲约 {hedge_ratio*100:.0f}% 的Beta敞口；"
                "若账户不支持做空/期权，则通过降低仓位替代对冲。"
            )
        elif signal_type == "sell":
            hedge_ratio = 1.0
            hedge_text = "不建议新增多头敞口；已有仓位优先降仓，必要时用保护性看跌期权覆盖剩余仓位。"
        else:
            hedge_ratio = min(0.50, risk_cfg["hedge_ratio"])
            hedge_text = "观望阶段不主动扩大敞口；若持仓较重，优先通过减仓或保护性看跌期权降低尾部风险。"

        return {
            "beta": round(beta, 2),
            "sector": sector,
            "suggested_hedge_ratio_pct": round(hedge_ratio * 100, 2),
            "method": hedge_text,
        }

    def _execution_plan(
        self,
        signal_type: str,
        current_price: Optional[float],
        target_price: Optional[float],
        stop_loss: Optional[float],
        atr_pct: float,
        position_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        """生成分批执行计划"""
        if current_price is None:
            return {"steps": ["价格数据缺失，暂不建议执行。"]}

        buy_zone_low = current_price * (1 - atr_pct * 0.5)
        buy_zone_high = current_price * (1 + atr_pct * 0.2)
        add_zone = current_price * (1 - atr_pct * 1.2)
        invalidation = stop_loss or current_price * (1 - atr_pct * 2.0)

        if signal_type == "buy":
            steps = [
                f"第一笔只做试探仓：约 {position_plan['initial_position_pct']}% 组合仓位，避免一次性满仓。",
                f"挂单区间优先放在 {buy_zone_low:.2f} - {buy_zone_high:.2f}，不要追高超过日内波动上沿。",
                f"若回撤到 {add_zone:.2f} 附近且基本面/技术面未恶化，再补第二笔。",
                f"若跌破 {invalidation:.2f} 或核心分析信号转空，先减仓而不是摊平。",
            ]
        elif signal_type == "sell":
            steps = [
                "已有仓位优先分两到三笔退出，避免在单一价位全部成交。",
                "若反弹但量能不足，可作为降低仓位的窗口。",
                f"若重新站上 {current_price * (1 + atr_pct * 1.5):.2f} 且技术信号转多，再重新评估。",
            ]
        else:
            steps = [
                "当前不适合主动扩大仓位，最多保留小观察仓。",
                f"若价格回落到 {add_zone:.2f} 附近且评分改善，再考虑试探性买入。",
                f"若跌破 {invalidation:.2f}，说明风险释放未结束，应继续等待。",
            ]

        return {
            "buy_zone_low": round(buy_zone_low, 2),
            "buy_zone_high": round(buy_zone_high, 2),
            "add_zone": round(add_zone, 2),
            "invalidation_price": round(invalidation, 2),
            "steps": steps,
        }

    def _build_reasoning(
        self,
        symbol: str,
        signal_type: str,
        confidence: float,
        current_price: Optional[float],
        volatility: float,
        atr_pct: float,
        consensus: Dict[str, Any],
        risk_cfg: Dict[str, Any],
        position_plan: Dict[str, Any],
        hedge_plan: Dict[str, Any],
        execution_plan: Dict[str, Any],
    ) -> str:
        lines = [
            f"操作指导（{risk_cfg['label']}风险参数）：{symbol}",
            f"上游综合信号为 {signal_type.upper()}，置信度 {confidence:.1f}%。当前建议以控制风险敞口为第一优先级。",
            f"当前价格: {current_price:.2f}" if current_price else "当前价格: 数据缺失",
            f"年化波动率估计: {volatility*100:.1f}%，ATR波动区间约 {atr_pct*100:.1f}%。",
            f"信号一致性: {consensus['buy_count']}多 / {consensus['sell_count']}空 / {consensus['hold_count']}观望，是否冲突: {'是' if consensus['conflict'] else '否'}。",
            "",
            "仓位建议:",
            f"- 目标仓位: {position_plan['target_position_pct']}%，单票上限: {position_plan['max_position_pct']}%。",
            f"- 首笔仓位: {position_plan['initial_position_pct']}%，约 {position_plan['initial_amount']} 资金。估算首笔股数: {position_plan['initial_shares']}。",
            f"- 目标总资金: {position_plan['target_amount']}，估算总股数: {position_plan['estimated_shares']}。",
            "",
            "执行步骤:",
        ]
        lines.extend([f"- {step}" for step in execution_plan["steps"]])
        lines.extend([
            "",
            "风险敞口与对冲:",
            f"- Beta估计: {hedge_plan['beta']}，行业: {hedge_plan['sector']}。",
            f"- 建议对冲比例: {hedge_plan['suggested_hedge_ratio_pct']}%。",
            f"- {hedge_plan['method']}",
            "",
            "注意：以上是基于模型的风险控制建议，不构成保证收益的投资承诺；执行前仍需结合账户规模、持仓相关性和交易成本。"
        ])
        return "\n".join(lines)
=======
"""
操作指导智能体 - 将分析信号转化为风险控制后的执行建议
"""
from typing import Any, Dict, Optional

from stock_analyzer.agents.base_agent import AgentSignal, BaseAgent


class OperationGuideAgent(BaseAgent):
    """
    操作指导智能体

    不直接参与买/卖投票，而是在技术、基本面、情绪分析完成后，
    基于对冲基金常用的风险预算、分批建仓、止损和风险敞口控制方法，
    给出更可执行的操作建议。
    """

    RISK_PROFILE = {
        "conservative": {
            "max_position": 0.08,
            "initial_fraction": 0.30,
            "risk_per_trade": 0.005,
            "hedge_ratio": 0.60,
            "label": "保守型",
        },
        "moderate": {
            "max_position": 0.12,
            "initial_fraction": 0.40,
            "risk_per_trade": 0.010,
            "hedge_ratio": 0.40,
            "label": "稳健型",
        },
        "aggressive": {
            "max_position": 0.18,
            "initial_fraction": 0.50,
            "risk_per_trade": 0.015,
            "hedge_ratio": 0.25,
            "label": "进取型",
        },
    }

    def __init__(self, risk_tolerance: str = "moderate", portfolio_value: float = 10000.0):
        super().__init__(
            name="OperationGuide",
            description="基于风险预算、分批交易和对冲思路生成执行建议"
        )
        self.risk_tolerance = risk_tolerance if risk_tolerance in self.RISK_PROFILE else "moderate"
        self.portfolio_value = portfolio_value

    def analyze(self, symbol: str, data: Dict[str, Any]) -> AgentSignal:
        """生成操作指导建议"""
        final_decision = data.get("final_decision", {})
        signals = data.get("individual_signals", {})
        historical_data = data.get("historical_data")
        stock_info = data.get("stock_info", {})

        signal_type = final_decision.get("signal_type", "hold")
        confidence = float(final_decision.get("confidence", 0) or 0)
        target_price = final_decision.get("target_price")
        stop_loss = final_decision.get("stop_loss")

        current_price = self._get_current_price(historical_data, stock_info)
        volatility = self._estimate_volatility(historical_data)
        atr_pct = self._estimate_atr_pct(historical_data)
        risk_cfg = self.RISK_PROFILE[self.risk_tolerance]

        consensus = self._calculate_consensus(signals)
        position_plan = self._position_plan(
            signal_type=signal_type,
            confidence=confidence,
            volatility=volatility,
            consensus=consensus,
            current_price=current_price,
            stop_loss=stop_loss,
            risk_cfg=risk_cfg,
        )
        hedge_plan = self._hedge_plan(
            signal_type=signal_type,
            confidence=confidence,
            volatility=volatility,
            stock_info=stock_info,
            risk_cfg=risk_cfg,
        )
        execution_plan = self._execution_plan(
            signal_type=signal_type,
            current_price=current_price,
            target_price=target_price,
            stop_loss=stop_loss,
            atr_pct=atr_pct,
            position_plan=position_plan,
        )

        reasoning = self._build_reasoning(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            current_price=current_price,
            volatility=volatility,
            atr_pct=atr_pct,
            consensus=consensus,
            risk_cfg=risk_cfg,
            position_plan=position_plan,
            hedge_plan=hedge_plan,
            execution_plan=execution_plan,
        )

        guide_confidence = min(95, max(25, confidence + consensus["agreement"] * 20))
        return AgentSignal(
            agent_name=self.name,
            signal_type="guide",
            confidence=round(guide_confidence, 2),
            reasoning=reasoning,
            target_price=target_price,
            stop_loss=stop_loss,
            time_horizon="execution",
            metadata={
                "risk_profile": risk_cfg["label"],
                "current_price": current_price,
                "volatility_annualized": round(volatility, 4),
                "atr_pct": round(atr_pct, 4),
                "consensus": consensus,
                "position_plan": position_plan,
                "hedge_plan": hedge_plan,
                "execution_plan": execution_plan,
            },
        )

    def _get_current_price(self, historical_data, stock_info: Dict[str, Any]) -> Optional[float]:
        if historical_data is not None and not historical_data.empty:
            return float(historical_data["Close"].iloc[-1])
        for key in ("close", "regularMarketPrice", "current_price"):
            value = stock_info.get(key)
            if value:
                return float(value)
        return None

    def _estimate_volatility(self, historical_data) -> float:
        """估算年化波动率"""
        if historical_data is None or historical_data.empty or len(historical_data) < 30:
            return 0.30
        returns = historical_data["Close"].pct_change().dropna()
        if returns.empty:
            return 0.30
        return float(returns.tail(60).std() * (252 ** 0.5))

    def _estimate_atr_pct(self, historical_data) -> float:
        """估算 ATR 占价格比例，用于挂单区间和止损距离"""
        if historical_data is None or historical_data.empty or len(historical_data) < 15:
            return 0.03
        df = historical_data.tail(15).copy()
        high_low = df["High"] - df["Low"]
        high_close = (df["High"] - df["Close"].shift(1)).abs()
        low_close = (df["Low"] - df["Close"].shift(1)).abs()
        true_range = high_low.combine(high_close, max).combine(low_close, max)
        atr = float(true_range.tail(14).mean())
        price = float(df["Close"].iloc[-1])
        return max(0.005, min(0.12, atr / price)) if price > 0 else 0.03

    def _calculate_consensus(self, signals: Dict[str, AgentSignal]) -> Dict[str, Any]:
        buy = sum(1 for s in signals.values() if s.signal_type == "buy")
        sell = sum(1 for s in signals.values() if s.signal_type == "sell")
        hold = sum(1 for s in signals.values() if s.signal_type == "hold")
        total = max(1, len(signals))
        agreement = max(buy, sell, hold) / total
        conflict = buy > 0 and sell > 0
        return {
            "buy_count": buy,
            "sell_count": sell,
            "hold_count": hold,
            "agreement": round(agreement, 3),
            "conflict": conflict,
        }

    def _position_plan(
        self,
        signal_type: str,
        confidence: float,
        volatility: float,
        consensus: Dict[str, Any],
        current_price: Optional[float],
        stop_loss: Optional[float],
        risk_cfg: Dict[str, Any],
    ) -> Dict[str, Any]:
        """基于风险预算计算建议仓位"""
        if signal_type == "sell":
            target_position_pct = 0.0
        elif signal_type == "hold":
            target_position_pct = min(risk_cfg["max_position"] * 0.35, 0.05)
        else:
            confidence_factor = max(0.25, min(1.0, confidence / 80))
            consensus_factor = 0.70 if consensus["conflict"] else max(0.65, consensus["agreement"])
            volatility_factor = 1.0
            if volatility > 0.55:
                volatility_factor = 0.55
            elif volatility > 0.40:
                volatility_factor = 0.75
            elif volatility < 0.25:
                volatility_factor = 1.10
            target_position_pct = risk_cfg["max_position"] * confidence_factor * consensus_factor * volatility_factor

        target_position_pct = max(0.0, min(risk_cfg["max_position"], target_position_pct))

        # 如果有明确止损，用单笔风险预算约束仓位
        risk_budget_position_pct = None
        if current_price and stop_loss and current_price > 0 and stop_loss > 0:
            stop_distance = abs(current_price - stop_loss) / current_price
            if stop_distance > 0:
                risk_budget_position_pct = risk_cfg["risk_per_trade"] / stop_distance
                target_position_pct = min(target_position_pct, risk_budget_position_pct)

        target_amount = self.portfolio_value * target_position_pct
        initial_amount = target_amount * risk_cfg["initial_fraction"]
        shares = int(target_amount / current_price) if current_price else 0
        initial_shares = int(initial_amount / current_price) if current_price else 0

        return {
            "target_position_pct": round(target_position_pct * 100, 2),
            "max_position_pct": round(risk_cfg["max_position"] * 100, 2),
            "initial_position_pct": round(target_position_pct * risk_cfg["initial_fraction"] * 100, 2),
            "target_amount": round(target_amount, 2),
            "initial_amount": round(initial_amount, 2),
            "estimated_shares": shares,
            "initial_shares": initial_shares,
            "risk_budget_position_pct": round(risk_budget_position_pct * 100, 2) if risk_budget_position_pct else None,
        }

    def _hedge_plan(
        self,
        signal_type: str,
        confidence: float,
        volatility: float,
        stock_info: Dict[str, Any],
        risk_cfg: Dict[str, Any],
    ) -> Dict[str, Any]:
        """生成对冲建议"""
        beta = float(stock_info.get("beta") or 1.0)
        sector = stock_info.get("sector", "N/A")

        if signal_type == "buy":
            hedge_ratio = risk_cfg["hedge_ratio"]
            if confidence >= 70 and volatility < 0.35:
                hedge_ratio *= 0.6
            elif volatility > 0.50:
                hedge_ratio *= 1.3
            hedge_ratio = min(0.80, max(0.10, hedge_ratio))
            hedge_text = (
                f"如已有较高科技/半导体敞口，可用指数ETF空头或看跌期权对冲约 {hedge_ratio*100:.0f}% 的Beta敞口；"
                "若账户不支持做空/期权，则通过降低仓位替代对冲。"
            )
        elif signal_type == "sell":
            hedge_ratio = 1.0
            hedge_text = "不建议新增多头敞口；已有仓位优先降仓，必要时用保护性看跌期权覆盖剩余仓位。"
        else:
            hedge_ratio = min(0.50, risk_cfg["hedge_ratio"])
            hedge_text = "观望阶段不主动扩大敞口；若持仓较重，优先通过减仓或保护性看跌期权降低尾部风险。"

        return {
            "beta": round(beta, 2),
            "sector": sector,
            "suggested_hedge_ratio_pct": round(hedge_ratio * 100, 2),
            "method": hedge_text,
        }

    def _execution_plan(
        self,
        signal_type: str,
        current_price: Optional[float],
        target_price: Optional[float],
        stop_loss: Optional[float],
        atr_pct: float,
        position_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        """生成分批执行计划"""
        if current_price is None:
            return {"steps": ["价格数据缺失，暂不建议执行。"]}

        buy_zone_low = current_price * (1 - atr_pct * 0.5)
        buy_zone_high = current_price * (1 + atr_pct * 0.2)
        add_zone = current_price * (1 - atr_pct * 1.2)
        invalidation = stop_loss or current_price * (1 - atr_pct * 2.0)

        if signal_type == "buy":
            steps = [
                f"第一笔只做试探仓：约 {position_plan['initial_position_pct']}% 组合仓位，避免一次性满仓。",
                f"挂单区间优先放在 {buy_zone_low:.2f} - {buy_zone_high:.2f}，不要追高超过日内波动上沿。",
                f"若回撤到 {add_zone:.2f} 附近且基本面/技术面未恶化，再补第二笔。",
                f"若跌破 {invalidation:.2f} 或核心分析信号转空，先减仓而不是摊平。",
            ]
        elif signal_type == "sell":
            steps = [
                "已有仓位优先分两到三笔退出，避免在单一价位全部成交。",
                "若反弹但量能不足，可作为降低仓位的窗口。",
                f"若重新站上 {current_price * (1 + atr_pct * 1.5):.2f} 且技术信号转多，再重新评估。",
            ]
        else:
            steps = [
                "当前不适合主动扩大仓位，最多保留小观察仓。",
                f"若价格回落到 {add_zone:.2f} 附近且评分改善，再考虑试探性买入。",
                f"若跌破 {invalidation:.2f}，说明风险释放未结束，应继续等待。",
            ]

        return {
            "buy_zone_low": round(buy_zone_low, 2),
            "buy_zone_high": round(buy_zone_high, 2),
            "add_zone": round(add_zone, 2),
            "invalidation_price": round(invalidation, 2),
            "steps": steps,
        }

    def _build_reasoning(
        self,
        symbol: str,
        signal_type: str,
        confidence: float,
        current_price: Optional[float],
        volatility: float,
        atr_pct: float,
        consensus: Dict[str, Any],
        risk_cfg: Dict[str, Any],
        position_plan: Dict[str, Any],
        hedge_plan: Dict[str, Any],
        execution_plan: Dict[str, Any],
    ) -> str:
        lines = [
            f"操作指导（{risk_cfg['label']}风险参数）：{symbol}",
            f"上游综合信号为 {signal_type.upper()}，置信度 {confidence:.1f}%。当前建议以控制风险敞口为第一优先级。",
            f"当前价格: {current_price:.2f}" if current_price else "当前价格: 数据缺失",
            f"年化波动率估计: {volatility*100:.1f}%，ATR波动区间约 {atr_pct*100:.1f}%。",
            f"信号一致性: {consensus['buy_count']}多 / {consensus['sell_count']}空 / {consensus['hold_count']}观望，是否冲突: {'是' if consensus['conflict'] else '否'}。",
            "",
            "仓位建议:",
            f"- 目标仓位: {position_plan['target_position_pct']}%，单票上限: {position_plan['max_position_pct']}%。",
            f"- 首笔仓位: {position_plan['initial_position_pct']}%，约 {position_plan['initial_amount']} 资金。估算首笔股数: {position_plan['initial_shares']}。",
            f"- 目标总资金: {position_plan['target_amount']}，估算总股数: {position_plan['estimated_shares']}。",
            "",
            "执行步骤:",
        ]
        lines.extend([f"- {step}" for step in execution_plan["steps"]])
        lines.extend([
            "",
            "风险敞口与对冲:",
            f"- Beta估计: {hedge_plan['beta']}，行业: {hedge_plan['sector']}。",
            f"- 建议对冲比例: {hedge_plan['suggested_hedge_ratio_pct']}%。",
            f"- {hedge_plan['method']}",
            "",
            "注意：以上是基于模型的风险控制建议，不构成保证收益的投资承诺；执行前仍需结合账户规模、持仓相关性和交易成本。"
        ])
        return "\n".join(lines)
>>>>>>> 9499a60678460588353065030d55c19c2df72747

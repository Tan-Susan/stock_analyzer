"""
技术分析智能体 - 基于技术指标生成交易信号
使用连续化评分系统，每个指标输出 [-1, +1] 的信号强度
"""
import math
from typing import Any, Dict

import pandas as pd

from stock_analyzer.agents.base_agent import AgentSignal, BaseAgent
from stock_analyzer.core.analyzer import TechnicalAnalyzer


class TechnicalAgent(BaseAgent):
    """
    技术分析智能体

    基于多种技术指标（MA、MACD、RSI、布林带、KDJ、CCI、OBV、ADX等）
    连续化评分系统，综合分析并生成交易信号
    """

    # 各指标权重（加和 = 1.0）
    INDICATOR_WEIGHTS = {
        "macd": 0.18,
        "rsi": 0.14,
        "bollinger": 0.12,
        "kdj": 0.12,
        "ma": 0.14,
        "cci": 0.10,
        "obv": 0.10,
        "adx": 0.10,
    }

    def __init__(self):
        super().__init__(
            name="TechnicalAnalyst",
            description="基于技术指标分析生成交易信号"
        )
        self.analyzer = TechnicalAnalyzer()

    def analyze(self, symbol: str, data: Dict[str, Any]) -> AgentSignal:
        """技术分析并生成信号"""
        if not self.validate_data(data, ["historical_data"]):
            return AgentSignal(
                agent_name=self.name,
                signal_type="hold",
                confidence=0,
                reasoning="缺少历史数据，无法进行分析"
            )

        df = data["historical_data"]
        if len(df) < 60:
            return AgentSignal(
                agent_name=self.name,
                signal_type="hold",
                confidence=30,
                reasoning="历史数据不足，建议观望"
            )

        # 计算所有技术指标
        analyzed_df = self.analyzer.full_analysis(df)
        latest = analyzed_df.iloc[-1]
        prev = analyzed_df.iloc[-2]

        # 计算 ATR 用于归一化
        atr = latest.get("ATR14", latest.get("ATR", 1))
        atr = max(atr, 0.01)  # 避免除零
        current_price = latest.get("Close", 0)

        # 各指标连续评分 [-1, +1]
        scores = {}
        reasons = []

        scores["macd"] = self._score_macd(latest, prev, atr)
        reasons.append(self._reason_macd(latest, prev, scores["macd"]))

        scores["rsi"] = self._score_rsi(latest)
        reasons.append(self._reason_rsi(latest, scores["rsi"]))

        scores["bollinger"] = self._score_bollinger(latest)
        reasons.append(self._reason_bollinger(latest, scores["bollinger"]))

        scores["kdj"] = self._score_kdj(latest, prev)
        reasons.append(self._reason_kdj(latest, scores["kdj"]))

        scores["ma"] = self._score_ma(latest)
        reasons.append(self._reason_ma(latest, scores["ma"]))

        scores["cci"] = self._score_cci(latest)
        reasons.append(self._reason_cci(latest, scores["cci"]))

        scores["obv"] = self._score_obv(analyzed_df, atr)
        reasons.append(self._reason_obv(scores["obv"]))

        scores["adx"] = self._score_adx(latest)
        reasons.append(self._reason_adx(latest, scores["adx"]))

        # 加权综合评分
        composite_score = sum(
            scores[k] * self.INDICATOR_WEIGHTS[k]
            for k in self.INDICATOR_WEIGHTS
        )

        # ADX 动态调整: ADX > 25 时趋势类指标(macd+ma)权重增加
        adx = latest.get("ADX", 20)
        if adx > 25:
            trend_boost = 1.3
            oscillator_dampen = 0.8
        elif adx < 18:
            trend_boost = 0.8
            oscillator_dampen = 1.2
        else:
            trend_boost = 1.0
            oscillator_dampen = 1.0

        composite_score = (
            scores["macd"] * 0.18 * trend_boost
            + scores["rsi"] * 0.14 * oscillator_dampen
            + scores["bollinger"] * 0.12 * oscillator_dampen
            + scores["kdj"] * 0.12 * oscillator_dampen
            + scores["ma"] * 0.14 * trend_boost
            + scores["cci"] * 0.10 * oscillator_dampen
            + scores["obv"] * 0.10
            + scores["adx"] * 0.10
        )

        # 信号判定（软阈值）
        if composite_score > 0.25:
            final_signal = "buy"
        elif composite_score < -0.25:
            final_signal = "sell"
        else:
            final_signal = "hold"

        # 置信度: 基于分数绝对值 + 信号一致性 + 方向集中度
        # 基础置信度: 分数偏离0的程度
        base_conf = min(80, abs(composite_score) * 150)
        # 信号一致性加分: 超过6个同方向指标，说明共识度高
        positive_count = sum(1 for v in scores.values() if v > 0.1)
        negative_count = sum(1 for v in scores.values() if v < -0.1)
        neutral_count = sum(1 for v in scores.values() if abs(v) <= 0.1)
        if (final_signal == "buy" and positive_count >= 6) or \
           (final_signal == "sell" and negative_count >= 6):
            base_conf = min(90, base_conf + 15)
        # hold 时: 如果指标方向高度一致（都接近中性），说明"确定是hold"
        # 如果指标分歧大（多空各半），说明"不确定"
        if final_signal == "hold":
            # 方向集中度: 1 - (分歧程度 / 最大分歧)
            max_disagree = len(scores) / 2  # 最大分歧
            disagreement = min(positive_count, negative_count)
            concentration = 1 - disagreement / max_disagree if max_disagree > 0 else 0.5
            # 集中度高 → 确定hold → 置信度高
            # 集中度低 → 不确定 → 置信度低
            hold_conf = 40 + concentration * 30  # 40-70
            confidence = max(base_conf, hold_conf)
        else:
            confidence = base_conf
        confidence = min(95, confidence)

        # 生成理由
        reasoning = f"技术分析综合评分: {composite_score:+.3f} ({len([v for v in scores.values() if v > 0.1])}多/{len([v for v in scores.values() if v < -0.1])}空/{len([v for v in scores.values() if abs(v) <= 0.1])}中性)\n"
        reasoning += "各指标评分:\n" + "\n".join([f"- {r}" for r in reasons])

        # 目标价和止损价
        if final_signal == "buy":
            target_price = current_price * (1 + abs(composite_score) * 0.12)
            stop_loss = current_price * (1 - abs(composite_score) * 0.06)
        elif final_signal == "sell":
            target_price = current_price * (1 - abs(composite_score) * 0.12)
            stop_loss = current_price * (1 + abs(composite_score) * 0.06)
        else:
            target_price = None
            stop_loss = None

        return AgentSignal(
            agent_name=self.name,
            signal_type=final_signal,
            confidence=round(confidence, 2),
            reasoning=reasoning,
            target_price=round(target_price, 2) if target_price else None,
            stop_loss=round(stop_loss, 2) if stop_loss else None,
            time_horizon="short",
            metadata={
                "composite_score": round(composite_score, 4),
                "adx": round(adx, 2),
                "atr": round(atr, 4),
                "indicator_scores": {k: round(v, 4) for k, v in scores.items()},
            }
        )

    # ---- 连续评分函数 [-1, +1] ----

    def _score_macd(self, latest, prev, atr):
        """MACD 连续评分, 用 ATR 归一化"""
        hist = latest.get("MACD_Histogram", 0)
        prev_hist = prev.get("MACD_Histogram", 0)
        # 用 ATR 归一化柱状图
        normalized = hist / atr if atr > 0 else 0
        # 变化方向加分
        direction = 1 if hist > prev_hist else (-0.3 if hist < prev_hist else 0)
        # tanh 映射到 [-1, +1]
        raw = math.tanh(normalized * 2) * 0.7 + direction * 0.3
        return max(-1.0, min(1.0, raw))

    def _score_rsi(self, latest):
        """RSI 连续评分, 软阈值"""
        rsi = latest.get("RSI", 50)
        if rsi <= 20:
            return 1.0
        elif rsi <= 35:
            return 0.5 + (35 - rsi) / 30
        elif rsi <= 50:
            return (50 - rsi) / 30
        elif rsi <= 65:
            return (50 - rsi) / 30
        elif rsi <= 80:
            return -(rsi - 65) / 30 - 0.5
        else:
            return -1.0

    def _score_bollinger(self, latest):
        """布林带连续评分"""
        pos = latest.get("BB_Position", 0.5)
        if pd.isna(pos):
            return 0
        return max(-1.0, min(1.0, (0.5 - pos) * 2.5))

    def _score_kdj(self, latest, prev):
        """KDJ 连续评分"""
        k = latest.get("K", 50)
        d = latest.get("D", 50)
        prev_k = prev.get("K", 50)
        prev_d = prev.get("D", 50)
        # K 值位置评分
        k_score = (50 - k) / 50
        # 金叉/死叉加分
        cross = 0
        if k > d and prev_k <= prev_d:
            cross = 0.3
        elif k < d and prev_k >= prev_d:
            cross = -0.3
        return max(-1.0, min(1.0, k_score * 0.7 + cross))

    def _score_ma(self, latest):
        """均线连续评分"""
        close = latest.get("Close", 0)
        ma5 = latest.get("MA5", 0)
        ma20 = latest.get("MA20", 0)
        ma60 = latest.get("MA60", 0)
        if ma5 == 0 or ma20 == 0 or ma60 == 0:
            return 0
        if close > ma5 > ma20 > ma60:
            return 1.0
        elif close < ma5 < ma20 < ma60:
            return -1.0
        elif close > ma5 and close > ma20:
            return 0.4
        elif close < ma5 and close < ma20:
            return -0.4
        elif close > ma20 and ma5 > ma20:
            return 0.2
        elif close < ma20 and ma5 < ma20:
            return -0.2
        return 0

    def _score_cci(self, latest):
        """CCI 连续评分"""
        cci = latest.get("CCI", 0)
        if pd.isna(cci):
            return 0
        # CCI > 100 超买, CCI < -100 超卖
        return max(-1.0, min(1.0, -math.tanh(cci / 200)))

    def _score_obv(self, df, atr):
        """OBV 连续评分"""
        if len(df) < 10:
            return 0
        # OBV 5日变化方向
        obv_latest = df["OBV"].iloc[-1] if "OBV" in df.columns else 0
        obv_5d_ago = df["OBV"].iloc[-5] if "OBV" in df.columns else 0
        price_change = df["Close"].iloc[-1] - df["Close"].iloc[-5]
        obv_change = obv_latest - obv_5d_ago
        # 量价配合: OBV上涨+价格上涨=看涨, OBV上涨+价格下跌=背离
        if price_change > 0 and obv_change > 0:
            return 0.5
        elif price_change > 0 and obv_change < 0:
            return -0.3  # 顶背离
        elif price_change < 0 and obv_change > 0:
            return 0.3   # 底背离
        elif price_change < 0 and obv_change < 0:
            return -0.5
        return 0

    def _score_adx(self, latest):
        """ADX 趋势强度评分（只作为方向参考）"""
        adx = latest.get("ADX", 20)
        plus_di = latest.get("PLUS_DI", 50)
        minus_di = latest.get("MINUS_DI", 50)
        if pd.isna(adx) or pd.isna(plus_di) or pd.isna(minus_di):
            return 0
        # ADX 高 + 方向明确 = 强信号
        if adx > 25:
            return max(-1.0, min(1.0, (plus_di - minus_di) / 50))
        return 0

    # ---- 理由生成 ----

    def _reason_macd(self, latest, prev, score):
        hist = latest.get("MACD_Histogram", 0)
        macd = latest.get("MACD", 0)
        direction = "扩张" if hist > prev.get("MACD_Histogram", 0) else "收缩"
        strength = "强烈" if abs(score) > 0.5 else "温和"
        side = "看多" if score > 0.1 else ("看空" if score < -0.1 else "中性")
        return f"MACD({macd:.4f})柱状图{direction}, {side}({strength}, 分数{score:+.2f})"

    def _reason_rsi(self, latest, score):
        rsi = latest.get("RSI", 50)
        label = "超卖" if rsi < 30 else ("超买" if rsi > 70 else "中间区域")
        return f"RSI({rsi:.1f}){label}(分数{score:+.2f})"

    def _reason_bollinger(self, latest, score):
        pos = latest.get("BB_Position", 0.5)
        pos = 0.5 if pd.isna(pos) else pos
        label = "下轨附近" if pos < 0.2 else ("上轨附近" if pos > 0.8 else "中轨区域")
        return f"布林带位置({pos:.2f}){label}(分数{score:+.2f})"

    def _reason_kdj(self, latest, score):
        k = latest.get("K", 50)
        d = latest.get("D", 50)
        label = "超卖区" if k < 20 else ("超买区" if k > 80 else "中间")
        return f"KDJ(K={k:.1f}, D={d:.1f}){label}(分数{score:+.2f})"

    def _reason_ma(self, latest, score):
        label = "多头排列" if score > 0.5 else ("空头排列" if score < -0.5 else "混合")
        return f"均线趋势: {label}(分数{score:+.2f})"

    def _reason_cci(self, latest, score):
        cci = latest.get("CCI", 0)
        if pd.isna(cci):
            return "CCI: 数据缺失"
        label = "超买" if cci > 100 else ("超卖" if cci < -100 else "正常")
        return f"CCI({cci:.1f}){label}(分数{score:+.2f})"

    def _reason_obv(self, score):
        label = "量价齐升" if score > 0.3 else ("量价齐跌" if score < -0.3 else ("顶背离" if score < -0.1 else ("底背离" if score > 0.1 else "中性")))
        return f"OBV能量潮: {label}(分数{score:+.2f})"

    def _reason_adx(self, latest, score):
        adx = latest.get("ADX", 20)
        if pd.isna(adx):
            return "ADX: 数据缺失"
        label = "强趋势" if adx > 25 else "弱趋势/震荡"
        side = "多" if score > 0 else ("空" if score < 0 else "")
        return f"ADX({adx:.1f}){label}, 方向{side}(分数{score:+.2f})"

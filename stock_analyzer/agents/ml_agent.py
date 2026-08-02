<<<<<<< HEAD
"""
机器学习预测智能体 - 基于MLP/随机森林的价格预测信号
"""
from typing import Any, Dict

import pandas as pd

from stock_analyzer.agents.base_agent import AgentSignal, BaseAgent
from stock_analyzer.ml.predictor import MLPredictor


class MLAgent(BaseAgent):
    """
    机器学习预测智能体

    使用随机森林或MLP神经网络，基于技术指标特征预测未来价格趋势，
    生成交易信号。每次分析时在线训练，保证模型使用最新数据。
    """

    def __init__(self, model_type: str = "random_forest"):
        super().__init__(
            name="MLPredictor",
            description="基于机器学习模型预测价格趋势"
        )
        self.model_type = model_type
        self.predictor = MLPredictor(model_type=model_type)

    def analyze(self, symbol: str, data: Dict[str, Any]) -> AgentSignal:
        """ML预测分析并生成信号"""
        if not self.validate_data(data, ["historical_data"]):
            return AgentSignal(
                agent_name=self.name,
                signal_type="hold",
                confidence=0,
                reasoning="缺少历史数据，无法进行ML预测"
            )

        df = data["historical_data"]
        if len(df) < 60:
            return AgentSignal(
                agent_name=self.name,
                signal_type="hold",
                confidence=20,
                reasoning="历史数据不足（需60条以上），ML模型无法训练"
            )

        current_price = data.get("current_price", df["Close"].iloc[-1] if "Close" in df.columns else 0)

        # 在线训练模型
        metrics = self.predictor.train(df, target_col="Close", test_ratio=0.2)
        r2 = metrics.get("R2", float("nan"))
        mae = metrics.get("MAE", float("nan"))

        # 检查训练是否成功
        if pd.isna(r2) or self.predictor.model is None:
            return AgentSignal(
                agent_name=self.name,
                signal_type="hold",
                confidence=20,
                reasoning=f"ML模型训练失败，无法生成预测信号"
            )

        # 预测未来5日价格
        predictions = self.predictor.predict(df, steps=5)
        avg_pred = sum(predictions) / len(predictions) if predictions else current_price

        # 获取特征重要性（仅随机森林）
        feature_importance = self.predictor.get_feature_importance()
        top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:3] if feature_importance else []

        # 根据预测趋势生成信号
        price_change_pct = (avg_pred - current_price) / current_price if current_price else 0

        if price_change_pct > 0.02:
            signal_type = "buy"
        elif price_change_pct < -0.02:
            signal_type = "sell"
        else:
            signal_type = "hold"

        # 置信度：基于R2 + 预测幅度
        # R2越高，模型越可信；预测幅度越大，信号越明确
        r2_score_norm = max(0, min(100, r2 * 100)) if not pd.isna(r2) else 30
        magnitude_score = min(50, abs(price_change_pct) * 1000)  # 2% -> 20分
        confidence = min(90, r2_score_norm * 0.5 + magnitude_score + 20)

        # 生成理由
        reasoning_lines = [
            f"ML模型({self.model_type})预测未来5日平均价格: {avg_pred:.2f} (当前: {current_price:.2f})",
            f"预测涨跌幅: {price_change_pct*100:+.2f}%",
            f"模型R2={r2:.3f}, MAE={mae:.3f}",
        ]
        if top_features:
            reasoning_lines.append(f"最重要特征: {', '.join([f'{k}({v:.2f})' for k, v in top_features])}")
        reasoning = "\n".join(reasoning_lines)

        # 目标价和止损价
        if signal_type == "buy":
            target_price = current_price * (1 + abs(price_change_pct) * 1.5)
            stop_loss = current_price * (1 - abs(price_change_pct) * 0.5)
        elif signal_type == "sell":
            target_price = current_price * (1 - abs(price_change_pct) * 1.5)
            stop_loss = current_price * (1 + abs(price_change_pct) * 0.5)
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
            time_horizon="medium",
            metadata={
                "model_type": self.model_type,
                "r2": round(r2, 4) if not pd.isna(r2) else None,
                "mae": round(mae, 4) if not pd.isna(mae) else None,
                "predictions": [round(p, 2) for p in predictions],
                "avg_prediction": round(avg_pred, 2),
                "price_change_pct": round(price_change_pct, 4),
                "feature_importance": {k: round(v, 4) for k, v in top_features},
            }
        )
=======
"""
机器学习预测智能体 - 基于MLP/随机森林的价格预测信号
"""
from typing import Any, Dict

import pandas as pd

from stock_analyzer.agents.base_agent import AgentSignal, BaseAgent
from stock_analyzer.ml.predictor import MLPredictor


class MLAgent(BaseAgent):
    """
    机器学习预测智能体

    使用随机森林或MLP神经网络，基于技术指标特征预测未来价格趋势，
    生成交易信号。每次分析时在线训练，保证模型使用最新数据。
    """

    def __init__(self, model_type: str = "random_forest"):
        super().__init__(
            name="MLPredictor",
            description="基于机器学习模型预测价格趋势"
        )
        self.model_type = model_type
        self.predictor = MLPredictor(model_type=model_type)

    def analyze(self, symbol: str, data: Dict[str, Any]) -> AgentSignal:
        """ML预测分析并生成信号"""
        if not self.validate_data(data, ["historical_data"]):
            return AgentSignal(
                agent_name=self.name,
                signal_type="hold",
                confidence=0,
                reasoning="缺少历史数据，无法进行ML预测"
            )

        df = data["historical_data"]
        if len(df) < 60:
            return AgentSignal(
                agent_name=self.name,
                signal_type="hold",
                confidence=20,
                reasoning="历史数据不足（需60条以上），ML模型无法训练"
            )

        current_price = data.get("current_price", df["Close"].iloc[-1] if "Close" in df.columns else 0)

        # 在线训练模型
        metrics = self.predictor.train(df, target_col="Close", test_ratio=0.2)
        r2 = metrics.get("R2", float("nan"))
        mae = metrics.get("MAE", float("nan"))

        # 检查训练是否成功
        if pd.isna(r2) or self.predictor.model is None:
            return AgentSignal(
                agent_name=self.name,
                signal_type="hold",
                confidence=20,
                reasoning=f"ML模型训练失败，无法生成预测信号"
            )

        # 预测未来5日价格
        predictions = self.predictor.predict(df, steps=5)
        avg_pred = sum(predictions) / len(predictions) if predictions else current_price

        # 获取特征重要性（仅随机森林）
        feature_importance = self.predictor.get_feature_importance()
        top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:3] if feature_importance else []

        # 根据预测趋势生成信号
        price_change_pct = (avg_pred - current_price) / current_price if current_price else 0

        if price_change_pct > 0.02:
            signal_type = "buy"
        elif price_change_pct < -0.02:
            signal_type = "sell"
        else:
            signal_type = "hold"

        # 置信度：基于R2 + 预测幅度
        # R2越高，模型越可信；预测幅度越大，信号越明确
        r2_score_norm = max(0, min(100, r2 * 100)) if not pd.isna(r2) else 30
        magnitude_score = min(50, abs(price_change_pct) * 1000)  # 2% -> 20分
        confidence = min(90, r2_score_norm * 0.5 + magnitude_score + 20)

        # 生成理由
        reasoning_lines = [
            f"ML模型({self.model_type})预测未来5日平均价格: {avg_pred:.2f} (当前: {current_price:.2f})",
            f"预测涨跌幅: {price_change_pct*100:+.2f}%",
            f"模型R2={r2:.3f}, MAE={mae:.3f}",
        ]
        if top_features:
            reasoning_lines.append(f"最重要特征: {', '.join([f'{k}({v:.2f})' for k, v in top_features])}")
        reasoning = "\n".join(reasoning_lines)

        # 目标价和止损价
        if signal_type == "buy":
            target_price = current_price * (1 + abs(price_change_pct) * 1.5)
            stop_loss = current_price * (1 - abs(price_change_pct) * 0.5)
        elif signal_type == "sell":
            target_price = current_price * (1 - abs(price_change_pct) * 1.5)
            stop_loss = current_price * (1 + abs(price_change_pct) * 0.5)
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
            time_horizon="medium",
            metadata={
                "model_type": self.model_type,
                "r2": round(r2, 4) if not pd.isna(r2) else None,
                "mae": round(mae, 4) if not pd.isna(mae) else None,
                "predictions": [round(p, 2) for p in predictions],
                "avg_prediction": round(avg_pred, 2),
                "price_change_pct": round(price_change_pct, 4),
                "feature_importance": {k: round(v, 4) for k, v in top_features},
            }
        )
>>>>>>> 9499a60678460588353065030d55c19c2df72747

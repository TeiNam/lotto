# utils/formatters.py
import json
from typing import List, Dict, Any
from models.prediction import LottoPrediction
from models.lotto_draw import LottoDraw


class ResultFormatter:
    """결과 포맷팅 유틸리티"""

    @staticmethod
    def format_predictions_to_json(predictions: List[LottoPrediction], pretty: bool = True) -> str:
        """예측 결과를 JSON 문자열로 변환"""
        prediction_dicts = [p.to_dict() for p in predictions]

        if pretty:
            return json.dumps(prediction_dicts, indent=2)
        else:
            return json.dumps(prediction_dicts)

    @staticmethod
    def format_predictions_to_text(predictions: List[LottoPrediction]) -> str:
        """예측 결과를 텍스트로 변환"""
        if not predictions:
            return "예측 결과가 없습니다."

        lines = ["다음 회차 로또 번호 예측 결과:"]

        for i, pred in enumerate(predictions, 1):
            numbers_str = ", ".join(str(n) for n in pred.combination)
            lines.append(f"{i}. [{numbers_str}] (점수: {pred.score:.4f}, 이전 회차와 공통 번호: {pred.common_with_last}개)")

        return "\n".join(lines)

    @staticmethod
    def format_draw_to_text(draw: LottoDraw) -> str:
        """당첨 번호를 텍스트로 변환"""
        if not draw:
            return "데이터가 없습니다."

        numbers_str = ", ".join(str(n) for n in draw.numbers)
        return f"회차: {draw.draw_no}, 당첨 번호: [{numbers_str}], 날짜: {draw.draw_date.strftime('%Y-%m-%d')}"
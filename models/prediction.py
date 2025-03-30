# models/prediction.py
from dataclasses import dataclass
from typing import List, Optional
import json


@dataclass
class LottoPrediction:
    """로또 번호 예측 모델"""
    combination: List[int]
    score: float
    common_with_last: int

    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            "combination": self.combination,
            "score": self.score,
            "common_with_last": self.common_with_last
        }

    def to_json(self):
        """JSON 문자열로 변환"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data):
        """딕셔너리에서 객체 생성"""
        return cls(
            combination=data["combination"],
            score=data["score"],
            common_with_last=data["common_with_last"]
        )
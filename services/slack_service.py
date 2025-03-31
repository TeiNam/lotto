# services/slack_service.py
import json
import logging
from typing import List, Dict, Any

import aiohttp

from config.settings import SLACK_WEBHOOK_URL
from utils.exceptions import SlackNotificationError

logger = logging.getLogger("lotto_prediction")


class SlackNotifier:
    """슬랙 알림 서비스"""

    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or SLACK_WEBHOOK_URL
        if not self.webhook_url:
            logger.error("슬랙 웹훅 URL이 설정되지 않았습니다.")
            raise ValueError("SLACK_WEBHOOK_URL is not set")

    async def send_prediction_notification(
            self,
            predictions: List[Dict[str, Any]],
            next_draw_no: int
    ) -> bool:
        """예측 결과를 슬랙으로 전송"""
        try:
            # 메시지 템플릿 생성
            message = self._create_prediction_message(predictions, next_draw_no)

            # 비동기 HTTP 요청으로 웹훅 호출
            async with aiohttp.ClientSession() as session:
                async with session.post(
                        self.webhook_url,
                        data=json.dumps(message),
                        headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        logger.info(f"슬랙 알림 전송 성공: {next_draw_no}회차 예측 ({len(predictions)}개)")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"슬랙 알림 전송 실패: {response.status}, {error_text}")
                        return False

        except Exception as e:
            logger.exception(f"슬랙 알림 전송 중 오류 발생: {str(e)}")
            raise SlackNotificationError(f"슬랙 알림 전송 실패: {str(e)}")

    def _create_prediction_message(
            self,
            predictions: List[Dict[str, Any]],
            next_draw_no: int
    ) -> Dict[str, Any]:
        """슬랙 메시지 포맷 생성"""
        # 예측 번호 문자열 생성
        prediction_texts = []
        for i, pred in enumerate(predictions, 1):
            numbers = pred.get("combination", [])
            score = pred.get("score", 0)
            common_with_last = pred.get("common_with_last", 0)

            # 번호를 문자열로 변환 (오름차순 정렬 확인)
            sorted_numbers = sorted(numbers)
            numbers_str = " ".join(f"{n:2d}" for n in sorted_numbers)

            prediction_texts.append(
                f"*{i}*: `{numbers_str}` (점수: {score:.4f}, 이전 회차와 공통: {common_with_last}개)"
            )

        # 전체 메시지 생성
        attachments = [
            {
                "color": "#36a64f",  # 녹색 컬러
                "text": "\n".join(prediction_texts),
                "footer": "로또 예측 시스템 | Claude 3.7 Sonnet",
                "footer_icon": "https://img.icons8.com/cute-clipart/64/lottery.png"
            }
        ]

        return {
            "text": f"🎲 *{next_draw_no}회차 로또 예측 번호*",
            "attachments": attachments
        }

    async def send_lottery_result_notification(
            self,
            draw_no: int,
            numbers: list,
            bonus_no: int,
            draw_date: str,
            prediction_comparisons: List[Dict[str, Any]] = None
    ) -> bool:
        """로또 당첨 결과를 슬랙으로 전송 (예측 비교 결과 포함)"""
        try:
            # 메시지 템플릿 생성
            message = self._create_lottery_result_message(
                draw_no=draw_no,
                numbers=numbers,
                bonus_no=bonus_no,
                draw_date=draw_date,
                prediction_comparisons=prediction_comparisons
            )

            # 비동기 HTTP 요청으로 웹훅 호출
            async with aiohttp.ClientSession() as session:
                async with session.post(
                        self.webhook_url,
                        data=json.dumps(message),
                        headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        logger.info(f"슬랙 당첨번호 알림 전송 성공: {draw_no}회차")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"슬랙 당첨번호 알림 전송 실패: {response.status}, {error_text}")
                        return False

        except Exception as e:
            logger.exception(f"슬랙 당첨번호 알림 전송 중 오류 발생: {str(e)}")
            raise SlackNotificationError(f"슬랙 당첨번호 알림 전송 실패: {str(e)}")

    def _create_lottery_result_message(
            self,
            draw_no: int,
            numbers: list,
            bonus_no: int,
            draw_date: str,
            prediction_comparisons: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """로또 당첨 결과 메시지 포맷 생성 (예측 비교 포함)"""
        # 당첨번호 문자열 생성
        numbers_str = " ".join(f"{n:2d}" for n in sorted(numbers))

        # 메시지 블록 초기화
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🎉 {draw_no}회차 로또 당첨번호 발표",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*당첨일자:*\n{draw_date}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*당첨번호*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```{numbers_str}```"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*보너스 번호:* {bonus_no}"
                }
            },
            {
                "type": "divider"
            }
        ]

        # 예측 비교 결과가 있는 경우 추가
        if prediction_comparisons and len(prediction_comparisons) > 0:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🔮 예측 결과 비교*"
                }
            })

            # 상위 5개 예측 결과만 표시
            for i, comp in enumerate(prediction_comparisons[:5], 1):
                pred_numbers_str = " ".join(f"{n:2d}" for n in sorted(comp["prediction_numbers"]))
                matched_numbers_str = ", ".join(str(n) for n in sorted(comp["matched_numbers"]))

                if not matched_numbers_str:
                    matched_numbers_str = "없음"

                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*예측 {i}:* `{pred_numbers_str}`\n"
                                f"*맞은 개수:* {comp['matched_count']}개\n"
                                f"*맞은 번호:* {matched_numbers_str}"
                    }
                })

            # 예측 결과 요약
            best_match = max(
                [comp["matched_count"] for comp in prediction_comparisons]) if prediction_comparisons else 0
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📊 예측 결과 요약*\n"
                            f"총 {len(prediction_comparisons)}개 예측 중 최고 {best_match}개 맞음"
                }
            })
        else:
            # 예측 결과가 없는 경우 메시지 추가
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🔮 예측 결과 비교*\n"
                            f"{draw_no}회차에 대한 예측 결과가 없습니다."
                }
            })

        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "로또 예측 시스템 | 동행복권 API 데이터 기준"
                }
            ]
        })

        return {
            "blocks": blocks
        }
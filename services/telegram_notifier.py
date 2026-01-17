"""Telegram 알림 서비스

이 모듈은 Telegram Bot API를 통해 로또 예측 결과를 전송합니다.
"""

import aiohttp
import logging
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger("lotto_prediction")


class TelegramNotifier:
    """Telegram 알림 서비스
    
    Telegram Bot API를 사용하여 예측 결과를 채팅방으로 전송합니다.
    """
    
    def __init__(self, bot_token: str, chat_id: str):
        """TelegramNotifier 초기화
        
        Args:
            bot_token: Telegram Bot API 토큰
            chat_id: 메시지를 보낼 채팅방 ID
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
    
    async def send_predictions(
        self,
        predictions: List[List[int]],
        timestamp: Optional[str] = None
    ) -> bool:
        """예측 결과를 Telegram으로 전송
        
        Args:
            predictions: 예측 번호 리스트 (각 예측은 6개 숫자 리스트)
            timestamp: 생성 시각 (선택, 없으면 현재 시각 사용)
            
        Returns:
            전송 성공 여부 (True: 성공, False: 실패)
        """
        try:
            # 타임스탬프가 없으면 현재 시각 사용
            if timestamp is None:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 메시지 포맷팅
            message = self._format_message(predictions, timestamp)
            
            # 메시지 전송
            success = await self._send_message(message)
            
            if success:
                logger.info(
                    f"Telegram 알림 전송 성공: {len(predictions)}개 예측",
                    extra={
                        "num_predictions": len(predictions),
                        "timestamp": timestamp
                    }
                )
            else:
                logger.warning(
                    f"Telegram 알림 전송 실패: {len(predictions)}개 예측",
                    extra={
                        "num_predictions": len(predictions),
                        "timestamp": timestamp
                    }
                )
            
            return success
            
        except Exception as e:
            logger.error(
                f"Telegram 알림 전송 중 오류 발생: {e}",
                extra={
                    "num_predictions": len(predictions),
                    "error": str(e)
                },
                exc_info=True
            )
            return False
    
    def _format_message(
        self,
        predictions: List[List[int]],
        timestamp: Optional[str] = None
    ) -> str:
        """Telegram 메시지 포맷팅
        
        Args:
            predictions: 예측 번호 리스트
            timestamp: 생성 시각
            
        Returns:
            포맷된 메시지 문자열
        """
        # 메시지 헤더
        lines = [
            "🎰 로또 예측 결과 🎰",
            ""
        ]
        
        # 타임스탬프 추가
        if timestamp:
            lines.append(f"생성 시각: {timestamp}")
            lines.append("")
        
        # 각 예측 번호 추가
        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟",
                        "1️⃣1️⃣", "1️⃣2️⃣", "1️⃣3️⃣", "1️⃣4️⃣", "1️⃣5️⃣", "1️⃣6️⃣", "1️⃣7️⃣", "1️⃣8️⃣", "1️⃣9️⃣", "2️⃣0️⃣"]
        
        for idx, prediction in enumerate(predictions, 1):
            # 인덱스에 맞는 이모지 선택 (최대 20개)
            emoji = number_emojis[idx - 1] if idx <= len(number_emojis) else f"{idx}."
            
            # 번호를 문자열로 포맷팅
            numbers_str = ", ".join(str(num) for num in prediction)
            lines.append(f"{emoji} [{numbers_str}]")
        
        # 메시지 푸터
        lines.append("")
        lines.append("행운을 빕니다! 🍀")
        
        return "\n".join(lines)
    
    async def _send_message(self, text: str) -> bool:
        """Telegram API를 통해 메시지 전송
        
        Args:
            text: 전송할 메시지
            
        Returns:
            전송 성공 여부
        """
        url = f"{self.api_url}/sendMessage"
        
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"  # HTML 포맷 지원
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("ok"):
                            logger.debug(f"Telegram API 응답 성공: {result}")
                            return True
                        else:
                            logger.error(
                                f"Telegram API 응답 실패: {result}",
                                extra={"response": result}
                            )
                            return False
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Telegram API HTTP 오류: {response.status}",
                            extra={
                                "status_code": response.status,
                                "error_text": error_text
                            }
                        )
                        return False
                        
        except aiohttp.ClientError as e:
            logger.error(
                f"Telegram API 연결 오류: {e}",
                extra={"error": str(e)},
                exc_info=True
            )
            return False
        except Exception as e:
            logger.error(
                f"Telegram 메시지 전송 중 예상치 못한 오류: {e}",
                extra={"error": str(e)},
                exc_info=True
            )
            return False

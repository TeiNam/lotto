"""Telegram 통합 테스트

이 모듈은 실제 Telegram Bot API를 사용한 통합 테스트를 제공합니다.
테스트 봇을 사용하여 메시지 전송 및 수신을 확인합니다.
"""

import pytest
import asyncio
import aiohttp
from datetime import datetime
from typing import List, Optional

from services.telegram_notifier import TelegramNotifier
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


class TestTelegramBotAPI:
    """Telegram Bot API 기본 기능 테스트"""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not TELEGRAM_BOT_TOKEN,
        reason="TELEGRAM_BOT_TOKEN이 설정되지 않았습니다"
    )
    async def test_bot_info(self):
        """
        Bot 정보 조회 테스트
        
        Bot API가 정상적으로 작동하는지 확인합니다.
        
        Requirements: 11.2
        """
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                assert response.status == 200, f"Bot API 호출 실패: {response.status}"
                
                result = await response.json()
                assert result.get("ok") is True, "Bot API 응답 오류"
                
                bot_info = result.get("result", {})
                assert "id" in bot_info, "Bot ID가 없습니다"
                assert "username" in bot_info, "Bot username이 없습니다"
                
                print(f"Bot 정보: {bot_info.get('username')} (ID: {bot_info.get('id')})")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID,
        reason="Telegram 설정이 없습니다 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)"
    )
    async def test_send_simple_message(self):
        """
        간단한 메시지 전송 테스트
        
        Requirements: 11.2, 11.3
        """
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"테스트 메시지 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                assert response.status == 200, f"메시지 전송 실패: {response.status}"
                
                result = await response.json()
                assert result.get("ok") is True, "메시지 전송 응답 오류"
                
                message_info = result.get("result", {})
                assert "message_id" in message_info, "메시지 ID가 없습니다"
                
                print(f"메시지 전송 성공: message_id={message_info.get('message_id')}")


class TestTelegramNotifierIntegration:
    """TelegramNotifier 통합 테스트"""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID,
        reason="Telegram 설정이 없습니다 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)"
    )
    async def test_send_single_prediction(self):
        """
        단일 예측 전송 테스트
        
        Requirements: 11.3, 11.4
        """
        notifier = TelegramNotifier(
            bot_token=TELEGRAM_BOT_TOKEN,
            chat_id=TELEGRAM_CHAT_ID
        )
        
        predictions = [[3, 12, 23, 28, 35, 42]]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        success = await notifier.send_predictions(
            predictions=predictions,
            timestamp=timestamp
        )
        
        assert success is True, "메시지 전송 실패"
        print(f"단일 예측 전송 성공: {predictions[0]}")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID,
        reason="Telegram 설정이 없습니다 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)"
    )
    async def test_send_multiple_predictions(self):
        """
        다중 예측 전송 테스트
        
        Requirements: 11.3, 11.4, 11.8
        """
        notifier = TelegramNotifier(
            bot_token=TELEGRAM_BOT_TOKEN,
            chat_id=TELEGRAM_CHAT_ID
        )
        
        predictions = [
            [3, 12, 23, 28, 35, 42],
            [5, 14, 19, 27, 33, 41],
            [7, 11, 22, 29, 36, 44],
            [2, 15, 24, 31, 38, 45],
            [8, 16, 20, 30, 37, 43]
        ]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        success = await notifier.send_predictions(
            predictions=predictions,
            timestamp=timestamp
        )
        
        assert success is True, "메시지 전송 실패"
        print(f"다중 예측 전송 성공: {len(predictions)}개")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID,
        reason="Telegram 설정이 없습니다 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)"
    )
    async def test_message_formatting(self):
        """
        메시지 포맷팅 테스트
        
        메시지에 모든 필수 정보가 포함되어 있는지 확인합니다.
        
        Requirements: 11.4, 11.5
        """
        notifier = TelegramNotifier(
            bot_token=TELEGRAM_BOT_TOKEN,
            chat_id=TELEGRAM_CHAT_ID
        )
        
        predictions = [
            [1, 2, 3, 4, 5, 6],
            [7, 8, 9, 10, 11, 12]
        ]
        timestamp = "2024-01-15 10:30:00"
        
        # 메시지 포맷팅
        message = notifier._format_message(predictions, timestamp)
        
        # 헤더 확인
        assert "🎰 로또 예측 결과 🎰" in message
        
        # 타임스탬프 확인
        assert timestamp in message
        assert "생성 시각:" in message
        
        # 예측 번호 확인
        assert "[1, 2, 3, 4, 5, 6]" in message
        assert "[7, 8, 9, 10, 11, 12]" in message
        
        # 푸터 확인
        assert "행운을 빕니다! 🍀" in message
        
        # 실제 전송
        success = await notifier.send_predictions(
            predictions=predictions,
            timestamp=timestamp
        )
        
        assert success is True
        print("메시지 포맷팅 테스트 성공")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID,
        reason="Telegram 설정이 없습니다 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)"
    )
    async def test_send_without_timestamp(self):
        """
        타임스탬프 없이 전송 테스트
        
        타임스탬프가 없으면 현재 시각을 사용해야 합니다.
        
        Requirements: 11.5
        """
        notifier = TelegramNotifier(
            bot_token=TELEGRAM_BOT_TOKEN,
            chat_id=TELEGRAM_CHAT_ID
        )
        
        predictions = [[10, 20, 30, 40, 41, 42]]
        
        # 타임스탬프 없이 전송
        success = await notifier.send_predictions(
            predictions=predictions,
            timestamp=None
        )
        
        assert success is True, "메시지 전송 실패"
        print("타임스탬프 없이 전송 성공")

    @pytest.mark.asyncio
    async def test_invalid_bot_token(self):
        """
        잘못된 Bot 토큰 처리 테스트
        
        Requirements: 11.6
        """
        notifier = TelegramNotifier(
            bot_token="invalid_token_12345",
            chat_id="123456789"
        )
        
        predictions = [[1, 2, 3, 4, 5, 6]]
        
        # 잘못된 토큰으로 전송 시도
        success = await notifier.send_predictions(
            predictions=predictions,
            timestamp=None
        )
        
        # 실패해도 예외가 발생하지 않고 False 반환
        assert success is False, "잘못된 토큰으로 성공하면 안 됨"
        print("잘못된 토큰 처리 성공 (예외 없이 False 반환)")

    @pytest.mark.asyncio
    async def test_invalid_chat_id(self):
        """
        잘못된 Chat ID 처리 테스트
        
        Requirements: 11.6
        """
        if not TELEGRAM_BOT_TOKEN:
            pytest.skip("TELEGRAM_BOT_TOKEN이 설정되지 않았습니다")
        
        notifier = TelegramNotifier(
            bot_token=TELEGRAM_BOT_TOKEN,
            chat_id="invalid_chat_id"
        )
        
        predictions = [[1, 2, 3, 4, 5, 6]]
        
        # 잘못된 Chat ID로 전송 시도
        success = await notifier.send_predictions(
            predictions=predictions,
            timestamp=None
        )
        
        # 실패해도 예외가 발생하지 않고 False 반환
        assert success is False, "잘못된 Chat ID로 성공하면 안 됨"
        print("잘못된 Chat ID 처리 성공 (예외 없이 False 반환)")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID,
        reason="Telegram 설정이 없습니다 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)"
    )
    async def test_concurrent_message_sending(self):
        """
        동시 메시지 전송 테스트
        
        여러 메시지를 동시에 전송해도 정상 작동해야 합니다.
        
        Requirements: 11.3
        """
        notifier = TelegramNotifier(
            bot_token=TELEGRAM_BOT_TOKEN,
            chat_id=TELEGRAM_CHAT_ID
        )
        
        # 여러 예측 세트 준비
        prediction_sets = [
            [[1, 2, 3, 4, 5, 6]],
            [[7, 8, 9, 10, 11, 12]],
            [[13, 14, 15, 16, 17, 18]]
        ]
        
        # 동시 전송
        tasks = [
            notifier.send_predictions(predictions=preds, timestamp=None)
            for preds in prediction_sets
        ]
        
        results = await asyncio.gather(*tasks)
        
        # 모든 전송이 성공해야 함
        assert all(results), "일부 메시지 전송 실패"
        assert len(results) == len(prediction_sets)
        
        print(f"동시 메시지 전송 성공: {len(results)}개")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID,
        reason="Telegram 설정이 없습니다 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)"
    )
    async def test_large_prediction_batch(self):
        """
        대량 예측 전송 테스트
        
        최대 20개 예측을 한 번에 전송할 수 있어야 합니다.
        
        Requirements: 11.8
        """
        notifier = TelegramNotifier(
            bot_token=TELEGRAM_BOT_TOKEN,
            chat_id=TELEGRAM_CHAT_ID
        )
        
        # 20개 예측 생성
        predictions = []
        for i in range(20):
            # 간단한 패턴으로 20개 조합 생성
            base = i * 2 + 1
            combo = [base, base+1, base+2, base+3, base+4, base+5]
            # 45를 넘지 않도록 조정
            combo = [min(n, 45) for n in combo]
            # 중복 제거 및 정렬
            combo = sorted(list(set(combo)))
            # 6개가 안 되면 채우기
            while len(combo) < 6:
                combo.append(min(combo[-1] + 1, 45))
            predictions.append(combo[:6])
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        success = await notifier.send_predictions(
            predictions=predictions,
            timestamp=timestamp
        )
        
        assert success is True, "대량 예측 전송 실패"
        print(f"대량 예측 전송 성공: {len(predictions)}개")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID,
        reason="Telegram 설정이 없습니다 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)"
    )
    async def test_special_characters_in_message(self):
        """
        특수 문자 포함 메시지 테스트
        
        메시지에 특수 문자가 포함되어도 정상 전송되어야 합니다.
        """
        notifier = TelegramNotifier(
            bot_token=TELEGRAM_BOT_TOKEN,
            chat_id=TELEGRAM_CHAT_ID
        )
        
        predictions = [[1, 2, 3, 4, 5, 6]]
        # 특수 문자가 포함된 타임스탬프
        timestamp = "2024-01-15 10:30:00 (테스트 🎰)"
        
        success = await notifier.send_predictions(
            predictions=predictions,
            timestamp=timestamp
        )
        
        assert success is True, "특수 문자 포함 메시지 전송 실패"
        print("특수 문자 포함 메시지 전송 성공")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID,
        reason="Telegram 설정이 없습니다 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)"
    )
    async def test_message_length_limit(self):
        """
        메시지 길이 제한 테스트
        
        Telegram은 메시지 길이를 4096자로 제한합니다.
        매우 많은 예측을 전송해도 오류가 발생하지 않아야 합니다.
        """
        notifier = TelegramNotifier(
            bot_token=TELEGRAM_BOT_TOKEN,
            chat_id=TELEGRAM_CHAT_ID
        )
        
        # 20개 예측 (정상 범위)
        predictions = []
        for i in range(20):
            base = i + 1
            combo = [base, base+5, base+10, base+15, base+20, base+25]
            combo = [min(n, 45) for n in combo]
            predictions.append(sorted(combo))
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 메시지 포맷팅
        message = notifier._format_message(predictions, timestamp)
        
        # 메시지 길이 확인
        print(f"메시지 길이: {len(message)} 문자")
        assert len(message) < 4096, "메시지가 Telegram 제한(4096자)을 초과합니다"
        
        # 전송
        success = await notifier.send_predictions(
            predictions=predictions,
            timestamp=timestamp
        )
        
        assert success is True, "메시지 전송 실패"
        print("메시지 길이 제한 테스트 성공")


class TestTelegramErrorHandling:
    """Telegram 에러 처리 테스트"""

    @pytest.mark.asyncio
    async def test_network_error_handling(self):
        """
        네트워크 오류 처리 테스트
        
        네트워크 오류가 발생해도 예외가 발생하지 않아야 합니다.
        
        Requirements: 11.6
        """
        from unittest.mock import AsyncMock, patch
        
        notifier = TelegramNotifier(
            bot_token="test_token",
            chat_id="test_chat_id"
        )
        
        predictions = [[1, 2, 3, 4, 5, 6]]
        
        # 네트워크 오류 시뮬레이션
        with patch('aiohttp.ClientSession.post', side_effect=aiohttp.ClientError("Network error")):
            success = await notifier.send_predictions(
                predictions=predictions,
                timestamp=None
            )
            
            # 실패해도 예외가 발생하지 않고 False 반환
            assert success is False
            print("네트워크 오류 처리 성공 (예외 없이 False 반환)")

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """
        타임아웃 처리 테스트
        
        타임아웃이 발생해도 예외가 발생하지 않아야 합니다.
        
        Requirements: 11.6
        """
        from unittest.mock import AsyncMock, patch
        
        notifier = TelegramNotifier(
            bot_token="test_token",
            chat_id="test_chat_id"
        )
        
        predictions = [[1, 2, 3, 4, 5, 6]]
        
        # 타임아웃 시뮬레이션
        with patch('aiohttp.ClientSession.post', side_effect=asyncio.TimeoutError("Timeout")):
            success = await notifier.send_predictions(
                predictions=predictions,
                timestamp=None
            )
            
            # 실패해도 예외가 발생하지 않고 False 반환
            assert success is False
            print("타임아웃 처리 성공 (예외 없이 False 반환)")

    @pytest.mark.asyncio
    async def test_empty_predictions(self):
        """
        빈 예측 리스트 처리 테스트
        
        빈 예측 리스트도 정상 처리되어야 합니다.
        """
        from unittest.mock import AsyncMock, patch
        
        notifier = TelegramNotifier(
            bot_token="test_token",
            chat_id="test_chat_id"
        )
        
        predictions = []
        
        with patch.object(notifier, '_send_message', new=AsyncMock(return_value=True)) as mock_send:
            success = await notifier.send_predictions(
                predictions=predictions,
                timestamp=None
            )
            
            # 빈 리스트도 전송 시도
            assert mock_send.called
            print("빈 예측 리스트 처리 성공")

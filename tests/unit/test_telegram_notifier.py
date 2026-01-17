"""TelegramNotifier 단위 테스트"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.telegram_notifier import TelegramNotifier


class TestTelegramNotifier:
    """TelegramNotifier 단위 테스트 클래스"""
    
    def test_init(self):
        """초기화 테스트"""
        bot_token = "test_token_123"
        chat_id = "test_chat_456"
        
        notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
        
        assert notifier.bot_token == bot_token
        assert notifier.chat_id == chat_id
        assert notifier.api_url == f"https://api.telegram.org/bot{bot_token}"
    
    def test_format_message_single_prediction(self):
        """단일 예측 메시지 포맷팅 테스트"""
        notifier = TelegramNotifier(bot_token="test_token", chat_id="test_chat")
        
        predictions = [[1, 2, 3, 4, 5, 6]]
        timestamp = "2024-01-15 10:30:00"
        
        message = notifier._format_message(predictions, timestamp)
        
        # 메시지 구조 검증
        assert "🎰 로또 예측 결과 🎰" in message
        assert "생성 시각: 2024-01-15 10:30:00" in message
        assert "[1, 2, 3, 4, 5, 6]" in message
        assert "행운을 빕니다! 🍀" in message
        assert "1️⃣" in message  # 첫 번째 예측 이모지
    
    def test_format_message_multiple_predictions(self):
        """여러 예측 메시지 포맷팅 테스트"""
        notifier = TelegramNotifier(bot_token="test_token", chat_id="test_chat")
        
        predictions = [
            [1, 2, 3, 4, 5, 6],
            [7, 8, 9, 10, 11, 12],
            [13, 14, 15, 16, 17, 18]
        ]
        timestamp = "2024-01-15 10:30:00"
        
        message = notifier._format_message(predictions, timestamp)
        
        # 모든 예측이 메시지에 포함되어야 함
        assert "[1, 2, 3, 4, 5, 6]" in message
        assert "[7, 8, 9, 10, 11, 12]" in message
        assert "[13, 14, 15, 16, 17, 18]" in message
        
        # 이모지 확인
        assert "1️⃣" in message
        assert "2️⃣" in message
        assert "3️⃣" in message
    
    def test_format_message_without_timestamp(self):
        """타임스탬프 없이 메시지 포맷팅 테스트"""
        notifier = TelegramNotifier(bot_token="test_token", chat_id="test_chat")
        
        predictions = [[1, 2, 3, 4, 5, 6]]
        
        message = notifier._format_message(predictions, timestamp=None)
        
        # 타임스탬프가 없어도 메시지는 생성되어야 함
        assert "🎰 로또 예측 결과 🎰" in message
        assert "[1, 2, 3, 4, 5, 6]" in message
        assert "행운을 빕니다! 🍀" in message
        # 타임스탬프 라인은 없어야 함
        assert "생성 시각:" not in message
    
    def test_format_message_many_predictions(self):
        """많은 예측 메시지 포맷팅 테스트 (20개)"""
        notifier = TelegramNotifier(bot_token="test_token", chat_id="test_chat")
        
        # 20개 예측 생성
        predictions = [[i, i+1, i+2, i+3, i+4, i+5] for i in range(1, 21)]
        
        message = notifier._format_message(predictions, timestamp="2024-01-15 10:30:00")
        
        # 모든 예측이 포함되어야 함
        assert len([line for line in message.split('\n') if '[' in line]) == 20
        
        # 20번째 예측 확인
        assert "2️⃣0️⃣" in message
    
    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """메시지 전송 성공 테스트"""
        notifier = TelegramNotifier(bot_token="test_token", chat_id="test_chat")
        
        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"ok": True, "result": {}})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await notifier._send_message("Test message")
        
        assert result is True
        mock_session.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_message_api_error(self):
        """API 오류 응답 테스트"""
        notifier = TelegramNotifier(bot_token="test_token", chat_id="test_chat")
        
        # Mock response with error
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"ok": False, "error_code": 400})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await notifier._send_message("Test message")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_message_http_error(self):
        """HTTP 오류 상태 코드 테스트"""
        notifier = TelegramNotifier(bot_token="test_token", chat_id="test_chat")
        
        # Mock response with HTTP error
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await notifier._send_message("Test message")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_message_connection_error(self):
        """연결 오류 테스트"""
        notifier = TelegramNotifier(bot_token="test_token", chat_id="test_chat")
        
        # Mock session that raises connection error
        mock_session = AsyncMock()
        mock_session.post = MagicMock(side_effect=Exception("Connection failed"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await notifier._send_message("Test message")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_predictions_success(self):
        """예측 전송 성공 테스트"""
        notifier = TelegramNotifier(bot_token="test_token", chat_id="test_chat")
        
        predictions = [[1, 2, 3, 4, 5, 6]]
        timestamp = "2024-01-15 10:30:00"
        
        # Mock _send_message to return success
        with patch.object(notifier, '_send_message', new=AsyncMock(return_value=True)):
            result = await notifier.send_predictions(predictions, timestamp)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_send_predictions_failure(self):
        """예측 전송 실패 테스트"""
        notifier = TelegramNotifier(bot_token="test_token", chat_id="test_chat")
        
        predictions = [[1, 2, 3, 4, 5, 6]]
        
        # Mock _send_message to return failure
        with patch.object(notifier, '_send_message', new=AsyncMock(return_value=False)):
            result = await notifier.send_predictions(predictions)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_predictions_exception_handling(self):
        """예측 전송 중 예외 처리 테스트"""
        notifier = TelegramNotifier(bot_token="test_token", chat_id="test_chat")
        
        predictions = [[1, 2, 3, 4, 5, 6]]
        
        # Mock _send_message to raise exception
        with patch.object(notifier, '_send_message', new=AsyncMock(side_effect=Exception("API Error"))):
            result = await notifier.send_predictions(predictions)
        
        # 예외가 발생해도 False 반환 (크래시 안 함)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_predictions_auto_timestamp(self):
        """자동 타임스탬프 생성 테스트"""
        notifier = TelegramNotifier(bot_token="test_token", chat_id="test_chat")
        
        predictions = [[1, 2, 3, 4, 5, 6]]
        
        # Mock _send_message
        with patch.object(notifier, '_send_message', new=AsyncMock(return_value=True)) as mock_send:
            result = await notifier.send_predictions(predictions, timestamp=None)
        
        assert result is True
        # _send_message가 호출되었는지 확인
        mock_send.assert_called_once()
        
        # 호출된 메시지에 타임스탬프가 포함되어 있는지 확인
        called_message = mock_send.call_args[0][0]
        assert "생성 시각:" in called_message
    
    @pytest.mark.asyncio
    async def test_send_predictions_with_multiple_predictions(self):
        """여러 예측 전송 테스트"""
        notifier = TelegramNotifier(bot_token="test_token", chat_id="test_chat")
        
        predictions = [
            [1, 2, 3, 4, 5, 6],
            [7, 8, 9, 10, 11, 12],
            [13, 14, 15, 16, 17, 18]
        ]
        
        with patch.object(notifier, '_send_message', new=AsyncMock(return_value=True)) as mock_send:
            result = await notifier.send_predictions(predictions)
        
        assert result is True
        
        # 호출된 메시지에 모든 예측이 포함되어 있는지 확인
        called_message = mock_send.call_args[0][0]
        assert "[1, 2, 3, 4, 5, 6]" in called_message
        assert "[7, 8, 9, 10, 11, 12]" in called_message
        assert "[13, 14, 15, 16, 17, 18]" in called_message

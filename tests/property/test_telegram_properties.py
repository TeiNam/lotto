"""TelegramNotifier 속성 기반 테스트

Property 11: Telegram Message Formatting
For any set of predictions sent to Telegram, the message should include 
all prediction numbers and a timestamp in a readable format.

Validates: Requirements 11.4, 11.5
"""

import pytest
from hypothesis import given, strategies as st, settings
from services.telegram_notifier import TelegramNotifier


# 전략: 1-45 범위의 6개 고유 숫자 조합 생성
@st.composite
def lotto_combination(draw):
    """로또 조합 생성 전략 (1-45 범위의 6개 고유 숫자)"""
    numbers = draw(st.lists(
        st.integers(min_value=1, max_value=45),
        min_size=6,
        max_size=6,
        unique=True
    ))
    return sorted(numbers)


# 전략: 1-20개의 로또 조합 리스트 생성
@st.composite
def predictions_list(draw):
    """예측 리스트 생성 전략 (1-20개의 조합)"""
    num_predictions = draw(st.integers(min_value=1, max_value=20))
    predictions = [draw(lotto_combination()) for _ in range(num_predictions)]
    return predictions


# 전략: 타임스탬프 문자열 생성
from datetime import datetime as dt

timestamp_strategy = st.one_of(
    st.none(),
    st.datetimes(
        min_value=dt(2020, 1, 1),
        max_value=dt(2030, 12, 31)
    ).map(lambda dt_obj: dt_obj.strftime("%Y-%m-%d %H:%M:%S"))
)


@given(
    predictions=predictions_list(),
    timestamp=timestamp_strategy
)
@settings(max_examples=100)
def test_property_telegram_message_formatting(predictions, timestamp):
    """
    Feature: lotto-algorithm-simplification, Property 11: Telegram Message Formatting
    
    For any set of predictions sent to Telegram, the message should include 
    all prediction numbers and a timestamp in a readable format.
    
    Validates: Requirements 11.4, 11.5
    """
    # Given: TelegramNotifier 인스턴스
    notifier = TelegramNotifier(bot_token="test_token", chat_id="test_chat")
    
    # When: 메시지 포맷팅
    message = notifier._format_message(predictions, timestamp)
    
    # Then: 메시지 구조 검증
    
    # 1. 메시지 헤더가 포함되어야 함
    assert "🎰 로또 예측 결과 🎰" in message, "메시지 헤더가 없습니다"
    
    # 2. 메시지 푸터가 포함되어야 함
    assert "행운을 빕니다! 🍀" in message, "메시지 푸터가 없습니다"
    
    # 3. 타임스탬프가 제공된 경우 메시지에 포함되어야 함
    if timestamp is not None:
        assert f"생성 시각: {timestamp}" in message, f"타임스탬프 '{timestamp}'가 메시지에 없습니다"
    
    # 4. 모든 예측 번호가 메시지에 포함되어야 함
    for prediction in predictions:
        # 번호를 문자열로 변환
        numbers_str = ", ".join(str(num) for num in prediction)
        prediction_str = f"[{numbers_str}]"
        assert prediction_str in message, f"예측 {prediction_str}이 메시지에 없습니다"
    
    # 5. 메시지가 비어있지 않아야 함
    assert len(message) > 0, "메시지가 비어있습니다"
    
    # 6. 메시지가 여러 줄로 구성되어야 함
    lines = message.split('\n')
    assert len(lines) >= 3, "메시지가 너무 짧습니다 (최소 3줄 이상)"
    
    # 7. 예측 개수만큼 번호 라인이 있어야 함
    # 대괄호로 시작하는 라인 또는 이모지가 있는 라인 카운트
    prediction_lines = [line for line in lines if '[' in line and ']' in line]
    assert len(prediction_lines) == len(predictions), \
        f"예측 개수({len(predictions)})와 메시지의 예측 라인 수({len(prediction_lines)})가 일치하지 않습니다"


@given(predictions=predictions_list())
@settings(max_examples=100)
def test_property_telegram_message_contains_all_numbers(predictions):
    """
    Feature: lotto-algorithm-simplification, Property 11: Telegram Message Formatting
    
    For any set of predictions, all individual numbers should be present in the message.
    
    Validates: Requirements 11.4
    """
    # Given: TelegramNotifier 인스턴스
    notifier = TelegramNotifier(bot_token="test_token", chat_id="test_chat")
    
    # When: 메시지 포맷팅
    message = notifier._format_message(predictions, timestamp="2024-01-15 10:30:00")
    
    # Then: 모든 개별 숫자가 메시지에 포함되어야 함
    for prediction in predictions:
        for number in prediction:
            assert str(number) in message, \
                f"숫자 {number}가 메시지에 없습니다 (예측: {prediction})"


@given(
    predictions=predictions_list(),
    timestamp=st.datetimes(
        min_value=dt(2020, 1, 1),
        max_value=dt(2030, 12, 31)
    ).map(lambda dt_obj: dt_obj.strftime("%Y-%m-%d %H:%M:%S"))
)
@settings(max_examples=100)
def test_property_telegram_message_timestamp_format(predictions, timestamp):
    """
    Feature: lotto-algorithm-simplification, Property 11: Telegram Message Formatting
    
    For any timestamp provided, it should be included in a readable format.
    
    Validates: Requirements 11.5
    """
    # Given: TelegramNotifier 인스턴스
    notifier = TelegramNotifier(bot_token="test_token", chat_id="test_chat")
    
    # When: 메시지 포맷팅
    message = notifier._format_message(predictions, timestamp)
    
    # Then: 타임스탬프가 읽기 쉬운 형식으로 포함되어야 함
    assert "생성 시각:" in message, "타임스탬프 라벨이 없습니다"
    assert timestamp in message, f"타임스탬프 '{timestamp}'가 메시지에 없습니다"
    
    # 타임스탬프 라인 찾기
    lines = message.split('\n')
    timestamp_lines = [line for line in lines if "생성 시각:" in line]
    assert len(timestamp_lines) == 1, "타임스탬프 라인이 정확히 하나여야 합니다"
    
    # 타임스탬프 형식 검증 (YYYY-MM-DD HH:MM:SS)
    timestamp_line = timestamp_lines[0]
    assert timestamp in timestamp_line, "타임스탬프가 올바른 라인에 없습니다"


@given(predictions=predictions_list())
@settings(max_examples=100)
def test_property_telegram_message_structure_consistency(predictions):
    """
    Feature: lotto-algorithm-simplification, Property 11: Telegram Message Formatting
    
    For any set of predictions, the message structure should be consistent.
    
    Validates: Requirements 11.4, 11.5
    """
    # Given: TelegramNotifier 인스턴스
    notifier = TelegramNotifier(bot_token="test_token", chat_id="test_chat")
    
    # When: 메시지 포맷팅 (타임스탬프 있음)
    message_with_timestamp = notifier._format_message(
        predictions, 
        timestamp="2024-01-15 10:30:00"
    )
    
    # When: 메시지 포맷팅 (타임스탬프 없음)
    message_without_timestamp = notifier._format_message(predictions, timestamp=None)
    
    # Then: 두 메시지 모두 기본 구조를 가져야 함
    for message in [message_with_timestamp, message_without_timestamp]:
        # 헤더 확인
        assert message.startswith("🎰 로또 예측 결과 🎰"), "메시지가 헤더로 시작해야 합니다"
        
        # 푸터 확인
        assert message.endswith("행운을 빕니다! 🍀"), "메시지가 푸터로 끝나야 합니다"
        
        # 예측 개수 확인
        prediction_lines = [line for line in message.split('\n') if '[' in line and ']' in line]
        assert len(prediction_lines) == len(predictions), \
            "예측 개수가 일치하지 않습니다"
    
    # Then: 타임스탬프 유무에 따른 차이 확인
    assert "생성 시각:" in message_with_timestamp, \
        "타임스탬프가 있는 메시지에 '생성 시각:'이 없습니다"
    assert "생성 시각:" not in message_without_timestamp, \
        "타임스탬프가 없는 메시지에 '생성 시각:'이 있으면 안 됩니다"


@given(
    num_predictions=st.integers(min_value=1, max_value=20)
)
@settings(max_examples=100)
def test_property_telegram_message_handles_various_prediction_counts(num_predictions):
    """
    Feature: lotto-algorithm-simplification, Property 11: Telegram Message Formatting
    
    For any number of predictions (1-20), the message should be properly formatted.
    
    Validates: Requirements 11.4
    """
    # Given: TelegramNotifier 인스턴스
    notifier = TelegramNotifier(bot_token="test_token", chat_id="test_chat")
    
    # Given: 지정된 개수의 예측 생성
    predictions = []
    for i in range(num_predictions):
        # 간단한 예측 생성 (중복 방지를 위해 범위 조정)
        start = (i * 6) % 40 + 1
        prediction = [start + j for j in range(6)]
        # 45를 초과하지 않도록 조정
        prediction = [n if n <= 45 else n - 40 for n in prediction]
        predictions.append(sorted(prediction))
    
    # When: 메시지 포맷팅
    message = notifier._format_message(predictions, timestamp="2024-01-15 10:30:00")
    
    # Then: 메시지가 올바르게 생성되어야 함
    assert len(message) > 0, "메시지가 비어있습니다"
    
    # 예측 개수 확인
    prediction_lines = [line for line in message.split('\n') if '[' in line and ']' in line]
    assert len(prediction_lines) == num_predictions, \
        f"예측 개수({num_predictions})와 메시지의 예측 라인 수({len(prediction_lines)})가 일치하지 않습니다"
    
    # 기본 구조 확인
    assert "🎰 로또 예측 결과 🎰" in message
    assert "행운을 빕니다! 🍀" in message

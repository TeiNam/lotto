"""/stats · /delete 명령어 단위 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram_bot_handler import _format_hit_stats, delete_command


def _row(numbers, winning, user_id=1):
    return {"user_id": user_id, "numbers": numbers, "winning": winning, "bonus": 7}


class TestFormatHitStats:
    """적중 분포 포맷팅 테스트"""

    def test_match_counts_are_bucketed(self):
        """일치 개수별로 정확히 집계되는지 확인"""
        rows = [
            _row([1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 6]),   # 6개
            _row([1, 2, 3, 40, 41, 42], [1, 2, 3, 4, 5, 6]),  # 3개
            _row([40, 41, 42, 43, 44, 45], [1, 2, 3, 4, 5, 6]),  # 0개
        ]
        result = _format_hit_stats("테스트", rows)

        assert "채점 3건" in result
        assert "0개: 1건" in result
        assert "3개: 1건" in result
        assert "6개: 1건" in result
        assert "→ 5등 이상: 2건" in result

    def test_zero_high_matches_are_hidden(self):
        """5·6개 적중 기록이 없으면 해당 줄을 표시하지 않음"""
        result = _format_hit_stats("테스트", [_row([1, 2, 3, 40, 41, 42], [1, 2, 3, 4, 5, 6])])

        assert "5개:" not in result
        assert "6개:" not in result


class TestDeleteCommand:
    """/delete 인덱스 → id 매핑 테스트"""

    def _update(self, user_id=1):
        update = MagicMock()
        update.effective_user.id = user_id
        update.message.reply_text = AsyncMock()
        return update

    @pytest.mark.asyncio
    async def test_deletes_selected_indexes(self):
        """지정한 순번의 예측만 id 기준으로 삭제"""
        update = self._update()
        context = MagicMock()
        context.args = ["1", "3"]

        with patch("telegram_bot_handler.AsyncLottoRepository") as mock_repo, \
             patch("telegram_bot_handler.TELEGRAM_ADMIN_IDS", {1}):
            mock_repo.get_last_draw = AsyncMock(return_value={"no": 1200})
            mock_repo.get_recommendations_for_draw = AsyncMock(return_value=[
                {"id": 10, "numbers": [1, 2, 3, 4, 5, 6]},
                {"id": 11, "numbers": [7, 8, 9, 10, 11, 12]},
                {"id": 12, "numbers": [13, 14, 15, 16, 17, 18]},
            ])
            mock_repo.delete_recommendation = AsyncMock(return_value=True)

            await delete_command(update, context)

        deleted_ids = [call.args[0] for call in mock_repo.delete_recommendation.call_args_list]
        assert deleted_ids == [10, 12]
        assert "2개 삭제 완료" in update.message.reply_text.call_args.args[0]

    @pytest.mark.asyncio
    async def test_rejects_out_of_range_index(self):
        """목록 범위를 벗어난 순번은 삭제하지 않음"""
        update = self._update()
        context = MagicMock()
        context.args = ["5"]

        with patch("telegram_bot_handler.AsyncLottoRepository") as mock_repo, \
             patch("telegram_bot_handler.TELEGRAM_ADMIN_IDS", {1}):
            mock_repo.get_last_draw = AsyncMock(return_value={"no": 1200})
            mock_repo.get_recommendations_for_draw = AsyncMock(return_value=[
                {"id": 10, "numbers": [1, 2, 3, 4, 5, 6]},
            ])
            mock_repo.delete_recommendation = AsyncMock(return_value=True)

            await delete_command(update, context)

        mock_repo.delete_recommendation.assert_not_called()
        assert "범위의 순번만" in update.message.reply_text.call_args.args[0]

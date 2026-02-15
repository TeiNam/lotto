"""Telegram Bot 핸들러

사용자가 Telegram Bot과 대화하면서 로또 예측을 생성하고 결과를 확인할 수 있습니다.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from telegram import Update, Bot
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    MessageHandler, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from database.repositories.lotto_repository import AsyncLottoRepository
from services.data_service import AsyncDataService
from services.random_generator import RandomGenerator
from services.duplicate_checker import DuplicateChecker
from services.simplified_prediction_service import SimplifiedPredictionService
from services.lottery_service import LotteryService

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 전역 서비스 인스턴스
data_service: Optional[AsyncDataService] = None
prediction_service: Optional[SimplifiedPredictionService] = None
scheduler: Optional[AsyncIOScheduler] = None

# 메시지 발송 재시도 설정
MAX_SEND_RETRIES = 3
RETRY_DELAY_SECONDS = 10


async def initialize_services():
    """서비스 초기화"""
    global data_service, prediction_service

    data_service = AsyncDataService()
    random_generator = RandomGenerator()
    duplicate_checker = DuplicateChecker(data_service)
    prediction_service = SimplifiedPredictionService(
        random_generator=random_generator,
        duplicate_checker=duplicate_checker,
        data_service=data_service
    )

    # 최근 데이터 로드
    last_draw = await AsyncLottoRepository.get_last_draw()
    if last_draw:
        last_draw_no = last_draw['no']
        start_no = max(1, last_draw_no - 9)
        await data_service.load_historical_data(
            start_no=start_no, end_no=last_draw_no
        )
        logger.info(f"데이터 로드 완료: {len(data_service.draws)}개 회차")


async def send_message_with_retry(
    bot: Bot,
    chat_id: str,
    text: str,
    max_retries: int = MAX_SEND_RETRIES,
    retry_delay: int = RETRY_DELAY_SECONDS
) -> bool:
    """메시지 발송 (재시도 로직 포함)

    Args:
        bot: Telegram Bot 인스턴스
        chat_id: 대상 채팅 ID
        text: 발송할 메시지
        max_retries: 최대 재시도 횟수
        retry_delay: 재시도 간격(초)

    Returns:
        발송 성공 여부
    """
    for attempt in range(1, max_retries + 1):
        try:
            await bot.send_message(chat_id=chat_id, text=text)
            logger.info(f"메시지 발송 성공 (시도 {attempt}/{max_retries})")
            return True
        except Exception as e:
            logger.warning(
                f"메시지 발송 실패 (시도 {attempt}/{max_retries}): {e}"
            )
            if attempt < max_retries:
                # 지수 백오프: 10초, 20초, 40초...
                delay = retry_delay * (2 ** (attempt - 1))
                logger.info(f"{delay}초 후 재시도...")
                await asyncio.sleep(delay)

    logger.error(
        f"메시지 발송 최종 실패 (chat_id: {chat_id}, "
        f"재시도 {max_retries}회 모두 소진)"
    )
    return False


async def update_lottery_results():
    """토요일 밤 9시 당첨번호 자동 업데이트 및 결과 알림"""
    logger.info("당첨번호 자동 업데이트 시작")

    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    try:
        success = await LotteryService.update_latest_draw()

        if success:
            logger.info("당첨번호 업데이트 성공")

            # 데이터 서비스 새로고침
            last_draw = await AsyncLottoRepository.get_last_draw()
            if last_draw:
                last_draw_no = last_draw['no']
                start_no = max(1, last_draw_no - 9)
                await data_service.load_historical_data(
                    start_no=start_no, end_no=last_draw_no
                )

                # 당첨번호 알림 발송
                numbers = [last_draw[str(i)] for i in range(1, 7)]
                numbers_str = ", ".join(str(n) for n in sorted(numbers))

                message = (
                    f"[{last_draw_no}회 당첨번호 업데이트]\n\n"
                    f"당첨 번호: [{numbers_str}]\n"
                    f"업데이트 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )

                sent = await send_message_with_retry(
                    bot, TELEGRAM_CHAT_ID, message
                )
                if not sent:
                    logger.error("당첨번호 알림 발송 최종 실패")
        else:
            logger.warning("당첨번호 업데이트 실패 (미발표 또는 오류)")

            # 실패 알림도 발송
            fail_message = (
                "[당첨번호 업데이트 실패]\n\n"
                "아직 발표되지 않았거나 조회 중 오류가 발생했습니다.\n"
                "30분 후 재시도합니다."
            )
            await send_message_with_retry(bot, TELEGRAM_CHAT_ID, fail_message)

    except Exception as e:
        logger.error(f"당첨번호 업데이트 중 오류: {e}", exc_info=True)

        error_message = (
            "[당첨번호 업데이트 오류]\n\n"
            f"오류: {str(e)[:200]}"
        )
        await send_message_with_retry(bot, TELEGRAM_CHAT_ID, error_message)


async def generate_weekly_predictions():
    """금요일 정오 자동 예측 생성 및 텔레그램 전송"""
    logger.info("주간 예측 자동 생성 시작")

    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    try:
        predictions = await prediction_service.generate_predictions(
            num_predictions=10
        )

        if not predictions:
            logger.error("예측 생성 실패")
            await send_message_with_retry(
                bot, TELEGRAM_CHAT_ID,
                "[주간 예측 생성 실패]\n\n예측 번호를 생성하지 못했습니다."
            )
            return

        # 다음 회차 번호
        last_draw = await AsyncLottoRepository.get_last_draw()
        next_draw_no = last_draw['no'] + 1 if last_draw else 1

        # DB 저장
        saved_count = 0
        for pred in predictions:
            try:
                success = await AsyncLottoRepository.save_recommendation(
                    numbers=pred.combination,
                    next_no=next_draw_no
                )
                if success:
                    saved_count += 1
            except Exception as e:
                logger.error(f"예측 저장 실패: {e}")

        logger.info(f"예측 생성 완료: {saved_count}/{len(predictions)}개 저장")

        # 메시지 구성
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message_lines = [
            f"[{next_draw_no}회 주간 예측]",
            "",
            f"생성 시각: {timestamp}",
            f"생성 개수: {len(predictions)}개",
            f"저장 완료: {saved_count}개",
            ""
        ]

        for idx, pred in enumerate(predictions, 1):
            numbers_str = ", ".join(str(n) for n in pred.combination)
            message_lines.append(f"{idx:2d}. [{numbers_str}]")

        message = "\n".join(message_lines)

        sent = await send_message_with_retry(bot, TELEGRAM_CHAT_ID, message)
        if sent:
            logger.info(f"주간 예측 텔레그램 발송 완료")
        else:
            logger.error("주간 예측 텔레그램 발송 최종 실패")

    except Exception as e:
        logger.error(f"주간 예측 생성 중 오류: {e}", exc_info=True)

        error_message = (
            "[주간 예측 생성 오류]\n\n"
            f"오류: {str(e)[:200]}"
        )
        await send_message_with_retry(bot, TELEGRAM_CHAT_ID, error_message)


def setup_scheduler():
    """스케줄러 설정"""
    global scheduler

    scheduler = AsyncIOScheduler()

    # 매주 토요일 밤 9시: 당첨번호 업데이트
    scheduler.add_job(
        update_lottery_results,
        CronTrigger(day_of_week='sat', hour=21, minute=0),
        id='saturday_lottery_update',
        name='토요일 밤 9시 당첨번호 업데이트'
    )

    # 토요일 밤 9시 30분: 당첨번호 업데이트 재시도 (첫 시도 실패 대비)
    scheduler.add_job(
        update_lottery_results,
        CronTrigger(day_of_week='sat', hour=21, minute=30),
        id='saturday_lottery_update_retry',
        name='토요일 밤 9시 30분 당첨번호 업데이트 재시도'
    )

    # 매주 금요일 정오: 예측 생성 및 텔레그램 전송
    scheduler.add_job(
        generate_weekly_predictions,
        CronTrigger(day_of_week='fri', hour=12, minute=0),
        id='friday_prediction_generation',
        name='금요일 정오 예측 생성'
    )

    scheduler.start()
    logger.info("스케줄러 시작됨")
    logger.info("  - 매주 금요일 12:00: 예측 생성 및 텔레그램 전송")
    logger.info("  - 매주 토요일 21:00: 당첨번호 업데이트")
    logger.info("  - 매주 토요일 21:30: 당첨번호 업데이트 재시도")

    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        if next_run:
            logger.info(
                f"  [{job.name}] 다음 실행: "
                f"{next_run.strftime('%Y-%m-%d %H:%M:%S')}"
            )


def stop_scheduler():
    """스케줄러 중지"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        logger.info("스케줄러 중지됨")


# -- 명령어 핸들러 --

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """시작 명령어 핸들러"""
    welcome_message = (
        "[로또 예측 봇]\n\n"
        "사용 가능한 명령어:\n"
        "/generate - 5개 조합 생성 (기본)\n"
        "/generate [개수] - 원하는 개수만큼 생성 (최대 20개)\n"
        "/mylist - 이번 회차 생성된 전체 번호 보기\n"
        "/winning - 최신 회차 당첨 번호 확인\n"
        "/result - 내 예측과 당첨 번호 매칭 확인\n"
        "/result [회차] - 특정 회차 결과 확인\n"
        "/help - 명령어 안내\n"
        "/start - 시작 메시지 표시"
    )
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """도움말 명령어 핸들러"""
    help_message = (
        "[명령어 안내]\n\n"
        "예측 생성:\n"
        "  /generate - 5개 조합 생성 (기본)\n"
        "  /generate [개수] - 원하는 개수만큼 생성 (최대 20개)\n"
        "  예: /generate 10\n\n"
        "내 번호 확인:\n"
        "  /mylist - 이번 회차 생성된 전체 번호 보기\n\n"
        "당첨 확인:\n"
        "  /winning - 최신 회차 당첨 번호 확인\n\n"
        "결과 확인:\n"
        "  /result - 내가 생성한 번호와 당첨 번호 매칭 확인\n"
        "  /result [회차] - 특정 회차 결과 확인\n"
        "  예: /result 1150\n\n"
        "기타:\n"
        "  /help - 이 메시지 표시\n"
        "  /start - 시작 메시지 표시\n\n"
        "참고: 당첨 번호는 매주 토요일 밤 9시에 자동 업데이트됩니다."
    )
    await update.message.reply_text(help_message)


async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """예측 생성 명령어 핸들러"""
    try:
        num_predictions = 5
        if context.args and len(context.args) > 0:
            try:
                num_predictions = int(context.args[0])
                if not 1 <= num_predictions <= 20:
                    await update.message.reply_text(
                        "생성 개수는 1~20 사이여야 합니다.\n예: /generate 10"
                    )
                    return
            except ValueError:
                await update.message.reply_text(
                    "올바른 숫자를 입력해주세요.\n예: /generate 10"
                )
                return

        loading_msg = await update.message.reply_text(
            f"{num_predictions}개 조합 생성 중..."
        )

        predictions = await prediction_service.generate_predictions(
            num_predictions=num_predictions
        )

        # 다음 회차 번호
        last_draw = await AsyncLottoRepository.get_last_draw()
        next_draw_no = last_draw['no'] + 1 if last_draw else 1

        # DB 저장 (사용자 ID 포함)
        user_id = update.effective_user.id
        saved_count = 0
        for pred in predictions:
            try:
                success = await AsyncLottoRepository.save_recommendation(
                    numbers=pred.combination,
                    next_no=next_draw_no,
                    user_id=user_id
                )
                if success:
                    saved_count += 1
            except Exception as e:
                logger.error(f"예측 저장 실패: {e}")

        # 결과 메시지
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message_lines = [
            f"[{next_draw_no}회 예측 결과]",
            "",
            f"생성 시각: {timestamp}",
            f"생성 개수: {len(predictions)}개",
            f"저장 완료: {saved_count}개",
            ""
        ]

        for idx, pred in enumerate(predictions, 1):
            numbers_str = ", ".join(str(n) for n in pred.combination)
            message_lines.append(f"{idx:2d}. [{numbers_str}]")

        message = "\n".join(message_lines)

        await loading_msg.delete()
        await update.message.reply_text(message)

        logger.info(
            f"예측 생성 완료: {num_predictions}개, "
            f"사용자: {update.effective_user.id}"
        )

    except Exception as e:
        logger.error(f"예측 생성 오류: {e}", exc_info=True)
        await update.message.reply_text(
            f"예측 생성 중 오류가 발생했습니다.\n{str(e)}"
        )


async def mylist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """이번 회차 생성된 전체 번호 조회 명령어 핸들러"""
    try:
        # 다음 회차 번호 계산
        last_draw = await AsyncLottoRepository.get_last_draw()
        if not last_draw:
            await update.message.reply_text("당첨 번호 정보를 찾을 수 없습니다.")
            return

        next_draw_no = last_draw['no'] + 1

        # 해당 회차의 내 예측 번호 조회 (사용자별)
        user_id = update.effective_user.id
        predictions = await AsyncLottoRepository.get_recommendations_for_draw(
            next_draw_no, user_id=user_id
        )

        if not predictions:
            await update.message.reply_text(
                f"{next_draw_no}회차에 생성한 예측이 없습니다.\n"
                f"/generate 명령어로 예측을 생성해보세요."
            )
            return

        # 메시지 구성
        message_lines = [
            f"[{next_draw_no}회 내 예측 번호 전체 목록]",
            "",
            f"총 {len(predictions)}개 조합",
            ""
        ]

        for idx, pred in enumerate(predictions, 1):
            numbers_str = ", ".join(str(n) for n in pred['numbers'])
            # 생성 시각 포맷팅
            create_at = pred.get('create_at')
            if create_at:
                if hasattr(create_at, 'strftime'):
                    time_str = create_at.strftime('%m/%d %H:%M')
                else:
                    time_str = str(create_at)[:16]
            else:
                time_str = ""

            message_lines.append(f"{idx:2d}. [{numbers_str}]  {time_str}")

        # 텔레그램 메시지 길이 제한(4096자) 대응
        message = "\n".join(message_lines)
        if len(message) > 4000:
            # 메시지를 분할 전송
            chunks = _split_message(message_lines)
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(message)

    except Exception as e:
        logger.error(f"내 번호 조회 오류: {e}", exc_info=True)
        await update.message.reply_text(
            f"번호 조회 중 오류가 발생했습니다.\n{str(e)}"
        )


def _split_message(lines: List[str], max_length: int = 4000) -> List[str]:
    """긴 메시지를 텔레그램 제한에 맞게 분할

    Args:
        lines: 메시지 라인 리스트
        max_length: 최대 메시지 길이

    Returns:
        분할된 메시지 리스트
    """
    chunks = []
    current_chunk = []
    current_length = 0

    for line in lines:
        line_length = len(line) + 1  # +1 for newline
        if current_length + line_length > max_length and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_length = 0

        current_chunk.append(line)
        current_length += line_length

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


async def check_winning_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """당첨 번호 확인 명령어 핸들러"""
    try:
        last_draw = await AsyncLottoRepository.get_last_draw()

        if not last_draw:
            await update.message.reply_text("당첨 번호 정보를 찾을 수 없습니다.")
            return

        draw_no = last_draw['no']
        numbers = [last_draw[str(i)] for i in range(1, 7)]
        draw_date = last_draw['create_at']

        numbers_str = ", ".join(str(n) for n in sorted(numbers))

        message = (
            f"[{draw_no}회 당첨 번호]\n\n"
            f"추첨일: {draw_date}\n"
            f"당첨 번호: [{numbers_str}]\n\n"
            f"다음 회차는 {draw_no + 1}회입니다."
        )

        await update.message.reply_text(message)

    except Exception as e:
        logger.error(f"당첨 번호 조회 오류: {e}", exc_info=True)
        await update.message.reply_text(
            f"당첨 번호 조회 중 오류가 발생했습니다.\n{str(e)}"
        )


async def check_result_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """결과 확인 명령어 핸들러"""
    try:
        target_draw_no = None
        if context.args and len(context.args) > 0:
            try:
                target_draw_no = int(context.args[0])
            except ValueError:
                await update.message.reply_text(
                    "올바른 회차 번호를 입력해주세요.\n예: /result 1206"
                )
                return

        # 회차 번호가 없으면 최신 회차 사용
        if target_draw_no is None:
            last_draw = await AsyncLottoRepository.get_last_draw()
            if not last_draw:
                await update.message.reply_text("당첨 번호 정보를 찾을 수 없습니다.")
                return
            target_draw_no = last_draw['no']

        draw_no = target_draw_no

        # 당첨 번호 조회
        winning_numbers = await _get_winning_numbers(draw_no)
        if not winning_numbers:
            await update.message.reply_text(
                f"{draw_no}회차 당첨 번호를 찾을 수 없습니다."
            )
            return

        # 내 예측 번호 조회 (사용자별)
        user_id = update.effective_user.id
        my_predictions = await AsyncLottoRepository.get_recommendations_for_draw(
            draw_no, user_id=user_id
        )

        if not my_predictions:
            await update.message.reply_text(
                f"{draw_no}회차에 생성한 예측이 없습니다."
            )
            return

        # 매칭 결과 계산
        results = []
        for pred in my_predictions:
            pred_numbers = set(pred['numbers'])
            winning_set = set(winning_numbers)
            matches = len(pred_numbers & winning_set)
            results.append((pred['numbers'], matches))

        results.sort(key=lambda x: x[1], reverse=True)

        winning_str = ", ".join(str(n) for n in sorted(winning_numbers))

        message_lines = [
            f"[{draw_no}회차 결과 확인]",
            "",
            f"당첨 번호: [{winning_str}]",
            f"내 예측: {len(my_predictions)}개",
            ""
        ]

        # 등수 판정
        rank_info = {
            6: "1등",
            5: "2등/3등",
            4: "4등",
            3: "5등",
        }

        best_match = results[0][1] if results else 0

        if best_match >= 3:
            message_lines.append(f"최고 매칭: {best_match}개 일치")
            if best_match in rank_info:
                message_lines.append(f"  -> {rank_info[best_match]}")
            message_lines.append("")

        message_lines.append("[상세 결과]")
        # 전체 결과 표시
        for idx, (numbers, matches) in enumerate(results, 1):
            numbers_str = ", ".join(str(n) for n in numbers)
            mark = "O" if matches >= 3 else "X"
            message_lines.append(
                f"{idx}. [{numbers_str}] - {matches}개 일치 {mark}"
            )

        # 텔레그램 메시지 길이 제한(4096자) 대응
        message = "\n".join(message_lines)
        if len(message) > 4000:
            chunks = _split_message(message_lines)
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(message)

    except Exception as e:
        logger.error(f"결과 확인 오류: {e}", exc_info=True)
        await update.message.reply_text(
            f"결과 확인 중 오류가 발생했습니다.\n{str(e)}"
        )


async def _get_winning_numbers(draw_no: int) -> Optional[List[int]]:
    """특정 회차의 당첨 번호 조회"""
    try:
        from database.connector import AsyncDatabaseConnector
        query = """
        SELECT `1`, `2`, `3`, `4`, `5`, `6`
        FROM result
        WHERE no = %s
        """
        results = await AsyncDatabaseConnector.execute_query(
            query, (draw_no,)
        )

        if results and len(results) > 0:
            row = results[0]
            return [row[str(i)] for i in range(1, 7)]

        return None

    except Exception as e:
        logger.error(f"당첨 번호 조회 오류: {e}")
        return None


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """알 수 없는 명령어 핸들러"""
    message = (
        "알 수 없는 명령어입니다.\n\n"
        "사용 가능한 명령어:\n"
        "/generate - 예측 생성 (기본 5개)\n"
        "/generate [개수] - 원하는 개수만큼 생성 (최대 20개)\n"
        "/mylist - 이번 회차 내 번호 보기\n"
        "/winning - 당첨 번호 확인\n"
        "/result - 내 예측과 당첨 번호 매칭 확인\n"
        "/result [회차] - 특정 회차 결과 확인\n"
        "/help - 명령어 안내\n"
        "/start - 시작 메시지 표시"
    )
    await update.message.reply_text(message)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """에러 핸들러"""
    logger.error(
        f"Update {update} caused error {context.error}",
        exc_info=context.error
    )


def main():
    """메인 함수"""
    async def run_bot():
        """Bot 실행 (비동기)"""
        logger.info("서비스 초기화 중...")
        await initialize_services()
        logger.info("서비스 초기화 완료")

        setup_scheduler()

        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # 명령어 핸들러 등록
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("generate", generate_command))
        application.add_handler(CommandHandler("mylist", mylist_command))
        application.add_handler(CommandHandler("winning", check_winning_command))
        application.add_handler(CommandHandler("result", check_result_command))

        # 알 수 없는 명령어 핸들러
        application.add_handler(
            MessageHandler(filters.COMMAND, unknown_command)
        )

        application.add_error_handler(error_handler)

        logger.info("Bot이 준비되었습니다.")

        await application.initialize()
        await application.start()
        await application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES
        )

        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Bot 종료 중...")
        finally:
            stop_scheduler()
            await application.updater.stop()
            await application.stop()
            await application.shutdown()

    logger.info("Telegram Bot 시작...")
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()

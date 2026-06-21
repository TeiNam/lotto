"""Telegram Bot 핸들러

사용자가 Telegram Bot과 대화하면서 로또 예측을 생성하고 결과를 확인할 수 있습니다.
"""

import asyncio
import logging
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional

from telegram import Update, Bot, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    MessageHandler, CallbackQueryHandler, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_ADMIN_IDS,
    DHL_USERNAME, DHL_PASSWORD,
)
from database.repositories.lotto_repository import AsyncLottoRepository
from services.data_service import AsyncDataService
from services.random_generator import RandomGenerator
from services.duplicate_checker import DuplicateChecker
from services.simplified_prediction_service import SimplifiedPredictionService
from services.lottery_service import LotteryService
from services.dhlottery_client import DhLotteryClient
from utils.exceptions import DhLotteryError

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


async def update_lottery_results(retry_count: int = 0):
    """토요일 밤 9시 당첨번호 자동 업데이트 및 결과 알림
    
    Args:
        retry_count: 현재 재시도 횟수 (최대 3회)
    """
    max_retries = 3
    logger.info(f"당첨번호 자동 업데이트 시작 (시도 {retry_count + 1}/{max_retries + 1})")

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

                # 당첨번호 알림 발송 (보너스 번호 포함)
                numbers = [last_draw[str(i)] for i in range(1, 7)]
                numbers_str = ", ".join(str(n) for n in sorted(numbers))
                bonus = last_draw.get('bonus')
                bonus_str = f"\n🎯 보너스 번호: {bonus}" if bonus else ""

                message = (
                    f"🏆 {last_draw_no}회 당첨번호 업데이트\n\n"
                    f"🎱 당첨 번호: [{numbers_str}]{bonus_str}\n"
                    f"⏰ 업데이트 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"📊 /result 명령어로 내 예측 번호와 당첨 결과를 확인해보세요!"
                )

                sent = await send_message_with_retry(
                    bot, TELEGRAM_CHAT_ID, message
                )
                if not sent:
                    logger.error("당첨번호 알림 발송 최종 실패")
        else:
            logger.warning("당첨번호 업데이트 실패 (미발표 또는 오류)")

            # 재시도 가능하면 10분 후 재시도 스케줄 등록
            if retry_count < max_retries:
                next_retry = retry_count + 1
                retry_minutes = 10
                logger.info(f"{retry_minutes}분 후 재시도 예정 ({next_retry}/{max_retries})")

                from datetime import timedelta
                run_time = datetime.now() + timedelta(minutes=retry_minutes)
                scheduler.add_job(
                    update_lottery_results,
                    'date',
                    run_date=run_time,
                    args=[next_retry],
                    id=f'lottery_update_retry_{next_retry}',
                    name=f'당첨번호 업데이트 재시도 ({next_retry}/{max_retries})',
                    replace_existing=True
                )

                fail_message = (
                    f"⚠️ 당첨번호 업데이트 실패 (시도 {retry_count + 1}/{max_retries + 1})\n\n"
                    f"아직 발표되지 않았거나 조회 중 오류가 발생했습니다.\n"
                    f"{retry_minutes}분 후 재시도합니다."
                )
                await send_message_with_retry(bot, TELEGRAM_CHAT_ID, fail_message)
            else:
                fail_message = (
                    "❌ 당첨번호 업데이트 최종 실패\n\n"
                    f"총 {max_retries + 1}회 시도했지만 실패했습니다.\n"
                    "/update 명령어로 수동 업데이트해주세요."
                )
                await send_message_with_retry(bot, TELEGRAM_CHAT_ID, fail_message)

    except Exception as e:
        logger.error(f"당첨번호 업데이트 중 오류: {e}", exc_info=True)

        error_message = (
            "❌ 당첨번호 업데이트 오류\n\n"
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
                "❌ 주간 예측 생성 실패\n\n예측 번호를 생성하지 못했습니다."
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
            f"🎰 {next_draw_no}회 주간 예측",
            "",
            f"⏰ 생성 시각: {timestamp}",
            f"📊 생성 개수: {len(predictions)}개",
            f"💾 저장 완료: {saved_count}개",
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
            "❌ 주간 예측 생성 오류\n\n"
            f"오류: {str(e)[:200]}"
        )
        await send_message_with_retry(bot, TELEGRAM_CHAT_ID, error_message)

async def send_monday_reminder():
    """월요일 오전 10시: 한 주 시작 알림"""
    logger.info("월요일 알림 발송")
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    last_draw = await AsyncLottoRepository.get_last_draw()
    next_draw_no = last_draw['no'] + 1 if last_draw else "?"

    message = (
        f"🌅 한 주가 시작되었어요!\n\n"
        f"🎱 이번주 로또 {next_draw_no}회 번호를 생성해볼까요?\n"
        f"👉 /generate 명령어로 번호를 생성해보세요!"
    )
    sent = await send_message_with_retry(bot, TELEGRAM_CHAT_ID, message)
    if not sent:
        logger.error("월요일 알림 발송 최종 실패")


async def send_friday_purchase_reminder():
    """금요일 오후 4시: 구매 알림"""
    logger.info("금요일 구매 알림 발송")
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    message = (
        "🛒 이번주 토요일이 오기전에 로또 구매하러 갑시다!\n\n"
        "📋 /mylist 로 내 번호를 확인하세요."
    )
    sent = await send_message_with_retry(bot, TELEGRAM_CHAT_ID, message)
    if not sent:
        logger.error("금요일 구매 알림 발송 최종 실패")


async def send_saturday_purchase_reminder():
    """토요일 오후 6시: 마감 임박 알림"""
    logger.info("토요일 구매 마감 알림 발송")
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    message = (
        "🚨 아직 안늦었어요! 빨리 구매하러 갑시다!\n\n"
        "⏰ 로또 판매 마감이 얼마 남지 않았어요.\n"
        "📋 /mylist 로 내 번호를 확인하세요."
    )
    sent = await send_message_with_retry(bot, TELEGRAM_CHAT_ID, message)
    if not sent:
        logger.error("토요일 구매 마감 알림 발송 최종 실패")



def setup_scheduler():
    """스케줄러 설정 (한국 시간 기준)"""
    global scheduler

    from pytz import timezone as pytz_timezone
    kst = pytz_timezone('Asia/Seoul')
    scheduler = AsyncIOScheduler(timezone=kst)

    # 매주 월요일 오전 10시: 한 주 시작 알림
    scheduler.add_job(
        send_monday_reminder,
        CronTrigger(day_of_week='mon', hour=10, minute=0),
        id='monday_reminder',
        name='월요일 오전 10시 한 주 시작 알림'
    )

    # 매주 금요일 정오: 예측 자동 생성
    scheduler.add_job(
        generate_weekly_predictions,
        CronTrigger(day_of_week='fri', hour=12, minute=0),
        id='friday_prediction_generation',
        name='금요일 정오 예측 생성'
    )

    # 매주 금요일 오후 4시: 구매 알림
    scheduler.add_job(
        send_friday_purchase_reminder,
        CronTrigger(day_of_week='fri', hour=16, minute=0),
        id='friday_purchase_reminder',
        name='금요일 오후 4시 구매 알림'
    )

    # 매주 토요일 오후 6시: 마감 임박 알림
    scheduler.add_job(
        send_saturday_purchase_reminder,
        CronTrigger(day_of_week='sat', hour=18, minute=0),
        id='saturday_purchase_reminder',
        name='토요일 오후 6시 구매 마감 알림'
    )

    # 매주 토요일 밤 9시: 당첨번호 업데이트
    scheduler.add_job(
        update_lottery_results,
        CronTrigger(day_of_week='sat', hour=21, minute=0),
        id='saturday_lottery_update',
        name='토요일 밤 9시 당첨번호 업데이트'
    )

    scheduler.start()
    logger.info("스케줄러 시작됨 (timezone: Asia/Seoul)")
    logger.info("  - 매주 월요일 10:00: 한 주 시작 알림")
    logger.info("  - 매주 금요일 12:00: 예측 생성 및 텔레그램 전송")
    logger.info("  - 매주 금요일 16:00: 구매 알림")
    logger.info("  - 매주 토요일 18:00: 구매 마감 알림")
    logger.info("  - 매주 토요일 21:00: 당첨번호 업데이트 (실패 시 10분 간격 최대 3회 재시도)")

    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        if next_run:
            logger.info(
                f"  [{job.name}] 다음 실행: "
                f"{next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}"
            )


def stop_scheduler():
    """스케줄러 중지"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        logger.info("스케줄러 중지됨")


# -- 명령어 핸들러 --

def restricted(func):
    """관리자(allowlist) 전용 핸들러로 제한하는 데코레이터

    TELEGRAM_ADMIN_IDS에 없는 사용자의 모든 명령/콜백을 차단한다.
    """
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        uid = user.id if user else None
        if uid not in TELEGRAM_ADMIN_IDS:
            logger.warning(f"비인가 접근 차단: user_id={uid}, username={getattr(user, 'username', None)}")
            if update.callback_query:
                await update.callback_query.answer("⛔ 권한이 없습니다.", show_alert=True)
            elif update.message:
                await update.message.reply_text(
                    "⛔ 이 봇은 관리자 전용입니다.\n"
                    f"당신의 user_id: `{uid}`\n\n"
                    "관리자라면 이 값을 .env의 TELEGRAM_ADMIN_IDS에 추가하세요.",
                    parse_mode="Markdown",
                )
            return
        return await func(update, context, *args, **kwargs)
    return wrapped


@restricted
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """시작 명령어 핸들러"""
    welcome_message = (
        "🎰 로또 예측 봇 🎰\n\n"
        "사용 가능한 명령어:\n"
        "🔮 /generate - 5개 조합 생성 (기본)\n"
        "🔮 /generate [개수] - 원하는 개수만큼 생성 (최대 20개)\n"
        "📋 /mylist - 이번 회차 생성된 전체 번호 보기\n"
        "🏆 /winning - 최신 회차 당첨 번호 확인\n"
        "📊 /result - 내 예측과 당첨 번호 매칭 확인\n"
        "📊 /result [회차] - 특정 회차 결과 확인\n"
        "🔄 /update - 최신 당첨번호 수동 업데이트\n"
        "❓ /help - 명령어 안내\n"
        "🏠 /start - 시작 메시지 표시"
    )
    keyboard = [[InlineKeyboardButton("☕ 후원하기 (카카오페이)", url="https://qr.kakaopay.com/Ej74xpc815dc06149")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)


@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """도움말 명령어 핸들러"""
    help_message = (
        "📖 명령어 안내\n\n"
        "🔮 예측 생성:\n"
        "  /generate - 5개 조합 생성 (기본)\n"
        "  /generate [개수] - 원하는 개수만큼 생성 (최대 20개)\n"
        "  예: /generate 10\n\n"
        "📋 내 번호 확인:\n"
        "  /mylist - 이번 회차 생성된 전체 번호 보기\n\n"
        "🏆 당첨 확인:\n"
        "  /winning - 최신 회차 당첨 번호 확인\n"
        "  /update - 최신 당첨번호 수동 업데이트\n\n"
        "📊 결과 확인:\n"
        "  /result - 내가 생성한 번호와 당첨 번호 매칭 확인\n"
        "  /result [회차] - 특정 회차 결과 확인\n"
        "  예: /result 1150\n\n"
        "⚙️ 기타:\n"
        "  /help - 이 메시지 표시\n"
        "  /start - 시작 메시지 표시\n\n"
        "⏰ 참고: 당첨 번호는 매주 토요일 밤 9시에 자동 업데이트됩니다."
    )
    await update.message.reply_text(help_message)


@restricted
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
            f"🔮 {num_predictions}개 조합 생성 중..."
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
            f"🎰 {next_draw_no}회 예측 결과",
            "",
            f"⏰ 생성 시각: {timestamp}",
            f"📊 생성 개수: {len(predictions)}개",
            f"💾 저장 완료: {saved_count}개",
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


@restricted
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
            f"📋 {next_draw_no}회 내 예측 번호 전체 목록",
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

def _determine_rank(matches: int, bonus_match: bool) -> str:
    """로또 등수 판정

    Args:
        matches: 당첨 번호와 일치하는 개수 (보너스 제외, 1~6번 기준)
        bonus_match: 보너스 번호 일치 여부

    Returns:
        등수 문자열 (1등~5등 또는 낙첨)
    """
    if matches == 6:
        return "1등"
    elif matches == 5 and bonus_match:
        return "2등"
    elif matches == 5:
        return "3등"
    elif matches == 4:
        return "4등"
    elif matches == 3:
        return "5등"
    else:
        return "낙첨"



@restricted
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

        # 날짜만 표시 (시간 제거)
        if hasattr(draw_date, 'strftime'):
            draw_date_str = draw_date.strftime('%Y-%m-%d (토)')
        else:
            draw_date_str = str(draw_date).split(' ')[0] + ' (토)'

        numbers_str = ", ".join(str(n) for n in sorted(numbers))
        bonus = last_draw.get('bonus')
        bonus_str = f"\n🎯 보너스 번호: {bonus}" if bonus else ""

        message = (
            f"🏆 {draw_no}회 당첨 번호\n\n"
            f"📅 추첨일: {draw_date_str}\n"
            f"🎱 당첨 번호: [{numbers_str}]{bonus_str}\n\n"
            f"다음 회차는 {draw_no + 1}회입니다."
        )

        await update.message.reply_text(message)

    except Exception as e:
        logger.error(f"당첨 번호 조회 오류: {e}", exc_info=True)
        await update.message.reply_text(
            f"당첨 번호 조회 중 오류가 발생했습니다.\n{str(e)}"
        )


@restricted
async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """수동 당첨번호 업데이트 명령어 핸들러"""
    try:
        await update.message.reply_text("🔄 최신 당첨번호 업데이트 중...")

        success = await LotteryService.update_latest_draw()

        if success:
            last_draw = await AsyncLottoRepository.get_last_draw()
            if last_draw:
                draw_no = last_draw['no']
                numbers = [last_draw[str(i)] for i in range(1, 7)]
                numbers_str = ", ".join(str(n) for n in sorted(numbers))
                bonus = last_draw.get('bonus')
                bonus_str = f"\n🎯 보너스 번호: {bonus}" if bonus else ""

                message = (
                    f"✅ 당첨번호 업데이트 완료\n\n"
                    f"🏆 {draw_no}회 당첨 번호\n"
                    f"🎱 [{numbers_str}]{bonus_str}"
                )
                await update.message.reply_text(message)
            else:
                await update.message.reply_text("✅ 업데이트 성공했지만 데이터 조회에 실패했습니다.")
        else:
            await update.message.reply_text(
                "⚠️ 업데이트 실패\n\n"
                "아직 발표되지 않았거나 이미 최신 상태입니다."
            )

    except Exception as e:
        logger.error(f"수동 당첨번호 업데이트 오류: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 업데이트 중 오류 발생\n{str(e)}")


@restricted
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

        # 당첨 번호 조회 (보너스 번호 포함)
        winning_data = await _get_winning_numbers(draw_no)
        if not winning_data:
            await update.message.reply_text(
                f"{draw_no}회차 당첨 번호를 찾을 수 없습니다."
            )
            return

        winning_numbers = winning_data["numbers"]
        bonus_number = winning_data["bonus"]

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

        # 매칭 결과 계산 (보너스 번호 매칭 포함)
        winning_set = set(winning_numbers)
        results = []
        for pred in my_predictions:
            pred_numbers = set(pred['numbers'])
            matches = len(pred_numbers & winning_set)
            bonus_match = bonus_number in pred_numbers if bonus_number else False
            rank = _determine_rank(matches, bonus_match)
            results.append((pred['numbers'], matches, bonus_match, rank))

        # 등수 우선, 같은 등수면 매칭 수 내림차순
        rank_order = {"1등": 1, "2등": 2, "3등": 3, "4등": 4, "5등": 5, "낙첨": 6}
        results.sort(key=lambda x: (rank_order.get(x[3], 99), -x[1]))

        winning_str = ", ".join(str(n) for n in sorted(winning_numbers))
        bonus_str = f" + 보너스: {bonus_number}" if bonus_number else ""

        message_lines = [
            f"📊 {draw_no}회차 결과 확인",
            "",
            f"🎱 당첨 번호: [{winning_str}]{bonus_str}",
            f"🔮 내 예측: {len(my_predictions)}개",
            ""
        ]

        # 최고 등수 판정
        best_rank = results[0][3] if results else "낙첨"
        best_match = results[0][1] if results else 0

        if best_rank != "낙첨":
            message_lines.append(f"🎉 최고 결과: {best_match}개 일치 → {best_rank}")
            if best_rank in ("1등", "2등", "3등", "4등"):
                message_lines.append("")
                message_lines.append("🍻 앱 개발자에게 한 턱 쏘는걸 잊지 마세요!")
            message_lines.append("")

        message_lines.append("[상세 결과]")
        # 전체 결과 표시
        for idx, (numbers, matches, bonus_match, rank) in enumerate(results, 1):
            numbers_str = ", ".join(str(n) for n in numbers)
            if rank != "낙첨":
                mark = "🏆" if rank in ("1등", "2등") else "✅"
                bonus_info = " (보너스⭕)" if bonus_match and matches == 5 else ""
                message_lines.append(
                    f"{idx}. [{numbers_str}] - {matches}개 일치{bonus_info} {mark} {rank}"
                )
            else:
                mark = "✅" if matches >= 3 else "❌"
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


async def _get_winning_numbers(draw_no: int) -> Optional[Dict[str, Any]]:
    """특정 회차의 당첨 번호 및 보너스 번호 조회

    Returns:
        {"numbers": [1,2,3,4,5,6], "bonus": 7} 또는 None
    """
    try:
        from database.connector import AsyncDatabaseConnector
        query = """
        SELECT `1`, `2`, `3`, `4`, `5`, `6`, bonus
        FROM result
        WHERE no = %s
        """
        results = await AsyncDatabaseConnector.execute_query(
            query, (draw_no,)
        )

        if results and len(results) > 0:
            row = results[0]
            numbers = [row[str(i)] for i in range(1, 7)]
            bonus = row.get('bonus')
            return {"numbers": numbers, "bonus": bonus}

        return None

    except Exception as e:
        logger.error(f"당첨 번호 조회 오류: {e}")
        return None


# --- 동행복권 잔액조회 / 구매 ---

def _dhl_get_balance() -> Dict[str, int]:
    """(blocking) 동행복권 로그인 후 예치금 조회"""
    client = DhLotteryClient(DHL_USERNAME, DHL_PASSWORD)
    return client.get_balance()


def _dhl_buy(tickets: List[Dict]) -> List[Dict]:
    """(blocking) 동행복권 로그인 후 로또645 구매"""
    client = DhLotteryClient(DHL_USERNAME, DHL_PASSWORD)
    return client.buy_lotto645(tickets)


def _dhl_buy_list(start_date=None, end_date=None) -> List[Dict]:
    """(blocking) 동행복권 로그인 후 구매 내역 조회"""
    client = DhLotteryClient(DHL_USERNAME, DHL_PASSWORD)
    return client.get_buy_list(start_date, end_date)


@restricted
async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """동행복권 예치금 잔액 조회"""
    if not (DHL_USERNAME and DHL_PASSWORD):
        await update.message.reply_text(
            "동행복권 계정이 설정되지 않았습니다. (.env의 DHL_USERNAME/DHL_PASSWORD)"
        )
        return
    msg = await update.message.reply_text("💰 예치금 조회 중...")
    try:
        bal = await asyncio.to_thread(_dhl_get_balance)
        await msg.edit_text(
            "💰 동행복권 예치금\n\n"
            f"총 예치금: {bal['total']:,}원\n"
            f"구매가능 금액: {bal['purchasable']:,}원\n"
            f"예약구매 금액: {bal['reserved']:,}원\n"
            f"출금신청중: {bal['withdrawing']:,}원"
        )
    except DhLotteryError as e:
        await msg.edit_text(f"❌ 예치금 조회 실패\n{e.message}")
    except Exception as e:
        logger.error(f"예치금 조회 오류: {e}", exc_info=True)
        await msg.edit_text("❌ 예치금 조회 중 알 수 없는 오류가 발생했습니다.")


@restricted
async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """로또645 구매 (잔액 확인 후 확인 절차를 거쳐 구매)

    /buy           : 이번 회차 내 추천번호(/mylist) 최대 5장을 수동 구매
    /buy auto [개수] : 자동 [개수]장 구매 (기본 5, 최대 5)
    """
    if not (DHL_USERNAME and DHL_PASSWORD):
        await update.message.reply_text(
            "동행복권 계정이 설정되지 않았습니다. (.env의 DHL_USERNAME/DHL_PASSWORD)"
        )
        return

    args = context.args or []
    tickets: List[Dict] = []
    preview_lines: List[str] = []

    if args and args[0].lower() == "auto":
        count = 5
        if len(args) > 1:
            try:
                count = int(args[1])
            except ValueError:
                await update.message.reply_text("개수는 숫자여야 합니다. 예: /buy auto 3")
                return
        if not 1 <= count <= 5:
            await update.message.reply_text("구매 매수는 1~5장입니다.")
            return
        tickets = [{"mode": "auto", "numbers": []} for _ in range(count)]
        preview_lines = [f"{i+1}. 자동" for i in range(count)]
    else:
        last_draw = await AsyncLottoRepository.get_last_draw()
        if not last_draw:
            await update.message.reply_text("당첨 번호 정보를 찾을 수 없습니다.")
            return
        next_no = last_draw["no"] + 1
        preds = await AsyncLottoRepository.get_recommendations_for_draw(
            next_no, user_id=update.effective_user.id
        )
        if not preds:
            await update.message.reply_text(
                f"{next_no}회차 추천번호가 없습니다.\n"
                "/generate 로 먼저 생성하거나 /buy auto 로 자동 구매하세요."
            )
            return
        chosen = preds[:5]  # 최대 5장
        tickets = [{"mode": "manual", "numbers": p["numbers"]} for p in chosen]
        preview_lines = [
            f"{i+1}. [{', '.join(map(str, p['numbers']))}] 수동"
            for i, p in enumerate(chosen)
        ]

    cost = 1000 * len(tickets)

    # 잔액 확인 (돈이 있을 때만 구매)
    try:
        bal = await asyncio.to_thread(_dhl_get_balance)
    except DhLotteryError as e:
        await update.message.reply_text(f"❌ 예치금 조회 실패\n{e.message}")
        return

    if bal["purchasable"] < cost:
        await update.message.reply_text(
            "❌ 예치금이 부족합니다.\n"
            f"구매가능: {bal['purchasable']:,}원 / 필요: {cost:,}원"
        )
        return

    # 구매 확정 전 확인 (금전 거래이므로 명시적 확인 필수)
    context.user_data["pending_buy"] = tickets
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ 구매 확정", callback_data="buy_confirm"),
        InlineKeyboardButton("❌ 취소", callback_data="buy_cancel"),
    ]])
    await update.message.reply_text(
        f"🛒 구매 확인 ({len(tickets)}장 / {cost:,}원)\n\n"
        + "\n".join(preview_lines)
        + f"\n\n구매가능 잔액: {bal['purchasable']:,}원\n\n진행할까요?",
        reply_markup=keyboard,
    )


@restricted
async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """구매 확정/취소 콜백 처리"""
    query = update.callback_query
    await query.answer()

    if query.data == "buy_cancel":
        context.user_data.pop("pending_buy", None)
        await query.edit_message_text("구매가 취소되었습니다.")
        return

    tickets = context.user_data.pop("pending_buy", None)
    if not tickets:
        await query.edit_message_text("구매 정보가 만료되었습니다. /buy 를 다시 실행해주세요.")
        return

    await query.edit_message_text("🛒 구매 진행 중...")
    try:
        slots = await asyncio.to_thread(_dhl_buy, tickets)
        lines = ["✅ 구매 완료!", ""]
        for s in slots:
            lines.append(f"[{s['slot']}] {s['mode']}: {', '.join(s['numbers'])}")
        await query.edit_message_text("\n".join(lines))
        logger.info(f"로또 구매 완료: {len(slots)}장, user_id={update.effective_user.id}")
    except DhLotteryError as e:
        await query.edit_message_text(f"❌ 구매 실패\n{e.message}")
    except Exception as e:
        logger.error(f"구매 오류: {e}", exc_info=True)
        await query.edit_message_text("❌ 구매 중 알 수 없는 오류가 발생했습니다.")


@restricted
async def buylist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """구매 내역 조회 (기본 최근 14일)

    /buylist            : 최근 14일 구매 내역
    /buylist 20250101 20250131 : 기간 지정(YYYYMMDD)
    """
    if not (DHL_USERNAME and DHL_PASSWORD):
        await update.message.reply_text(
            "동행복권 계정이 설정되지 않았습니다. (.env의 DHL_USERNAME/DHL_PASSWORD)"
        )
        return

    args = context.args or []
    start_date = args[0] if len(args) >= 1 else None
    end_date = args[1] if len(args) >= 2 else None

    msg = await update.message.reply_text("📜 구매 내역 조회 중...")
    try:
        rows = await asyncio.to_thread(_dhl_buy_list, start_date, end_date)
        if not rows:
            await msg.edit_text("해당 기간에 구매 내역이 없습니다.")
            return

        lines = [f"📜 구매 내역 ({len(rows)}건)", ""]
        for r in rows:
            amount = r["amount"]
            amt_str = f" / 당첨금 {amount:,}원" if amount else ""
            lines.append(
                f"• {r['date']} {r['round']}회 {r['name']}\n"
                f"  매수 {r['qty']} · {r['result']}{amt_str}"
            )
        text = "\n".join(lines)
        # 텔레그램 메시지 길이 제한 대응
        if len(text) > 4000:
            text = text[:3900] + "\n\n…(이하 생략, 기간을 좁혀 조회하세요)"
        await msg.edit_text(text)
    except DhLotteryError as e:
        await msg.edit_text(f"❌ 구매 내역 조회 실패\n{e.message}")
    except Exception as e:
        logger.error(f"구매 내역 조회 오류: {e}", exc_info=True)
        await msg.edit_text("❌ 구매 내역 조회 중 알 수 없는 오류가 발생했습니다.")


@restricted
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """알 수 없는 명령어 핸들러"""
    message = (
        "❓ 알 수 없는 명령어입니다.\n\n"
        "사용 가능한 명령어:\n"
        "🔮 /generate - 예측 생성 (기본 5개)\n"
        "🔮 /generate [개수] - 원하는 개수만큼 생성 (최대 20개)\n"
        "📋 /mylist - 이번 회차 내 번호 보기\n"
        "🏆 /winning - 당첨 번호 확인\n"
        "🔄 /update - 최신 당첨번호 수동 업데이트\n"
        "📊 /result - 내 예측과 당첨 번호 매칭 확인\n"
        "📊 /result [회차] - 특정 회차 결과 확인\n"
        "❓ /help - 명령어 안내\n"
        "🏠 /start - 시작 메시지 표시"
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
        application.add_handler(CommandHandler("update", update_command))
        application.add_handler(CommandHandler("balance", balance_command))
        application.add_handler(CommandHandler("buy", buy_command))
        application.add_handler(CommandHandler("buylist", buylist_command))
        application.add_handler(CallbackQueryHandler(buy_callback, pattern="^buy_"))

        # 알 수 없는 명령어 핸들러
        application.add_handler(
            MessageHandler(filters.COMMAND, unknown_command)
        )

        application.add_error_handler(error_handler)

        logger.info("Bot이 준비되었습니다.")

        await application.initialize()

        # 봇 명령어 메뉴 자동 등록
        bot_commands = [
            BotCommand("start", "시작 메시지 표시"),
            BotCommand("generate", "예측 번호 생성"),
            BotCommand("mylist", "이번 회차 내 번호 보기"),
            BotCommand("winning", "당첨 번호 확인"),
            BotCommand("result", "결과 확인"),
            BotCommand("balance", "동행복권 예치금 조회"),
            BotCommand("buy", "로또645 구매"),
            BotCommand("buylist", "구매 내역 조회"),
            BotCommand("help", "명령어 안내"),
        ]
        await application.bot.set_my_commands(bot_commands)
        logger.info("봇 명령어 메뉴 등록 완료")

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

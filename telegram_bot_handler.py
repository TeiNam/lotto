"""Telegram Bot 핸들러

사용자가 Telegram Bot과 대화하면서 로또 예측을 생성하고 결과를 확인할 수 있습니다.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Set, Tuple
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from database.repositories.lotto_repository import AsyncLottoRepository
from services.data_service import AsyncDataService
from services.random_generator import RandomGenerator
from services.duplicate_checker import DuplicateChecker
from services.simplified_prediction_service import SimplifiedPredictionService
from services.lottery_service import LotteryService

# 로깅 설정
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 전역 서비스 인스턴스
data_service = None
prediction_service = None
scheduler = None


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
    
    # 데이터 로드
    last_draw = await AsyncLottoRepository.get_last_draw()
    if last_draw:
        last_draw_no = last_draw['no']
        start_no = max(1, last_draw_no - 9)
        await data_service.load_historical_data(start_no=start_no, end_no=last_draw_no)
        logger.info(f"데이터 로드 완료: {len(data_service.draws)}개 회차")


async def update_lottery_results():
    """토요일 밤 9시 당첨번호 자동 업데이트"""
    logger.info("🎰 당첨번호 자동 업데이트 시작")
    
    try:
        # 최신 회차 업데이트
        success = await LotteryService.update_latest_draw()
        
        if success:
            logger.info("✅ 당첨번호 업데이트 성공")
            
            # 데이터 서비스 새로고침
            last_draw = await AsyncLottoRepository.get_last_draw()
            if last_draw:
                last_draw_no = last_draw['no']
                start_no = max(1, last_draw_no - 9)
                await data_service.load_historical_data(start_no=start_no, end_no=last_draw_no)
                logger.info(f"데이터 새로고침 완료: {len(data_service.draws)}개 회차")
        else:
            logger.warning("⚠️ 당첨번호 업데이트 실패 (아직 발표되지 않았거나 오류)")
            
    except Exception as e:
        logger.error(f"❌ 당첨번호 업데이트 중 오류: {e}", exc_info=True)


async def generate_weekly_predictions():
    """금요일 정오 자동 예측 생성 및 텔레그램 전송"""
    logger.info("🎲 주간 예측 자동 생성 시작")
    
    try:
        # 예측 생성
        predictions = await prediction_service.generate_predictions(num_predictions=10)
        
        if not predictions:
            logger.error("예측 생성 실패")
            return
        
        # 다음 회차 번호
        last_draw = await AsyncLottoRepository.get_last_draw()
        next_draw_no = last_draw['no'] + 1 if last_draw else 1
        
        # 데이터베이스에 저장
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
        
        logger.info(f"✅ 예측 생성 완료: {saved_count}/{len(predictions)}개 저장")
        
        # 텔레그램으로 전송
        from telegram import Bot
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message_lines = [
            "🎰 주간 로또 예측 🎰",
            "",
            f"📅 생성 시각: {timestamp}",
            f"🎯 예측 회차: {next_draw_no}회",
            f"📊 생성 개수: {len(predictions)}개",
            f"💾 저장 완료: {saved_count}개",
            ""
        ]
        
        # 각 예측 번호 추가
        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        for idx, pred in enumerate(predictions, 1):
            emoji = number_emojis[idx - 1] if idx <= len(number_emojis) else f"{idx}."
            numbers_str = ", ".join(str(n) for n in pred.combination)
            message_lines.append(f"{emoji} [{numbers_str}]")
        
        message_lines.append("")
        message_lines.append("행운을 빕니다! 🍀")
        
        message = "\n".join(message_lines)
        
        # 메시지 전송
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(f"✅ 텔레그램 전송 완료 (chat_id: {TELEGRAM_CHAT_ID})")
        
    except Exception as e:
        logger.error(f"❌ 주간 예측 생성 중 오류: {e}", exc_info=True)


def setup_scheduler():
    """스케줄러 설정"""
    global scheduler
    
    scheduler = AsyncIOScheduler()
    
    # 매주 토요일 밤 9시에 당첨번호 업데이트
    scheduler.add_job(
        update_lottery_results,
        CronTrigger(day_of_week='sat', hour=21, minute=0),
        id='saturday_lottery_update',
        name='토요일 밤 9시 당첨번호 업데이트'
    )
    
    # 매주 금요일 정오에 예측 생성 및 텔레그램 전송
    scheduler.add_job(
        generate_weekly_predictions,
        CronTrigger(day_of_week='fri', hour=12, minute=0),
        id='friday_prediction_generation',
        name='금요일 정오 예측 생성'
    )
    
    scheduler.start()
    logger.info("📅 스케줄러 시작됨")
    logger.info("   - 매주 금요일 12:00: 예측 생성 및 텔레그램 전송")
    logger.info("   - 매주 토요일 21:00: 당첨번호 업데이트")
    
    # 다음 실행 시간 로깅
    jobs = scheduler.get_jobs()
    for job in jobs:
        next_run = job.next_run_time
        if next_run:
            logger.info(f"   [{job.name}] 다음 실행: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")


def stop_scheduler():
    """스케줄러 중지"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        logger.info("스케줄러 중지됨")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """시작 명령어 핸들러"""
    welcome_message = """
🎰 로또 예측 봇에 오신 것을 환영합니다! 🎰

사용 가능한 명령어:
/generate - 5개 조합 생성
/generate 10 - 10개 조합 생성
/winning - 최신 회차 당첨 번호 확인
/result - 내 예측과 당첨 번호 매칭 확인
/help - 명령어 안내

행운을 빕니다! 🍀
"""
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """도움말 명령어 핸들러"""
    help_message = """
📖 명령어 안내

🎲 예측 생성:
/generate - 5개 조합 생성 (기본)
/generate [개수] - 원하는 개수만큼 생성 (최대 20개)
예: /generate 10

🎯 당첨 확인:
/winning - 최신 회차 당첨 번호 확인

📊 결과 확인:
/result - 내가 생성한 번호와 당첨 번호 매칭 확인
/result [회차] - 특정 회차 결과 확인
예: /result 1150

❓ 기타:
/help - 이 메시지 표시
/start - 시작 메시지 표시

💡 참고:
당첨 번호는 매주 토요일 밤 9시에 자동으로 업데이트됩니다.
"""
    await update.message.reply_text(help_message)


async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """예측 생성 명령어 핸들러"""
    try:
        # 개수 파라미터 확인
        num_predictions = 5  # 기본값
        if context.args and len(context.args) > 0:
            try:
                num_predictions = int(context.args[0])
                if not 1 <= num_predictions <= 20:
                    await update.message.reply_text(
                        "❌ 생성 개수는 1~20 사이여야 합니다.\n예: /generate 10"
                    )
                    return
            except ValueError:
                await update.message.reply_text(
                    "❌ 올바른 숫자를 입력해주세요.\n예: /generate 10"
                )
                return
        
        # 로딩 메시지
        loading_msg = await update.message.reply_text(
            f"🎲 {num_predictions}개 조합 생성 중..."
        )
        
        # 예측 생성
        predictions = await prediction_service.generate_predictions(
            num_predictions=num_predictions
        )
        
        # 다음 회차 번호
        last_draw = await AsyncLottoRepository.get_last_draw()
        next_draw_no = last_draw['no'] + 1 if last_draw else 1
        
        # 데이터베이스에 저장
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
        
        # 결과 메시지 포맷팅
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message_lines = [
            "🎰 로또 예측 결과 🎰",
            "",
            f"📅 생성 시각: {timestamp}",
            f"🎯 예측 회차: {next_draw_no}회",
            f"📊 생성 개수: {len(predictions)}개",
            f"💾 저장 완료: {saved_count}개",
            ""
        ]
        
        # 각 예측 번호 추가
        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟",
                        "1️⃣1️⃣", "1️⃣2️⃣", "1️⃣3️⃣", "1️⃣4️⃣", "1️⃣5️⃣", "1️⃣6️⃣", "1️⃣7️⃣", "1️⃣8️⃣", "1️⃣9️⃣", "2️⃣0️⃣"]
        
        for idx, pred in enumerate(predictions, 1):
            emoji = number_emojis[idx - 1] if idx <= len(number_emojis) else f"{idx}."
            numbers_str = ", ".join(str(n) for n in pred.combination)
            message_lines.append(f"{emoji} [{numbers_str}]")
        
        message_lines.append("")
        message_lines.append("행운을 빕니다! 🍀")
        
        message = "\n".join(message_lines)
        
        # 로딩 메시지 삭제 후 결과 전송
        await loading_msg.delete()
        await update.message.reply_text(message)
        
        logger.info(f"예측 생성 완료: {num_predictions}개, 사용자: {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"예측 생성 오류: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ 예측 생성 중 오류가 발생했습니다.\n{str(e)}"
        )


async def check_winning_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """당첨 번호 확인 명령어 핸들러"""
    try:
        # 최신 회차 당첨 번호 조회
        last_draw = await AsyncLottoRepository.get_last_draw()
        
        if not last_draw:
            await update.message.reply_text("❌ 당첨 번호 정보를 찾을 수 없습니다.")
            return
        
        draw_no = last_draw['no']
        numbers = [
            last_draw['1'], last_draw['2'], last_draw['3'],
            last_draw['4'], last_draw['5'], last_draw['6']
        ]
        bonus = last_draw.get('bonus_num')  # bonus_num이 없을 수 있음
        draw_date = last_draw['create_at']
        
        # 메시지 포맷팅
        numbers_str = ", ".join(str(n) for n in sorted(numbers))
        
        message = f"""
🎯 최신 회차 당첨 번호 🎯

📅 회차: {draw_no}회
📆 추첨일: {draw_date}

🎰 당첨 번호: [{numbers_str}]"""
        
        if bonus:
            message += f"\n⭐ 보너스: {bonus}"
        
        message += f"\n\n다음 회차는 {draw_no + 1}회입니다."
        
        await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"당첨 번호 조회 오류: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ 당첨 번호 조회 중 오류가 발생했습니다.\n{str(e)}"
        )


async def check_result_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """결과 확인 명령어 핸들러"""
    try:
        # 회차 파라미터 확인
        target_draw_no = None
        if context.args and len(context.args) > 0:
            try:
                target_draw_no = int(context.args[0])
            except ValueError:
                await update.message.reply_text(
                    "❌ 올바른 회차 번호를 입력해주세요.\n예: /result 1206"
                )
                return
        
        # 회차 번호가 없으면 최신 회차 사용
        if target_draw_no is None:
            last_draw = await AsyncLottoRepository.get_last_draw()
            if not last_draw:
                await update.message.reply_text("❌ 당첨 번호 정보를 찾을 수 없습니다.")
                return
            target_draw_no = last_draw['no']
        
        # 해당 회차의 예측은 next_no로 저장되어 있음
        draw_no = target_draw_no
        
        # 당첨 번호 조회
        winning_numbers = await get_winning_numbers(draw_no)
        if not winning_numbers:
            await update.message.reply_text(
                f"❌ {draw_no}회차 당첨 번호를 찾을 수 없습니다."
            )
            return
        
        # 내 예측 번호 조회
        my_predictions = await AsyncLottoRepository.get_recommendations_for_draw(draw_no)
        
        if not my_predictions:
            await update.message.reply_text(
                f"📭 {draw_no}회차에 생성한 예측이 없습니다."
            )
            return
        
        # 매칭 결과 계산
        results = []
        for pred in my_predictions:
            pred_numbers = set(pred['numbers'])
            winning_set = set(winning_numbers)
            matches = len(pred_numbers & winning_set)
            results.append((pred['numbers'], matches))
        
        # 결과 정렬 (매칭 개수 많은 순)
        results.sort(key=lambda x: x[1], reverse=True)
        
        # 메시지 포맷팅
        winning_str = ", ".join(str(n) for n in sorted(winning_numbers))
        
        message_lines = [
            f"📊 {draw_no}회차 결과 확인 📊",
            "",
            f"🎯 당첨 번호: [{winning_str}]",
            f"📝 내 예측: {len(my_predictions)}개",
            ""
        ]
        
        # 등수 판정
        rank_info = {
            6: "🏆 1등",
            5: "🥈 2등/3등",
            4: "🥉 4등",
            3: "🎖️ 5등",
        }
        
        best_match = results[0][1] if results else 0
        
        if best_match >= 3:
            message_lines.append(f"🎉 최고 매칭: {best_match}개 일치!")
            if best_match in rank_info:
                message_lines.append(f"   {rank_info[best_match]}")
            message_lines.append("")
        
        # 각 예측 결과
        message_lines.append("📋 상세 결과:")
        for idx, (numbers, matches) in enumerate(results[:10], 1):  # 최대 10개만 표시
            numbers_str = ", ".join(str(n) for n in numbers)
            match_emoji = "✅" if matches >= 3 else "❌"
            message_lines.append(f"{idx}. [{numbers_str}] - {matches}개 일치 {match_emoji}")
        
        if len(results) > 10:
            message_lines.append(f"\n... 외 {len(results) - 10}개")
        
        message = "\n".join(message_lines)
        await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"결과 확인 오류: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ 결과 확인 중 오류가 발생했습니다.\n{str(e)}"
        )


async def get_winning_numbers(draw_no: int) -> List[int]:
    """특정 회차의 당첨 번호 조회"""
    try:
        query = """
        SELECT `1`, `2`, `3`, `4`, `5`, `6`
        FROM result
        WHERE no = %s
        """
        from database.connector import AsyncDatabaseConnector
        results = await AsyncDatabaseConnector.execute_query(query, (draw_no,))
        
        if results and len(results) > 0:
            row = results[0]
            return [row['1'], row['2'], row['3'], row['4'], row['5'], row['6']]
        
        return None
        
    except Exception as e:
        logger.error(f"당첨 번호 조회 오류: {e}")
        return None


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """알 수 없는 명령어 핸들러"""
    message = """
❓ 알 수 없는 명령어입니다.

사용 가능한 명령어:
/generate - 예측 생성
/winning - 당첨 번호 확인
/result - 결과 확인
/help - 명령어 안내
"""
    await update.message.reply_text(message)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """에러 핸들러"""
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)


def main():
    """메인 함수"""
    async def run_bot():
        """Bot 실행 (비동기)"""
        # 서비스 초기화
        logger.info("서비스 초기화 중...")
        await initialize_services()
        logger.info("서비스 초기화 완료!")
        
        # 스케줄러 설정
        setup_scheduler()
        
        # Application 생성
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # 명령어 핸들러 등록
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("generate", generate_command))
        application.add_handler(CommandHandler("winning", check_winning_command))
        application.add_handler(CommandHandler("result", check_result_command))
        
        # 알 수 없는 명령어 핸들러
        application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
        
        # 에러 핸들러
        application.add_error_handler(error_handler)
        
        # Bot 시작
        logger.info("Bot이 준비되었습니다. 명령어를 입력하세요.")
        
        # Bot 초기화 및 실행
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        
        # Bot이 종료될 때까지 대기
        try:
            # 무한 대기
            await asyncio.Event().wait()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Bot 종료 중...")
        finally:
            stop_scheduler()
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
    
    # Bot 실행
    logger.info("Telegram Bot 시작...")
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()

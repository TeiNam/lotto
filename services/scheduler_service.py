# services/scheduler_service.py
import logging
import asyncio
from typing import Dict, Any, List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta

from services.prediction_service import AsyncPredictionService
from services.data_service import AsyncDataService
# TODO: SlackNotifier 제거됨 - Telegram으로 전환 예정
# from services.slack_service import SlackNotifier
from models.prediction import LottoPrediction
from utils.exceptions import SchedulerError, DataLoadError

logger = logging.getLogger("lotto_prediction")


class PredictionScheduler:
    """예측 자동화 스케줄러 서비스"""

    def __init__(
            self,
            data_service: AsyncDataService,
            prediction_service: AsyncPredictionService,
            slack_notifier=None  # TODO: Optional로 변경, Telegram으로 전환 예정
    ):
        self.data_service = data_service
        self.prediction_service = prediction_service
        self.slack_notifier = slack_notifier  # TODO: Telegram으로 전환 예정
        self.scheduler = AsyncIOScheduler()
        self.running = False

    async def start(self):
        """스케줄러 시작 (비동기)"""
        if self.running:
            logger.warning("스케줄러가 이미 실행 중입니다.")
            return

        try:
            # 현재 이벤트 루프 가져오기
            try:
                loop = asyncio.get_running_loop()
                logger.info("기존 이벤트 루프 사용")
            except RuntimeError:
                # 실행 중인 이벤트 루프가 없으면 새로 생성
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                logger.info("새 이벤트 루프 생성")

            # 스케줄러 작업 정의
            logger.info("스케줄러 작업 정의 시작...")

            # 월요일 오전 11시 예측 작업 스케줄링
            self.scheduler.add_job(
                self._run_prediction_job,
                CronTrigger(day_of_week='mon', hour=11, minute=0),
                id='monday_prediction',
                kwargs={'count': 5, 'job_name': '월요일 오전 11시'}
            )
            logger.info("월요일 오전 11시 예측 작업 스케줄링 완료")

            # 금요일 오후 3시 예측 작업 스케줄링
            self.scheduler.add_job(
                self._run_prediction_job,
                CronTrigger(day_of_week='fri', hour=15, minute=0),
                id='friday_prediction',
                kwargs={'count': 5, 'job_name': '금요일 오후 3시'}
            )
            logger.info("금요일 오후 3시 예측 작업 스케줄링 완료")

            # 토요일 밤 9시 당첨번호 업데이트 작업 스케줄링
            self.scheduler.add_job(
                self._run_lottery_update_job,
                CronTrigger(day_of_week='sat', hour=21, minute=0),
                id='saturday_lottery_update',
                kwargs={'job_name': '토요일 밤 9시 당첨번호 업데이트'}
            )
            logger.info("토요일 밤 9시 당첨번호 업데이트 작업 스케줄링 완료")

            # 스케줄러 시작
            logger.info("스케줄러 시작 중...")
            self.scheduler.start()
            self.running = True
            logger.info("예측 스케줄러 시작됨 (월요일 11시, 금요일 15시, 토요일 21시)")

            # 다음 실행 시간 로깅
            next_runs = self.get_next_run_times()
            for job_id, next_run in next_runs.items():
                logger.info(f"작업 '{job_id}'의 다음 실행 시간: {next_run}")

        except Exception as e:
            logger.exception(f"스케줄러 시작 실패: {str(e)}")
            raise SchedulerError(f"스케줄러 시작 실패: {str(e)}")

    # 로또 당첨 정보 업데이트 작업 메서드 추가
    async def _run_lottery_update_job(self, job_name: str = "당첨번호 업데이트"):
        """로또 당첨 정보 업데이트 작업 실행 (비동기)"""
        logger.info(f"[{job_name}] 로또 당첨 정보 업데이트 작업 시작")

        try:
            from services.lottery_service import LotteryService
            from database.repositories.lotto_repository import AsyncLottoRepository

            # 최신 당첨 정보 업데이트
            success = await LotteryService.update_latest_draw()

            if success:
                logger.info(f"[{job_name}] 로또 당첨 정보 업데이트 성공")

                # 데이터 서비스 새로고침 (새 당첨 정보 반영)
                await self.data_service.load_historical_data()
                logger.info(f"[{job_name}] 예측 서비스 데이터 새로고침 완료")
                
                # 현재 업데이트된 회차 번호 확인
                last_draw = self.data_service.get_last_draw()
                if last_draw:
                    current_draw_no = last_draw.draw_no
                    logger.info(f"[{job_name}] 현재 당첨 정보 회차: {current_draw_no}")
                    
                    # 해당 회차의 예측 결과가 있는지 확인
                    prediction_count = await AsyncLottoRepository.execute_raw_query(
                        "SELECT COUNT(*) as count FROM recommand WHERE next_no = %s",
                        (current_draw_no,)
                    )
                    prediction_exists = prediction_count[0]['count'] > 0 if prediction_count else False
                    
                    if not prediction_exists:
                        logger.warning(f"[{job_name}] {current_draw_no}회차 예측 결과가 없습니다. 다음 회차 예측 생성 시도")
                        
                        # 예측 실행을 위한 다음 회차 번호 (현재 + 1)
                        next_draw_no = current_draw_no + 1
                        
                        # 예측 생성 실행 (바로 다음 회차)
                        try:
                            await self.run_prediction_now(count=5)
                            logger.info(f"[{job_name}] {next_draw_no}회차 예측 자동 생성 성공")
                        except Exception as pred_error:
                            logger.error(f"[{job_name}] 자동 예측 생성 실패: {pred_error}")
            else:
                logger.warning(f"[{job_name}] 로또 당첨 정보 업데이트 실패 (아직 발표되지 않았거나 API 오류)")

        except Exception as e:
            logger.exception(f"[{job_name}] 로또 당첨 정보 업데이트 중 오류 발생: {str(e)}")

    def stop(self):
        """스케줄러 중지"""
        if not self.running:
            logger.warning("스케줄러가 실행 중이 아닙니다.")
            return

        try:
            self.scheduler.shutdown()
            self.running = False
            logger.info("예측 스케줄러 중지됨")
        except Exception as e:
            logger.exception(f"스케줄러 중지 실패: {str(e)}")
            raise SchedulerError(f"스케줄러 중지 실패: {str(e)}")

    def get_next_run_times(self) -> Dict[str, str]:
        """다음 실행 예정 시간 조회"""
        if not self.running:
            return {"status": "not_running"}

        next_runs = {}
        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time
            if next_run:
                next_runs[job.id] = next_run.strftime("%Y-%m-%d %H:%M:%S")
            else:
                next_runs[job.id] = "not scheduled"

        return next_runs

    async def _run_prediction_job(self, count: int = 5, job_name: str = "정기 예측"):
        """예측 작업 실행 (비동기)"""
        logger.info(f"[{job_name}] 예측 작업 시작 (예측 개수: {count})")

        try:
            # 1. 최신 데이터 로드
            await self._load_latest_data()

            # 2. 예측 실행
            predictions, _ = await self.prediction_service.predict_next_draw(num_predictions=count)

            if not predictions:
                logger.error(f"[{job_name}] 예측 실패: 결과 없음")
                return

            logger.info(f"[{job_name}] {len(predictions)}개 예측 조합 생성 완료")

            # 3. 최신 회차 정보 확인
            last_draw = self.data_service.get_last_draw()
            if not last_draw:
                raise DataLoadError("최신 회차 정보를 찾을 수 없습니다")

            next_draw_no = last_draw.draw_no + 1

            # 4. 예측 결과를 슬랙 서비스에 맞게 변환
            prediction_dicts = [{
                "combination": pred.combination,
                "score": pred.score,
                "common_with_last": pred.common_with_last
            } for pred in predictions]

            # 5. 슬랙으로 전송
            success = await self.slack_notifier.send_prediction_notification(
                predictions=prediction_dicts,
                next_draw_no=next_draw_no
            )

            if success:
                logger.info(f"[{job_name}] 슬랙 알림 전송 완료 ({next_draw_no}회차)")
            else:
                logger.error(f"[{job_name}] 슬랙 알림 전송 실패")

            # 6. 데이터베이스에 예측 결과 저장
            try:
                from database.repositories.lotto_repository import AsyncLottoRepository

                success_count = 0
                for pred in predictions:
                    # recommand 테이블에 저장 (next_no 추가)
                    success = await AsyncLottoRepository.save_recommendation(
                        numbers=pred.combination,
                        next_no=next_draw_no
                    )
                    if success:
                        success_count += 1

                logger.info(f"[{job_name}] 예측 결과 {success_count}/{len(predictions)}개 DB 저장 완료 (예측 회차: {next_draw_no})")

                if success_count < len(predictions):
                    logger.warning(f"[{job_name}] {len(predictions) - success_count}개 예측 저장 실패")

            except Exception as e:
                logger.error(f"[{job_name}] 예측 결과 DB 저장 중 오류 발생: {str(e)}")
                # DB 저장 실패는 전체 작업 실패로 처리하지 않음

        except Exception as e:
            logger.exception(f"[{job_name}] 예측 작업 실행 중 오류 발생: {str(e)}")

    async def _load_latest_data(self):
        """최신 데이터 로드 (비동기)"""
        try:
            # 최신 회차 가져오기
            last_no = None
            from database.repositories.lotto_repository import AsyncLottoRepository

            last_draw_data = await AsyncLottoRepository.get_last_draw()
            if last_draw_data:
                last_no = last_draw_data["no"]
                logger.info(f"최신 회차 확인됨: {last_no}회")
            else:
                raise DataLoadError("최신 회차 정보를 찾을 수 없습니다")

            # 데이터 로드
            success = await self.data_service.load_historical_data(
                start_no=601,
                end_no=last_no
            )

            if not success:
                raise DataLoadError("역대 데이터 로드 실패")

            logger.info(f"총 {len(self.data_service.get_all_draws())}개 회차 데이터 로드 완료")

        except Exception as e:
            logger.exception(f"데이터 로드 중 오류 발생: {str(e)}")
            raise DataLoadError(f"데이터 로드 실패: {str(e)}")

    async def run_prediction_now(self, count: int = 5) -> Optional[List[Dict[str, Any]]]:
        """즉시 예측 실행 (수동 트리거용)"""
        try:
            # 1. 최신 데이터 로드
            await self._load_latest_data()

            # 2. 예측 실행
            predictions, _ = await self.prediction_service.predict_next_draw(num_predictions=count)

            if not predictions:
                logger.error("수동 예측 실패: 결과 없음")
                return None

            # 3. 최신 회차 정보 확인
            last_draw = self.data_service.get_last_draw()
            if not last_draw:
                raise DataLoadError("최신 회차 정보를 찾을 수 없습니다")

            next_draw_no = last_draw.draw_no + 1

            # 4. 예측 결과를 슬랙 서비스에 맞게 변환
            prediction_dicts = [{
                "combination": pred.combination,
                "score": pred.score,
                "common_with_last": pred.common_with_last
            } for pred in predictions]

            # 5. 슬랙으로 전송
            await self.slack_notifier.send_prediction_notification(
                predictions=prediction_dicts,
                next_draw_no=next_draw_no
            )

            logger.info(f"수동 예측 및 슬랙 알림 전송 완료 ({next_draw_no}회차, {len(predictions)}개)")

            # 6. 데이터베이스에 예측 결과 저장
            try:
                from database.repositories.lotto_repository import AsyncLottoRepository

                success_count = 0
                for pred in predictions:
                    # recommand 테이블에 저장 (next_no 추가)
                    success = await AsyncLottoRepository.save_recommendation(
                        numbers=pred.combination,
                        next_no=next_draw_no
                    )
                    if success:
                        success_count += 1

                logger.info(f"수동 예측 결과 {success_count}/{len(predictions)}개 DB 저장 완료 (예측 회차: {next_draw_no})")

                if success_count < len(predictions):
                    logger.warning(f"{len(predictions) - success_count}개 예측 저장 실패")

            except Exception as e:
                logger.error(f"예측 결과 DB 저장 중 오류 발생: {str(e)}")
                # DB 저장 실패는 전체 작업 실패로 처리하지 않음

            return prediction_dicts

        except Exception as e:
            logger.exception(f"수동 예측 실행 중 오류 발생: {str(e)}")
            return None
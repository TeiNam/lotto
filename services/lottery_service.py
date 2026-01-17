# services/lottery_service.py
import json
import logging
import aiohttp
import asyncio
import requests
import re
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup

from database.repositories.lotto_repository import AsyncLottoRepository
from utils.exceptions import DataLoadError

logger = logging.getLogger("lotto_prediction")


class LotteryService:
    """로또 당첨 정보 조회 서비스"""

    # lotto.oot.kr API URL (더 안정적)
    OOT_URL = "https://lotto.oot.kr/?round={draw_no}"
    
    # 동행복권 API URL (백업용)
    API_URL = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={draw_no}"

    @classmethod
    async def fetch_draw_result(cls, draw_no: int) -> Optional[Dict[str, Any]]:
        """지정된 회차의 로또 당첨 정보 조회 (lotto.oot.kr 사용)"""
        try:
            url = cls.OOT_URL.format(draw_no=draw_no)
            logger.info(f"로또 {draw_no}회차 당첨 정보 조회 요청 중: {url}")

            # requests 사용 (동기)
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"로또 당첨 정보 조회 실패 (HTTP {response.status_code})")
                return None

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 메타 태그에서 정보 추출
            meta_desc = soup.find('meta', {'name': 'description'})
            if not meta_desc:
                logger.error(f"로또 {draw_no}회차 메타 태그를 찾을 수 없음")
                return None
            
            content = meta_desc.get('content', '')
            
            # 정규표현식으로 당첨번호 추출
            number_pattern = r'당첨번호 로또번호 ([\d,]+)\s*\+\s*보너스 번호 (\d+)'
            match = re.search(number_pattern, content)
            
            if not match:
                logger.error(f"로또 {draw_no}회차 당첨번호 패턴을 찾을 수 없음")
                return None
            
            numbers_str = match.group(1)
            bonus_str = match.group(2)
            
            numbers = [int(n.strip()) for n in numbers_str.split(',')]
            bonus = int(bonus_str)
            
            # 추첨일 추출
            date_pattern = r'당첨결과 \(([^)]+)\)'
            date_match = re.search(date_pattern, content)
            draw_date = date_match.group(1) if date_match else ''
            
            # 동행복권 API 형식으로 변환
            data = {
                "returnValue": "success",
                "drwNoDate": draw_date,
                "drwtNo1": numbers[0],
                "drwtNo2": numbers[1],
                "drwtNo3": numbers[2],
                "drwtNo4": numbers[3],
                "drwtNo5": numbers[4],
                "drwtNo6": numbers[5],
                "bnusNo": bonus,
                "drwNo": draw_no
            }
            
            logger.info(f"로또 {draw_no}회차 당첨 정보 조회 성공 (lotto.oot.kr)")
            return data

        except Exception as e:
            logger.exception(f"로또 당첨 정보 조회 중 예상치 못한 오류: {e}")
            return None

    @classmethod
    async def save_draw_result(cls, draw_no: int) -> bool:
        """지정된 회차의 로또 당첨 정보 조회 후 데이터베이스 저장"""
        try:
            # 1. 로또 당첨 정보 조회 (lotto.oot.kr 사용)
            data = await cls.fetch_draw_result(draw_no)

            if not data:
                logger.error(f"로또 {draw_no}회차 당첨 정보 조회 실패")
                return False

            # 로그에 원본 데이터 출력
            logger.debug(f"로또 {draw_no}회차 당첨 정보 조회 결과: {data}")

            # 2. 당첨번호 및 보너스 번호 추출
            numbers = [
                data.get("drwtNo1"),
                data.get("drwtNo2"),
                data.get("drwtNo3"),
                data.get("drwtNo4"),
                data.get("drwtNo5"),
                data.get("drwtNo6")
            ]
            bonus_no = data.get("bnusNo")
            draw_date = data.get("drwNoDate", "")

            # 유효성 검증 (모든 번호가 1~45 사이 숫자인지)
            if not all(isinstance(n, int) and 1 <= n <= 45 for n in numbers):
                logger.error(f"로또 {draw_no}회차 당첨 번호 형식 오류: {numbers}")
                return False

            if not isinstance(bonus_no, int) or not (1 <= bonus_no <= 45):
                logger.error(f"로또 {draw_no}회차 보너스 번호 형식 오류: {bonus_no}")
                return False

            # 번호 정렬
            sorted_numbers = sorted(numbers)

            # 3. 예측 결과와 비교
            prediction_comparisons = await cls.get_prediction_comparison(draw_no, sorted_numbers)

            # 4. 이미 존재하는지 확인
            from database.repositories.lotto_repository import AsyncLottoRepository
            exists = await AsyncLottoRepository.check_draw_exists(draw_no)

            if exists:
                logger.info(f"로또 {draw_no}회차 당첨 정보가 이미 데이터베이스에 존재합니다")
                return True

            # 5. 데이터베이스에 저장 (1~6 번호만)
            success = await AsyncLottoRepository.save_draw_result(
                draw_no=draw_no,
                numbers=sorted_numbers
            )

            if success:
                logger.info(f"로또 {draw_no}회차 당첨 정보 저장 성공: {sorted_numbers}")
                return True
            else:
                logger.error(f"로또 {draw_no}회차 당첨 정보 저장 실패")
                return False

        except Exception as e:
            logger.exception(f"로또 {draw_no}회차 당첨 정보 저장 중 오류: {e}")
            return False

    @classmethod
    async def update_latest_draw(cls) -> bool:
        """최신 회차의 당첨 정보 조회 및 저장"""
        try:
            # 1. 현재 DB에 저장된 마지막 회차 조회
            last_draw = await AsyncLottoRepository.get_last_draw()

            if not last_draw:
                logger.warning("저장된 로또 당첨 정보가 없습니다")
                return False

            last_no = last_draw.get("no", 0)
            next_no = last_no + 1

            logger.info(f"현재 저장된 마지막 회차: {last_no}, 다음 회차: {next_no}")

            # 2. 다음 회차 당첨 정보 조회 및 저장
            success = await cls.save_draw_result(next_no)

            if success:
                logger.info(f"로또 {next_no}회차 당첨 정보 업데이트 성공")
                return True
            else:
                logger.warning(f"로또 {next_no}회차 당첨 정보가 아직 발표되지 않았거나 조회 실패")
                return False

        except Exception as e:
            logger.exception(f"최신 로또 당첨 정보 업데이트 중 오류: {e}")
            return False

    @classmethod
    async def get_prediction_comparison(cls, draw_no: int, winning_numbers: list) -> list:
        """해당 회차에 대한 예측 결과와 실제 당첨 번호 비교"""
        try:
            # 데이터베이스에서 해당 회차에 대한 예측 결과 조회
            from database.repositories.lotto_repository import AsyncLottoRepository

            # 회차 번호 정수로 확실히 변환
            draw_no = int(draw_no)
            
            logger.info(f"로또 {draw_no}회차 예측 결과 비교 시작")
            
            # 디버깅: 모든 회차 예측 확인
            all_predictions = await AsyncLottoRepository.execute_raw_query(
                "SELECT next_no, COUNT(*) as count FROM recommand GROUP BY next_no ORDER BY next_no"
            )
            prediction_counts = {r['next_no']: r['count'] for r in all_predictions} if all_predictions else {}
            logger.info(f"추천 테이블 회차별 예측 수: {prediction_counts}")
            
            # 정확히 현재 회차가 있는지 명시적 확인
            specific_check = await AsyncLottoRepository.execute_raw_query(
                "SELECT COUNT(*) as count FROM recommand WHERE next_no = %s",
                (draw_no,)
            )
            specific_count = specific_check[0]['count'] if specific_check else 0
            logger.info(f"로또 {draw_no}회차에 대한 예측 레코드 수: {specific_count}")
            
            # recommand 테이블에서 next_no가 현재 회차인 예측 결과 조회
            predictions = await AsyncLottoRepository.get_recommendations_for_draw(draw_no)
            
            if not predictions:
                logger.warning(f"로또 {draw_no}회차에 대한 예측 결과가 recommand 테이블에 없음")
                
                # 대체 방법: 이전 회차 예측이 다음 회차로 저장되었을 가능성
                prev_draw_no = draw_no - 1
                logger.info(f"이전 회차({prev_draw_no})를 다음 회차로 저장했을 가능성 확인")
                prev_predictions = await AsyncLottoRepository.get_recommendations_for_draw(prev_draw_no)
                
                if prev_predictions:
                    logger.info(f"이전 회차({prev_draw_no})에 대한 예측 결과 {len(prev_predictions)}개 찾음, 이를 사용합니다.")
                    predictions = prev_predictions
                else:
                    # 마지막 시도: 가장 최근 예측 결과 가져오기
                    latest_draw = await AsyncLottoRepository.execute_raw_query(
                        "SELECT next_no FROM recommand ORDER BY next_no DESC LIMIT 1"
                    )
                    if latest_draw and len(latest_draw) > 0:
                        latest_draw_no = latest_draw[0]['next_no']
                        logger.info(f"최신 예측 결과 회차({latest_draw_no}) 시도")
                        latest_predictions = await AsyncLottoRepository.get_recommendations_for_draw(latest_draw_no)
                        if latest_predictions:
                            logger.info(f"최신 회차({latest_draw_no})에 대한 예측 결과 {len(latest_predictions)}개 찾음, 이를 사용합니다.")
                            predictions = latest_predictions
                        else:
                            return []
                    else:
                        return []
            
            # 각 예측 결과와 당첨 번호 비교
            comparison_results = []
            winning_numbers_set = set(winning_numbers)
            
            for pred in predictions:
                pred_numbers = pred.get("numbers", [])
                if not pred_numbers:
                    continue
                    
                # 맞은 번호 개수 계산
                pred_numbers_set = set(pred_numbers)
                matched_count = len(pred_numbers_set.intersection(winning_numbers_set))
                
                comparison_results.append({
                    "prediction_numbers": pred_numbers,
                    "matched_count": matched_count,
                    "matched_numbers": list(pred_numbers_set.intersection(winning_numbers_set))
                })
            
            # 맞은 개수 순으로 정렬
            comparison_results.sort(key=lambda x: x["matched_count"], reverse=True)
            
            logger.info(f"예측 비교 결과: {len(comparison_results)}개 결과 생성")
            return comparison_results
            
        except Exception as e:
            logger.exception(f"예측 결과 비교 중 오류: {e}")
            return []
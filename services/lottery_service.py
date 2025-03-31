# services/lottery_service.py
import json
import logging
import aiohttp
import asyncio
from typing import Dict, Any, Optional, List

from database.repositories.lotto_repository import AsyncLottoRepository
from utils.exceptions import DataLoadError

logger = logging.getLogger("lotto_prediction")


class LotteryService:
    """로또 당첨 정보 조회 서비스"""

    # 동행복권 API URL
    API_URL = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={draw_no}"

    @classmethod
    async def fetch_draw_result(cls, draw_no: int) -> Optional[Dict[str, Any]]:
        """지정된 회차의 로또 당첨 정보 조회"""
        try:
            url = cls.API_URL.format(draw_no=draw_no)
            logger.info(f"로또 {draw_no}회차 당첨 정보 조회 요청 중: {url}")

            # 브라우저처럼 보이는 User-Agent와 Referer 헤더 추가
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Referer": "https://www.dhlottery.co.kr/gameResult.do?method=byWin",
                "Accept": "application/json, text/plain, */*"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=30) as response:
                    if response.status != 200:
                        logger.error(f"로또 당첨 정보 조회 실패 (HTTP {response.status}): {await response.text()}")
                        return None

                    # 응답 본문 가져오기
                    content_type = response.headers.get('Content-Type', '')
                    text = await response.text()

                    # JSON 형식으로 파싱 시도
                    try:
                        # JSON 데이터로 파싱
                        data = json.loads(text)

                        # 응답 유효성 검증
                        if data.get("returnValue") != "success":
                            logger.warning(f"로또 당첨 정보 조회 결과 실패: {data}")
                            return None

                        logger.info(f"로또 {draw_no}회차 당첨 정보 조회 성공")
                        return data

                    except json.JSONDecodeError:
                        # HTML이나 다른 형식인 경우 수동으로 파싱 시도
                        logger.warning(f"JSON 파싱 실패, 응답 형식: {content_type}")

                        # 응답에 당첨번호 패턴이 있는지 확인
                        if "drwtNo1" in text and "bnusNo" in text:
                            logger.info("JSON 파싱 실패했지만 당첨번호 포함된 응답 발견, 수동 파싱 시도")
                            return cls._manual_parse_result(text, draw_no)

                        logger.error(f"로또 {draw_no}회차 당첨 정보 형식을 파싱할 수 없음")
                        return None

        except aiohttp.ClientError as e:
            logger.error(f"로또 당첨 정보 API 요청 중 네트워크 오류: {e}")
            return None
        except asyncio.TimeoutError:
            logger.error(f"로또 당첨 정보 API 요청 타임아웃")
            return None
        except Exception as e:
            logger.exception(f"로또 당첨 정보 조회 중 예상치 못한 오류: {e}")
            return None

    @classmethod
    def _manual_parse_result(cls, text: str, draw_no: int) -> Optional[Dict[str, Any]]:
        """HTML이나 다른 형식의 응답에서 당첨번호 수동 파싱"""
        try:
            # 정규 표현식으로 필요한 정보 추출
            import re

            # 회차 날짜
            date_match = re.search(r'"drwNoDate"\s*:\s*"([^"]+)"', text)

            # 당첨번호 6개
            no1 = re.search(r'"drwtNo1"\s*:\s*(\d+)', text)
            no2 = re.search(r'"drwtNo2"\s*:\s*(\d+)', text)
            no3 = re.search(r'"drwtNo3"\s*:\s*(\d+)', text)
            no4 = re.search(r'"drwtNo4"\s*:\s*(\d+)', text)
            no5 = re.search(r'"drwtNo5"\s*:\s*(\d+)', text)
            no6 = re.search(r'"drwtNo6"\s*:\s*(\d+)', text)

            # 보너스 번호
            bonus = re.search(r'"bnusNo"\s*:\s*(\d+)', text)

            # 필요한 정보가 모두 추출되었는지 확인
            if all([date_match, no1, no2, no3, no4, no5, no6, bonus]):
                # 추출된 정보로 딕셔너리 구성
                result = {
                    "returnValue": "success",
                    "drwNoDate": date_match.group(1),
                    "drwtNo1": int(no1.group(1)),
                    "drwtNo2": int(no2.group(1)),
                    "drwtNo3": int(no3.group(1)),
                    "drwtNo4": int(no4.group(1)),
                    "drwtNo5": int(no5.group(1)),
                    "drwtNo6": int(no6.group(1)),
                    "bnusNo": int(bonus.group(1)),
                    "drwNo": draw_no
                }

                logger.info(f"로또 {draw_no}회차 당첨 정보 수동 파싱 성공")
                return result
            else:
                logger.error(f"로또 {draw_no}회차 당첨 정보 수동 파싱 실패: 필요한 정보를 찾을 수 없음")
                return None

        except Exception as e:
            logger.exception(f"로또 당첨 정보 수동 파싱 중 오류: {e}")
            return None

    # 대체 방법 (직접 웹페이지에서 파싱 방식)
    @classmethod
    async def fetch_draw_result_alternative(cls, draw_no: int) -> Optional[Dict[str, Any]]:
        """동행복권 웹페이지에서 당첨 정보를 직접 파싱하는 대체 방법"""
        try:
            # 당첨번호 페이지 URL
            url = f"https://www.dhlottery.co.kr/gameResult.do?method=byWin&drwNo={draw_no}"

            # 브라우저처럼 보이는 User-Agent 헤더 추가
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=30) as response:
                    if response.status != 200:
                        logger.error(f"로또 당첨 정보 페이지 조회 실패 (HTTP {response.status})")
                        return None

                    # HTML 파싱을 위한 추가 라이브러리가 필요할 수 있음
                    # requirements.txt에 beautifulsoup4 추가 필요
                    try:
                        from bs4 import BeautifulSoup

                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')

                        # 당첨번호가 있는 요소 찾기 (실제 웹페이지 구조에 따라 수정 필요)
                        date_element = soup.select_one('.win_result .desc')
                        numbers_element = soup.select('.win_result .num.win')
                        bonus_element = soup.select_one('.win_result .num.bonus')

                        if date_element and numbers_element and len(numbers_element) >= 6 and bonus_element:
                            # 날짜 추출
                            date_text = date_element.get_text().strip()
                            date_match = re.search(r'(\d{4}년\s+\d{1,2}월\s+\d{1,2}일)', date_text)
                            draw_date = date_match.group(1) if date_match else ''

                            # 당첨번호 추출
                            numbers = [int(num.get_text().strip()) for num in numbers_element[:6]]
                            bonus_number = int(bonus_element.get_text().strip())

                            # 결과 구성
                            result = {
                                "returnValue": "success",
                                "drwNoDate": draw_date,
                                "drwtNo1": numbers[0],
                                "drwtNo2": numbers[1],
                                "drwtNo3": numbers[2],
                                "drwtNo4": numbers[3],
                                "drwtNo5": numbers[4],
                                "drwtNo6": numbers[5],
                                "bnusNo": bonus_number,
                                "drwNo": draw_no
                            }

                            logger.info(f"로또 {draw_no}회차 당첨 정보 웹페이지 파싱 성공")
                            return result
                        else:
                            logger.error(f"로또 {draw_no}회차 당첨 정보 웹페이지 파싱 실패: 요소를 찾을 수 없음")
                            return None

                    except ImportError:
                        logger.error("BeautifulSoup 라이브러리가 설치되지 않았습니다. pip install beautifulsoup4를 실행하세요.")
                        return None
                    except Exception as e:
                        logger.exception(f"웹페이지 파싱 중 오류: {e}")
                        return None

        except Exception as e:
            logger.exception(f"대체 방법을 통한 로또 당첨 정보 조회 중 오류: {e}")
            return None

    @classmethod
    async def save_draw_result(cls, draw_no: int) -> bool:
        """지정된 회차의 로또 당첨 정보 조회 후 슬랙 알림 및 데이터베이스 저장"""
        try:
            # 1. 로또 당첨 정보 조회 (기본 API 방식)
            data = await cls.fetch_draw_result(draw_no)

            # 기본 API 방식이 실패하면 대체 방법 시도
            if not data:
                logger.warning(f"로또 {draw_no}회차 기본 API 조회 실패, 대체 방법 시도 중...")
                data = await cls.fetch_draw_result_alternative(draw_no)

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

            # 4. 슬랙으로 당첨 결과 알림 (예측 비교 포함)
            try:
                from services.slack_service import SlackNotifier
                slack_notifier = SlackNotifier()

                await slack_notifier.send_lottery_result_notification(
                    draw_no=draw_no,
                    numbers=sorted_numbers,
                    bonus_no=bonus_no,
                    draw_date=draw_date,
                    prediction_comparisons=prediction_comparisons
                )

                logger.info(f"로또 {draw_no}회차 당첨 결과 슬랙 알림 전송 완료")
            except Exception as e:
                logger.warning(f"로또 {draw_no}회차 당첨 결과 슬랙 알림 전송 실패: {e}")
                # 슬랙 알림 실패해도 DB 저장은 계속 진행

            # 5. 이미 존재하는지 확인
            from database.repositories.lotto_repository import AsyncLottoRepository
            exists = await AsyncLottoRepository.check_draw_exists(draw_no)

            if exists:
                logger.info(f"로또 {draw_no}회차 당첨 정보가 이미 데이터베이스에 존재합니다")
                return True

            # 6. 데이터베이스에 저장 (1~6 번호만)
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

            # recommand 테이블에서 next_no가 현재 회차인 예측 결과 조회
            predictions = await AsyncLottoRepository.get_recommendations_for_draw(draw_no)

            if not predictions:
                logger.warning(f"로또 {draw_no}회차에 대한 예측 결과가 없습니다")
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

            return comparison_results

        except Exception as e:
            logger.exception(f"예측 결과 비교 중 오류: {e}")
            return []
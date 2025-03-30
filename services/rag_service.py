# services/rag_service.py
import asyncio
import json
import logging
from typing import List, Dict, Any, Tuple

import aiohttp
from anthropic import AsyncAnthropic
from anthropic.types import MessageParam

from config.settings import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    ANTHROPIC_MAX_TOKENS,
    ANTHROPIC_TEMPERATURE,
    ANTHROPIC_FALLBACK_STRATEGY
)
from utils.exceptions import ConfigurationError

logger = logging.getLogger("lotto_prediction")


class RAGService:
    """Anthropic Claude RAG 서비스 (비동기 구현)"""

    def __init__(self):
        if not ANTHROPIC_API_KEY:
            logger.error("Anthropic API 키가 설정되지 않았습니다")
            raise ConfigurationError("ANTHROPIC_API_KEY is not set")

        self.client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        self.max_retries = 3
        self.retry_delay = 2

        # Claude 3.7 Sonnet 가격 설정 (2025년 3월 기준, 변경될 수 있음)
        self.price_per_1k_input_tokens = 0.01  # 입력 토큰 1000개당 $0.01
        self.price_per_1k_output_tokens = 0.03  # 출력 토큰 1000개당 $0.03

    async def generate_combinations(
            self,
            analysis_results: Dict[str, Any],
            num_combinations: int = 10
    ) -> Tuple[List[List[int]], Dict[str, Any]]:
        """분석 결과 기반으로 로또 번호 조합 생성 (비동기)"""
        # 사용량 통계 초기화
        usage_stats = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "api_calls": 0,
            "estimated_cost": 0.0,
        }

        retry_count = 0
        last_error = None

        while retry_count < self.max_retries:
            try:
                # 분석 결과 문자열로 변환
                analysis_json = json.dumps(analysis_results, indent=2)

                # 프롬프트 생성
                prompt = self._create_prompt(analysis_json, num_combinations)

                # Anthropic API 비동기 호출
                usage_stats["api_calls"] += 1
                response = await self.client.messages.create(
                    model=ANTHROPIC_MODEL,
                    max_tokens=ANTHROPIC_MAX_TOKENS,
                    temperature=ANTHROPIC_TEMPERATURE,
                    system="You are a lottery number prediction assistant that analyzes patterns and generates potential combinations.",
                    messages=[{"role": "user", "content": prompt}],
                    timeout=60  # 60초 타임아웃 설정
                )

                # 토큰 사용량 업데이트
                if hasattr(response, 'usage'):
                    usage_stats["prompt_tokens"] += response.usage.input_tokens
                    usage_stats["completion_tokens"] += response.usage.output_tokens
                    usage_stats["total_tokens"] = usage_stats["prompt_tokens"] + usage_stats["completion_tokens"]

                    # 비용 계산
                    input_cost = (usage_stats["prompt_tokens"] / 1000) * self.price_per_1k_input_tokens
                    output_cost = (usage_stats["completion_tokens"] / 1000) * self.price_per_1k_output_tokens
                    usage_stats["estimated_cost"] = input_cost + output_cost
                else:
                    # 토큰 정보가 없는 경우 추정 (약 4자당 1토큰)
                    prompt_tokens = len(prompt) // 4
                    completion_tokens = len(response.content[0].text) // 4
                    usage_stats["prompt_tokens"] += prompt_tokens
                    usage_stats["completion_tokens"] += completion_tokens
                    usage_stats["total_tokens"] = usage_stats["prompt_tokens"] + usage_stats["completion_tokens"]

                    # 추정 비용 계산
                    input_cost = (usage_stats["prompt_tokens"] / 1000) * self.price_per_1k_input_tokens
                    output_cost = (usage_stats["completion_tokens"] / 1000) * self.price_per_1k_output_tokens
                    usage_stats["estimated_cost"] = input_cost + output_cost

                # 응답에서 JSON 추출
                content = response.content[0].text
                combinations = await self._extract_json_combinations(content)

                # 생성된 조합 검증
                if not combinations:
                    logger.warning("Anthropic API가 유효한 조합을 생성하지 않음, 대체 전략 사용")
                    fallback_combinations, fallback_usage = await self._fallback_combination_generator(analysis_results,
                                                                                                       num_combinations)

                    # 대체 전략 사용량 통계 병합
                    for key in usage_stats:
                        if key in fallback_usage:
                            usage_stats[key] += fallback_usage[key]

                    return fallback_combinations, usage_stats

                if len(combinations) < num_combinations:
                    logger.warning(f"Anthropic API가 요청한 개수보다 적은 조합 생성: {len(combinations)}/{num_combinations}")
                    # 부족한 조합 추가 생성
                    additional_combinations, additional_usage = await self._fallback_combination_generator(
                        analysis_results,
                        num_combinations - len(combinations)
                    )

                    # 대체 전략 사용량 통계 병합
                    for key in usage_stats:
                        if key in additional_usage:
                            usage_stats[key] += additional_usage[key]

                    combinations.extend(additional_combinations)

                logger.info(
                    f"Anthropic API를 통해 {len(combinations)}개 조합 생성 완료, 총 토큰: {usage_stats['total_tokens']}, 예상 비용: ${usage_stats['estimated_cost']:.4f}")
                return combinations, usage_stats

            except asyncio.TimeoutError:
                retry_count += 1
                last_error = "API 호출 타임아웃"
                logger.warning(f"Anthropic API 호출 타임아웃 (시도 {retry_count}/{self.max_retries})")

                if retry_count < self.max_retries:
                    delay = self.retry_delay * (2 ** (retry_count - 1))
                    logger.info(f"{delay}초 후 재시도...")
                    await asyncio.sleep(delay)

            except Exception as e:
                retry_count += 1
                last_error = e
                logger.error(f"Anthropic API 호출 오류 (시도 {retry_count}/{self.max_retries}): {e}")

                if retry_count < self.max_retries:
                    delay = self.retry_delay * (2 ** (retry_count - 1))
                    logger.info(f"{delay}초 후 재시도...")
                    await asyncio.sleep(delay)

        # 최대 재시도 횟수 초과 - 대체 전략 사용
        logger.error(f"Anthropic API 호출 최대 재시도 횟수 초과: {last_error}")
        logger.info("대체 조합 생성 전략 사용 중...")

        return await self._fallback_combination_generator(analysis_results, num_combinations)

    async def _fallback_combination_generator(
            self,
            analysis_results: Dict[str, Any],
            num_combinations: int
    ) -> Tuple[List[List[int]], Dict[str, Any]]:
        """API 호출 실패 시 대체 조합 생성 전략"""
        # 대체 전략 사용량 통계
        fallback_usage = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "api_calls": 0,
            "estimated_cost": 0.0,
        }

        strategy = ANTHROPIC_FALLBACK_STRATEGY
        logger.info(f"대체 전략 '{strategy}' 사용")

        if strategy == "statistical":
            combinations = await self._statistical_combination_generator(analysis_results, num_combinations)
        elif strategy == "random":
            combinations = await self._random_combination_generator(num_combinations)
        else:
            logger.warning(f"알 수 없는 대체 전략 '{strategy}', 랜덤 전략 사용")
            combinations = await self._random_combination_generator(num_combinations)

        logger.info(f"대체 전략으로 {len(combinations)}개 조합 생성")
        return combinations, fallback_usage

    async def _statistical_combination_generator(
            self,
            analysis_results: Dict[str, Any],
            num_combinations: int
    ) -> List[List[int]]:
        """통계 기반 조합 생성 전략"""
        import random
        import numpy as np

        try:
            # 번호 빈도 분석 결과 사용
            number_frequency = analysis_results.get("number_frequency", {})
            continuity_dist = analysis_results.get("continuity_distribution", {})
            last_numbers = analysis_results.get("last_draw", {}).get("numbers", [])

            # 번호 빈도가 없으면 균등 분포 가정
            if not number_frequency:
                number_frequency = {i: 1 for i in range(1, 46)}

            # 번호별 가중치 계산
            weights = np.array([number_frequency.get(i, 0) for i in range(1, 46)])
            if weights.sum() == 0:
                weights = np.ones(45)
            weights = weights / weights.sum()

            # 연속성 분포가 없으면 균등 분포 가정
            if not continuity_dist:
                continuity_dist = {i: 1 / 7 for i in range(7)}

            # 각 조합별 중복 번호 수 결정
            combinations = []
            for _ in range(num_combinations):
                # 이전 회차와 중복될 번호 개수 선택
                common_count = random.choices(
                    list(continuity_dist.keys()),
                    weights=list(continuity_dist.values())
                )[0]

                # 중복 번호 선택
                common_numbers = []
                if common_count > 0 and last_numbers:
                    common_numbers = random.sample(last_numbers, min(common_count, len(last_numbers)))

                # 남은 번호 선택
                remaining_count = 6 - len(common_numbers)
                available_numbers = [i for i in range(1, 46) if i not in common_numbers]

                # 가중치 조정 (이미 선택된 번호 제외)
                adjusted_weights = [weights[i - 1] if i in available_numbers else 0 for i in range(1, 46)]
                adjusted_weights = np.array(adjusted_weights)
                if adjusted_weights.sum() > 0:
                    adjusted_weights = adjusted_weights / adjusted_weights.sum()

                # 남은 번호 선택
                remaining_numbers = np.random.choice(
                    range(1, 46),
                    size=remaining_count,
                    replace=False,
                    p=adjusted_weights
                ).tolist()

                # 모든 번호 조합
                combination = sorted(common_numbers + remaining_numbers)

                # 중복 조합 방지
                if combination not in combinations:
                    combinations.append(combination)

            logger.info(f"통계 기반 대체 전략으로 {len(combinations)}개 조합 생성")
            return combinations

        except Exception as e:
            logger.error(f"통계 기반 조합 생성 오류: {e}")
            # 오류 발생 시 랜덤 전략으로 대체
            return await self._random_combination_generator(num_combinations)

    async def _random_combination_generator(self, num_combinations: int) -> List[List[int]]:
        """완전 랜덤 조합 생성 전략"""
        import random

        combinations = []
        for _ in range(num_combinations):
            combination = sorted(random.sample(range(1, 46), 6))
            if combination not in combinations:
                combinations.append(combination)

        logger.info(f"랜덤 대체 전략으로 {len(combinations)}개 조합 생성")
        return combinations

    # 나머지 메서드는 그대로 유지...

    def _create_prompt(self, analysis_json: str, num_combinations: int) -> str:
        """RAG 프롬프트 생성"""
        return f"""
        다음은 로또 번호(1~45 사이 숫자 6개) 예측을 위한 역대 당첨 데이터 분석 결과입니다:

        {analysis_json}

        위 데이터를 기반으로, 다음 회차에 나올 것 같은 로또 번호 조합 {num_combinations}개를 생성해주세요.
        각 조합은 1~45 사이의 숫자 6개로 구성되어야 하며, 오름차순으로 정렬해주세요.
        이전에 나왔던 조합과 동일한 조합은 제외합니다.
        이전 회차 번호와의 연속성(중복되는 번호의 수)을 고려해주세요.

        특히 다음 사항을 고려해주세요:
        1. 번호 빈도 분석을 참고하여 자주 나오는 번호와 드물게 나오는 번호의 균형을 맞춰주세요.
        2. 홀수/짝수 분포를 고려해주세요.
        3. 번호 합계 범위를 고려해주세요.
        4. 이전 회차와의 연속성 분포를 반영해주세요.

        응답은 다음과 같은 JSON 형식으로 해주세요:
        [
            [n1, n2, n3, n4, n5, n6],
            [n1, n2, n3, n4, n5, n6],
            ...
        ]
        """

    async def _extract_json_combinations(self, content: str) -> List[List[int]]:
        """응답에서 JSON 조합 추출 (비동기)"""
        try:
            # JSON 부분 추출
            json_start = content.find('[')
            json_end = content.rfind(']') + 1

            if json_start != -1 and json_end != -1:
                json_str = content[json_start:json_end]
                combinations = json.loads(json_str)

                # 병렬로 유효성 검사 실행
                tasks = [self._validate_combination(combo) for combo in combinations]
                valid_combinations = await asyncio.gather(*tasks)

                # None 값 제거
                return [combo for combo in valid_combinations if combo is not None]
            else:
                # 대체 파싱 방법 사용
                return await self._fallback_extraction(content)

        except json.JSONDecodeError:
            logger.warning("JSON 파싱 실패, 대체 추출 방법 사용")
            return await self._fallback_extraction(content)

    async def _validate_combination(self, combo: List[int]) -> List[int] or None:
        """조합 유효성 검사 (비동기)"""
        if (isinstance(combo, list) and
                len(combo) == 6 and
                all(isinstance(n, int) and 1 <= n <= 45 for n in combo) and
                len(set(combo)) == 6):
            return sorted(combo)
        return None

    async def _fallback_extraction(self, text: str) -> List[List[int]]:
        """텍스트에서 번호 조합 추출 (JSON 파싱 실패 시) (비동기)"""
        combinations = []
        lines = text.split('\n')

        for line in lines:
            # 숫자 추출
            numbers = [int(n) for n in line.split() if n.isdigit() and 1 <= int(n) <= 45]
            if len(numbers) >= 6:
                # 6개씩 그룹화
                for i in range(0, len(numbers) - 5):
                    combo = sorted(numbers[i:i + 6])
                    if len(set(combo)) == 6:  # 중복 숫자 없는지 확인
                        combinations.append(combo)

        return combinations

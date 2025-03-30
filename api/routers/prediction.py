# api/routers/prediction.py - 오류 처리 개선
import asyncio
import logging
import traceback
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_async_data_service, get_async_prediction_service
from api.schemas.prediction import PredictionRequest, PredictionResponse, PredictionResult, PerformanceMetrics, \
    DrawResultResponse, DrawResultRequest
from database.connector import AsyncDatabaseConnector
from database.repositories.lotto_repository import AsyncLottoRepository
from services.analysis_service import AnalysisService
from services.data_service import AsyncDataService
from services.prediction_service import AsyncPredictionService
from utils.exceptions import (
    LottoPredictionError, DatabaseError, DataLoadError,
    AnalysisError, PredictionGenerationError, APIServiceError, ValidationError
)

router = APIRouter()
logger = logging.getLogger("lotto_prediction")


@router.post("/predict", response_model=PredictionResponse, status_code=status.HTTP_200_OK)
async def predict_lotto_numbers(
        request: PredictionRequest,
        data_service: AsyncDataService = Depends(get_async_data_service),
        prediction_service: AsyncPredictionService = Depends(get_async_prediction_service)
):
    """
    로또 번호 예측 통합 API - 데이터 수집, 분석, 예측, 결과 도출까지 한번에 처리 (비동기)

    사용자는 생성할 예측 개수만 지정하면 나머지는 시스템이 자동으로 처리합니다.
    항상 601회차부터 최신 회차까지의 데이터를 분석합니다.
    """
    # 시작 시간 기록
    start_time = time.time()
    logger.info(f"로또 예측 프로세스 시작 (요청 예측 개수: {request.count})")

    # 사용량 통계 초기화
    performance_metrics = {
        "elapsed_time": 0,
        "total_tokens": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "api_calls": 0,
        "estimated_cost": 0.0,
    }

    try:
        # 1. 역대 당첨 데이터 로드 (601회차부터 최신까지)
        logger.info("601회차부터 최신 회차까지 데이터 로드 중...")

        try:
            # 최신 회차 가져오기
            last_no = None
            last_draw_data = await AsyncLottoRepository.get_last_draw()
            if last_draw_data:
                last_no = last_draw_data["no"]
                logger.info(f"최신 회차 확인됨: {last_no}회")
        except DatabaseError as e:
            logger.error(f"최신 회차 조회 오류: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="데이터베이스 서비스를 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해주세요."
            )

        # 데이터 로드
        try:
            success = await data_service.load_historical_data(
                start_no=601,
                end_no=last_no
            )

            if not success:
                raise DataLoadError("역대 데이터 로드 실패")
        except DatabaseError as e:
            logger.error(f"데이터베이스 오류: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="데이터베이스 서비스를 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해주세요."
            )
        except DataLoadError as e:
            logger.error(f"데이터 로드 오류: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="역대 당첨 데이터를 로드하는데 실패했습니다."
            )

        last_draw = data_service.get_last_draw()
        if not last_draw:
            logger.error("최근 회차 데이터 찾기 실패")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="최근 회차 데이터를 찾을 수 없습니다"
            )

        logger.info(f"총 {len(data_service.get_all_draws())}개 회차 데이터 로드 완료")
        logger.info(f"최근 회차: {last_draw.draw_no}, 당첨번호: {last_draw.numbers}")

        # 2. 데이터 분석
        logger.info("당첨 데이터 분석 중...")
        try:
            analysis_service = AnalysisService(data_service.get_all_draws())
            analysis_results = analysis_service.get_comprehensive_analysis()

            if not analysis_results:
                raise AnalysisError("데이터 분석 결과가 비어있습니다")
        except AnalysisError as e:
            logger.error(f"데이터 분석 오류: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="데이터 분석에 실패했습니다"
            )

        logger.info("데이터 분석 완료")

        # 3. 다음 회차 번호 예측 (비동기)
        logger.info(f"{request.count}개 예측 조합 생성 중...")
        try:
            # 기존 코드에서 토큰 사용량 정보를 반환받지 못하는 경우 처리
            try:
                predictions, api_usage = await prediction_service.predict_next_draw(
                    num_predictions=request.count
                )

                # API 사용량 정보 업데이트
                if api_usage:
                    performance_metrics.update(api_usage)
            except ValueError:
                # 단일 값만 반환하는 경우 처리
                predictions = await prediction_service.predict_next_draw(
                    num_predictions=request.count
                )
                logger.warning("API 사용량 정보를 가져오지 못했습니다. 기본값 사용.")

            if not predictions:
                raise PredictionGenerationError("예측 결과가 비어있습니다")
        except APIServiceError as e:
            logger.error(f"AI 서비스 오류: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI 예측 서비스를 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해주세요."
            )
        except PredictionGenerationError as e:
            logger.error(f"예측 생성 오류: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="예측 생성에 실패했습니다"
            )

        logger.info(f"{len(predictions)}개 예측 조합 생성 완료")

        # 4. 결과 준비
        prediction_results = [
            PredictionResult(
                combination=pred.combination,
                score=pred.score,
                common_with_last=pred.common_with_last
            )
            for pred in predictions
        ]

        # 화면에 예측 번호 출력 (저장 전)
        logger.info("생성된 예측 번호 조합:")
        for i, pred in enumerate(predictions, 1):
            sorted_numbers = sorted(pred.combination)
            numbers_str = ", ".join(str(n) for n in sorted_numbers)
            logger.info(f"조합 {i}: [{numbers_str}] (점수: {pred.score:.4f}, 이전 회차와 공통 번호: {pred.common_with_last}개)")

        # 5. 분석 결과 요약 준비
        analysis_summary = {
            "hot_numbers": analysis_results.get("hot_numbers", [])[:5],
            "cold_numbers": analysis_results.get("cold_numbers", [])[:5],
            "avg_continuity": sum(
                k * v for k, v in analysis_results.get("continuity_distribution", {}).items()
            ) / analysis_results.get("total_draws", 1),
            "parity_distribution": analysis_results.get("parity_distribution", {}),
            "sum_distribution": analysis_results.get("sum_distribution", {}),
            "data_range": {
                "start_draw": 601,
                "end_draw": last_draw.draw_no,
                "total_draws": len(data_service.get_all_draws())
            }
        }

        # 6. 결과 저장 (비동기)
        next_draw_no = last_draw.draw_no + 1

        try:
            success_count = 0
            for pred in predictions:
                # recommand 테이블에 저장 (next_no 추가)
                success = await AsyncLottoRepository.save_recommendation(
                    numbers=pred.combination,
                    next_no=next_draw_no
                )
                if success:
                    success_count += 1

            logger.info(f"예측 결과 {success_count}/{len(predictions)}개 저장 완료 (예측 회차: {next_draw_no})")

            if success_count < len(predictions):
                logger.warning(f"{len(predictions) - success_count}개 예측 저장 실패")

        except Exception as e:
            logger.warning(f"예측 결과 저장 중 오류 발생: {str(e)}")
            # 저장 실패는 API 응답에 영향을 주지 않음

        # 7. 종료 시간 기록 및 소요 시간 계산
        end_time = time.time()
        elapsed_time = end_time - start_time
        performance_metrics["elapsed_time"] = elapsed_time

        logger.info(
            f"예측 완료: 소요 시간 {elapsed_time:.2f}초, 토큰 사용량: {performance_metrics['total_tokens']}, 예상 비용: ${performance_metrics['estimated_cost']:.4f}")

        # 8. 응답 생성
        response = PredictionResponse(
            predictions=prediction_results,
            last_draw={
                "draw_no": last_draw.draw_no,
                "numbers": last_draw.numbers,
                "draw_date": last_draw.draw_date.isoformat()
            },
            next_draw_no=next_draw_no,
            analysis_summary=analysis_summary,
            performance_metrics=PerformanceMetrics(**performance_metrics)  # 성능 지표 추가
        )

        logger.info("로또 예측 프로세스 완료")
        return response

    except HTTPException:
        # 이미 처리된 HTTP 예외는 그대로 전달
        raise

    except LottoPredictionError as e:
        # 시스템 정의 예외를 HTTP 예외로 변환
        logger.error(f"예측 시스템 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

    except asyncio.TimeoutError:
        # 비동기 작업 타임아웃
        logger.error("작업 타임아웃")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="요청 처리 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."
        )

    except Exception as e:
        # 예상치 못한 오류
        logger.exception(f"예상치 못한 오류 발생: {str(e)}")
        logger.error(f"스택 트레이스: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="내부 서버 오류가 발생했습니다. 관리자에게 문의하세요."
        )


@router.post("/results", response_model=DrawResultResponse, status_code=status.HTTP_201_CREATED)
async def save_draw_result(request: DrawResultRequest):
    """
    로또 당첨 결과 저장 API

    새로운 회차의 당첨 번호를 result 테이블에 저장합니다.
    이미 존재하는 회차 번호는 저장되지 않습니다.
    """
    logger.info(f"당첨 결과 저장 요청 (회차: {request.draw_no})")

    try:
        # 번호 유효성 검증 (Pydantic 모델에서 이미 수행)
        sorted_numbers = sorted(request.numbers)

        # 당첨 결과 저장
        success = await AsyncLottoRepository.save_draw_result(
            draw_no=request.draw_no,
            numbers=sorted_numbers
        )

        if success:
            response = DrawResultResponse(
                success=True,
                draw_no=request.draw_no,
                numbers=sorted_numbers,
                message="당첨 결과가 성공적으로 저장되었습니다."
            )
            logger.info(f"당첨 결과 저장 성공 (회차: {request.draw_no})")
            return response
        else:
            # 이미 존재하는 회차 등의 이유로 저장 실패
            response = DrawResultResponse(
                success=False,
                draw_no=request.draw_no,
                numbers=sorted_numbers,
                message="당첨 결과 저장에 실패했습니다. 이미 존재하는 회차일 수 있습니다."
            )
            logger.warning(f"당첨 결과 저장 실패 (회차: {request.draw_no})")
            return response

    except DatabaseError as e:
        logger.error(f"데이터베이스 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="데이터베이스 서비스를 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해주세요."
        )
    except ValidationError as e:
        logger.error(f"유효성 검증 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"당첨 결과 저장 중 예상치 못한 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="내부 서버 오류가 발생했습니다. 관리자에게 문의하세요."
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """API 헬스 체크 엔드포인트"""
    try:
        # 데이터베이스 연결 확인
        await AsyncDatabaseConnector.get_pool()

        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"헬스 체크 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="시스템이 현재 이용 불가능합니다"
        )
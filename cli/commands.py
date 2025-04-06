# cli/commands.py
import argparse
import logging
import json
import os
from datetime import datetime
from config.logging_config import setup_logging
from services.data_service import DataService
from services.prediction_service import PredictionService
from evaluation.cross_validator import CrossValidator
from utils.formatters import ResultFormatter

logger = logging.getLogger("lotto_prediction")


class CLI:
    """로또 예측 시스템 CLI"""

    def __init__(self):
        self.data_service = DataService()
        self.parser = self._create_parser()

    def _create_parser(self):
        """명령줄 파서 생성"""
        parser = argparse.ArgumentParser(
            description="로또 번호 예측 시스템"
        )

        subparsers = parser.add_subparsers(dest="command", help="명령")

        # 데이터 로드 명령
        load_parser = subparsers.add_parser("load", help="로또 당첨 데이터 로드")
        load_parser.add_argument(
            "--start", type=int, default=601,
            help="시작 회차 (기본값: 601)"
        )
        load_parser.add_argument(
            "--end", type=int, default=1166,
            help="종료 회차 (기본값: 1166)"
        )

        # 예측 명령
        predict_parser = subparsers.add_parser("predict", help="다음 회차 번호 예측")
        predict_parser.add_argument(
            "--count", type=int, default=5,
            help="예측 조합 개수 (기본값: 5)"
        )
        predict_parser.add_argument(
            "--output", choices=["text", "json"], default="text",
            help="출력 형식 (기본값: text)"
        )
        predict_parser.add_argument(
            "--save", action="store_true",
            help="결과를 파일로 저장"
        )

        # 교차 검증 명령
        validate_parser = subparsers.add_parser("validate", help="예측 교차 검증")
        validate_parser.add_argument(
            "--draws", type=int, default=10,
            help="검증할 회차 수 (기본값: 10)"
        )
        validate_parser.add_argument(
            "--output", choices=["text", "json"], default="json",
            help="출력 형식 (기본값: json)"
        )
        validate_parser.add_argument(
            "--save", action="store_true",
            help="결과를 파일로 저장"
        )

        return parser

    def run(self):
        """CLI 실행"""
        args = self.parser.parse_args()

        if not args.command:
            self.parser.print_help()
            return

        if args.command == "load":
            self._handle_load(args)
        elif args.command == "predict":
            self._handle_predict(args)
        elif args.command == "validate":
            self._handle_validate(args)

    def _handle_load(self, args):
        """데이터 로드 명령 처리"""
        logger.info(f"로또 당첨 데이터 로드 중 (범위: {args.start}-{args.end})")

        success = self.data_service.load_historical_data(
            start_no=args.start,
            end_no=args.end
        )

        if success:
            draws = self.data_service.get_all_draws()
            print(f"데이터 로드 성공: {len(draws)}개 회차")

            if draws:
                last_draw = self.data_service.get_last_draw()
                print(f"최근 회차: {ResultFormatter.format_draw_to_text(last_draw)}")
        else:
            print("데이터 로드 실패")

    def _handle_predict(self, args):
        """예측 명령 처리"""
        logger.info(f"다음 회차 번호 예측 중 (생성 개수: {args.count})")

        # 데이터 로드 확인
        if not self.data_service.get_all_draws():
            print("데이터를 먼저 로드해야 합니다. 'load' 명령을 실행하세요.")
            return

        # 예측 서비스 초기화 및 실행
        prediction_service = PredictionService(self.data_service)
        predictions = prediction_service.predict_next_draw(
            num_predictions=args.count
        )

        if not predictions:
            print("예측 생성에 실패했습니다.")
            return

        # 결과 출력
        if args.output == "text":
            result = ResultFormatter.format_predictions_to_text(predictions)
        else:
            result = ResultFormatter.format_predictions_to_json(predictions)

        print(result)

        # 결과 저장
        if args.save:
            last_draw = self.data_service.get_last_draw()
            next_draw_no = last_draw.draw_no + 1 if last_draw else "unknown"

            filename = f"predictions_{next_draw_no}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if args.output == "json":
                filename += ".json"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(result)
            else:
                filename += ".txt"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(result)

            print(f"예측 결과가 저장되었습니다: {filename}")

    def _handle_validate(self, args):
        """교차 검증 명령 처리"""
        logger.info(f"교차 검증 실행 중 (회차 수: {args.draws})")

        # 데이터 로드 확인
        if not self.data_service.get_all_draws():
            print("데이터를 먼저 로드해야 합니다. 'load' 명령을 실행하세요.")
            return

        # 검증기 초기화 및 실행
        validator = CrossValidator(self.data_service)
        results = validator.validate(test_draws=args.draws)

        if "error" in results:
            print(f"검증 오류: {results['error']}")
            return

        # 결과 출력
        if args.output == "text":
            overall = results["overall"]
            print(f"교차 검증 결과 (검증 회차: {overall['draws_evaluated']}개):")
            print(f"최대 일치율 평균: {overall['avg_max_match_rate']:.4f}")
            print(f"평균 일치율: {overall['avg_avg_match_rate']:.4f}")

            print("\n상세 결과:")
            for result in results["detail"]:
                print(f"회차 {result['draw_no']}:")
                print(f"  실제 번호: {', '.join(map(str, result['actual_numbers']))}")
                print(f"  최대 일치 개수: {result['max_matches']}개")
                print(f"  최대 일치율: {result['max_match_rate']:.4f}")
                print(f"  평균 일치율: {result['avg_match_rate']:.4f}")
        else:
            result_json = json.dumps(results, indent=2)
            print(result_json)

        # 결과 저장
        if args.save:
            filename = f"validation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if args.output == "json":
                filename += ".json"
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2)
            else:
                filename += ".txt"
                with open(filename, "w", encoding="utf-8") as f:
                    overall = results["overall"]
                    f.write(f"교차 검증 결과 (검증 회차: {overall['draws_evaluated']}개):\n")
                    f.write(f"최대 일치율 평균: {overall['avg_max_match_rate']:.4f}\n")
                    f.write(f"평균 일치율: {overall['avg_avg_match_rate']:.4f}\n\n")

                    f.write("상세 결과:\n")
                    for result in results["detail"]:
                        f.write(f"회차 {result['draw_no']}:\n")
                        f.write(f"  실제 번호: {', '.join(map(str, result['actual_numbers']))}\n")
                        f.write(f"  최대 일치 개수: {result['max_matches']}개\n")
                        f.write(f"  최대 일치율: {result['max_match_rate']:.4f}\n")
                        f.write(f"  평균 일치율: {result['avg_match_rate']:.4f}\n\n")

            print(f"검증 결과가 저장되었습니다: {filename}")
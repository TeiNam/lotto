# services/dhlottery_client.py
"""동행복권 비공식 클라이언트 (로그인 / 예치금 조회 / 로또645 구매)

roeniss/dhlottery-api(dhapi)의 엔드포인트를 기반으로, 이 프로젝트에 필요한
세 가지 동작만 구현한다: 로그인, 예치금 잔액 조회, 로또645 구매.

주의:
- 동기 requests.Session 기반이다. 비동기 컨텍스트에서는 asyncio.to_thread로 호출할 것.
- 로그인 시 ID/PW는 동행복권이 내려준 RSA 공개키로 암호화해 전송한다.
  (pycryptodome 대신 이미 설치된 cryptography로 PKCS1v15 암호화 처리)
"""
import json
import logging
import datetime
from typing import List, Dict, Optional

import pytz
import requests
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from cryptography.hazmat.primitives.asymmetric import padding

from utils.exceptions import DhLotteryError

logger = logging.getLogger("lotto_prediction")

_KST = pytz.timezone("Asia/Seoul")
_FIRST_ROUND_DATE = datetime.date(2002, 12, 7)  # 로또645 1회차 추첨일(토)


class DhLotteryClient:
    _base_url = "https://www.dhlottery.co.kr"
    _login_page = "/login"
    _rsa_key_url = "/login/selectRsaModulus.do"
    _login_url = "/login/securityLoginCheck.do"
    _game645_page = "https://ol.dhlottery.co.kr/olotto/game/game645.do"
    _ready_socket = "https://ol.dhlottery.co.kr/olotto/game/egovUserReadySocket.json"
    _buy_url = "https://ol.dhlottery.co.kr/olotto/game/execBuy.do"
    _balance_url = "https://www.dhlottery.co.kr/mypage/selectUserMndp.do"

    def __init__(self, user_id: str, user_pw: str):
        self._user_id = user_id
        self._user_pw = user_pw
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        })
        self._logged_in = False

    # --- 로그인 ---

    def _rsa_encrypt(self, plain_text: str, modulus_hex: str, exponent_hex: str) -> str:
        n = int(modulus_hex, 16)
        e = int(exponent_hex, 16)
        public_key = RSAPublicNumbers(e, n).public_key()
        encrypted = public_key.encrypt(plain_text.encode("utf-8"), padding.PKCS1v15())
        return encrypted.hex()

    def login(self) -> None:
        """동행복권 로그인 및 구매 도메인 세션(JSESSIONID) 확립"""
        try:
            resp = self._session.get(f"{self._base_url}/", timeout=10)
            if "index_check.html" in resp.url:
                raise DhLotteryError("동행복권 사이트가 현재 시스템 점검중입니다.")

            self._session.get(f"{self._base_url}{self._login_page}", timeout=10)

            # RSA 공개키 요청
            rsa_headers = {
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{self._base_url}{self._login_page}",
            }
            resp = self._session.get(
                f"{self._base_url}{self._rsa_key_url}", headers=rsa_headers, timeout=10
            )
            rsa_data = resp.json()
            if "data" not in rsa_data:
                raise DhLotteryError("RSA 공개키를 가져올 수 없습니다.")

            modulus = rsa_data["data"]["rsaModulus"]
            exponent = rsa_data["data"]["publicExponent"]

            login_headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": self._base_url,
                "Referer": f"{self._base_url}{self._login_page}",
            }
            login_data = {
                "userId": self._rsa_encrypt(self._user_id, modulus, exponent),
                "userPswdEncn": self._rsa_encrypt(self._user_pw, modulus, exponent),
                "inpUserId": self._user_id,
            }
            resp = self._session.post(
                f"{self._base_url}{self._login_url}",
                headers=login_headers, data=login_data, timeout=10, allow_redirects=True,
            )

            if resp.status_code != 200 or "loginSuccess" not in resp.url:
                raise DhLotteryError("로그인 실패: 아이디 또는 비밀번호를 확인해주세요.")

            # 구매 도메인(ol.dhlottery.co.kr) 세션 확립
            self._session.get(f"{self._base_url}/main", timeout=10)
            self._session.get(self._game645_page, timeout=10, allow_redirects=True)

            if not any(c.name == "JSESSIONID" for c in self._session.cookies):
                logger.warning("JSESSIONID를 획득하지 못했습니다 (구매가 실패할 수 있음)")

            self._logged_in = True
            logger.info("동행복권 로그인 성공")
        except DhLotteryError:
            raise
        except Exception as e:
            raise DhLotteryError(f"로그인 중 오류: {e}", original_error=e)

    def _ensure_login(self):
        if not self._logged_in:
            self.login()

    # --- 예치금 조회 ---

    def get_balance(self) -> Dict[str, int]:
        """예치금 현황 조회. 구매가능금액 등 금액 정보를 dict로 반환"""
        self._ensure_login()
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.dhlottery.co.kr/mypage/home",
        }
        try:
            resp = self._session.get(self._balance_url, headers=headers, timeout=10)
            if resp.status_code != 200 or "json" not in resp.headers.get("Content-Type", "").lower():
                raise DhLotteryError("예치금 API 응답 오류 (세션 만료 가능)")

            mndp = resp.json().get("data", {}).get("userMndp", {})

            def g(key):
                return mndp.get(key, 0) or 0

            총예치금 = (
                (g("pntDpstAmt") - g("pntTkmnyAmt"))
                + (g("ncsblDpstAmt") - g("ncsblTkmnyAmt"))
                + (g("csblDpstAmt") - g("csblTkmnyAmt"))
            )
            구매가능금액 = g("crntEntrsAmt")
            return {
                "total": 총예치금,
                "purchasable": 구매가능금액,
                "reserved": g("rsvtOrdrAmt"),
                "withdrawing": g("dawAplyAmt"),
            }
        except DhLotteryError:
            raise
        except Exception as e:
            raise DhLotteryError(f"예치금 조회 중 오류: {e}", original_error=e)

    # --- 구매 ---

    def _get_round(self) -> int:
        """현재 판매 중인 회차 계산 (이번 주 토요일 기준 경과 주차)"""
        today = datetime.datetime.now(_KST).date()
        days_until_sat = (5 - today.weekday()) % 7
        this_saturday = today + datetime.timedelta(days=days_until_sat)
        return 1 + (this_saturday - _FIRST_ROUND_DATE).days // 7

    def _calculate_draw_dates(self):
        today = datetime.datetime.now(_KST).date()
        days_until_sat = (5 - today.weekday()) % 7
        draw_date = today + datetime.timedelta(days=days_until_sat)
        pay_limit_date = draw_date + datetime.timedelta(days=365)
        return draw_date, pay_limit_date

    def _build_param(self, tickets: List[Dict]) -> str:
        """구매 param JSON 생성

        tickets: [{"mode": "auto"|"manual"|"semiauto", "numbers": [..]}]
        genType: 0=자동, 1=수동, 2=반자동
        """
        mode_to_gentype = {"auto": "0", "manual": "1", "semiauto": "2"}
        params = []
        for i, t in enumerate(tickets):
            mode = t.get("mode", "auto")
            gen_type = mode_to_gentype.get(mode)
            if gen_type is None:
                raise DhLotteryError(f"올바르지 않은 구매 모드: {mode}")
            numbers = t.get("numbers") or []
            arr = None if mode == "auto" else ",".join(str(n) for n in sorted(numbers))
            params.append({
                "genType": gen_type,
                "arrGameChoiceNum": arr,
                "alpabet": "ABCDE"[i],  # 동행복권 API 철자 그대로
            })
        return json.dumps(params)

    def buy_lotto645(self, tickets: List[Dict]) -> List[Dict]:
        """로또645 구매 (최대 5장)

        Returns: 구매된 슬롯 정보 리스트 [{"mode","slot","numbers"}]
        """
        self._ensure_login()
        if not tickets or len(tickets) > 5:
            raise DhLotteryError("구매 매수는 1~5장이어야 합니다.")
        try:
            res = self._session.post(self._ready_socket, timeout=5)
            direct = json.loads(res.text)["ready_ip"]

            draw_date, pay_limit_date = self._calculate_draw_dates()
            data = {
                "round": str(self._get_round()),
                "direct": direct,
                "nBuyAmount": str(1000 * len(tickets)),
                "param": self._build_param(tickets),
                "ROUND_DRAW_DATE": draw_date.strftime("%Y/%m/%d"),
                "WAMT_PAY_TLMT_END_DT": pay_limit_date.strftime("%Y/%m/%d"),
                "gameCnt": len(tickets),
                "saleMdaDcd": "10",
            }
            buy_headers = {"Referer": self._game645_page, "Origin": "https://ol.dhlottery.co.kr"}
            resp = self._session.post(self._buy_url, headers=buy_headers, data=data, timeout=10)
            response = json.loads(resp.text)

            if response.get("result", {}).get("resultCode") != "100":
                msg = response.get("result", {}).get("resultMsg", "알 수 없는 오류")
                raise DhLotteryError(f"구매 실패: {msg}")

            return self._format_lotto_numbers(response["result"]["arrGameChoiceNum"])
        except DhLotteryError:
            raise
        except Exception as e:
            raise DhLotteryError(f"구매 중 오류: {e}", original_error=e)

    @staticmethod
    def _format_lotto_numbers(lines: list) -> List[Dict]:
        """예: ["A|01|02|04|27|39|443"] -> [{"mode":"자동","slot":"A","numbers":[..]}]"""
        mode_dict = {"1": "수동", "2": "반자동", "3": "자동"}
        slots = []
        for line in lines:
            slots.append({
                "mode": mode_dict.get(line[-1], "?"),
                "slot": line[0],
                "numbers": line[2:-1].split("|"),
            })
        return slots

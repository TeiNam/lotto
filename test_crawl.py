#!/usr/bin/env python
"""동행복권 당첨번호 크롤링 테스트"""
import requests
from bs4 import BeautifulSoup
import re
from datetime import date, timedelta

def get_current_round():
    """현재 회차 계산"""
    first_round_date = date(2002, 12, 7)
    today = date.today()
    # 이번 주 토요일 계산
    days_until_saturday = (5 - today.weekday()) % 7
    this_saturday = today + timedelta(days=days_until_saturday)
    days_diff = (this_saturday - first_round_date).days
    return 1 + (days_diff // 7)

def get_lotto_result(round_no):
    """특정 회차의 당첨번호 크롤링"""
    url = f"https://www.dhlottery.co.kr/gameResult.do?method=byWin&drwNo={round_no}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = requests.get(url, headers=headers, timeout=10)
    response.encoding = 'utf-8'
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 방법 1: span.ball_645 찾기
    balls = soup.select('span.ball_645')
    if balls and len(balls) >= 7:
        numbers = [int(ball.text.strip()) for ball in balls[:6]]
        bonus = int(balls[6].text.strip())
        return {'numbers': numbers, 'bonus': bonus, 'method': 'ball_645'}
    
    # 방법 2: div.num 찾기
    num_divs = soup.select('div.num')
    if num_divs and len(num_divs) >= 7:
        numbers = []
        for div in num_divs[:6]:
            text = div.text.strip()
            if text.isdigit():
                numbers.append(int(text))
        if len(numbers) == 6 and num_divs[6].text.strip().isdigit():
            bonus = int(num_divs[6].text.strip())
            return {'numbers': numbers, 'bonus': bonus, 'method': 'div.num'}
    
    # 방법 3: 정규표현식으로 JavaScript 변수에서 추출
    script_pattern = r'drwtNo(\d)\s*=\s*(\d+)'
    matches = re.findall(script_pattern, response.text)
    if len(matches) >= 6:
        numbers = [int(m[1]) for m in matches[:6]]
        
        bonus_pattern = r'bnusNo\s*=\s*(\d+)'
        bonus_match = re.search(bonus_pattern, response.text)
        if bonus_match:
            bonus = int(bonus_match.group(1))
            return {'numbers': numbers, 'bonus': bonus, 'method': 'regex'}
    
    # 방법 4: p.num 찾기
    num_p = soup.select('p.num')
    if num_p:
        all_nums = []
        for p in num_p:
            spans = p.select('span')
            for span in spans:
                text = span.text.strip()
                if text.isdigit():
                    all_nums.append(int(text))
        
        if len(all_nums) >= 7:
            return {'numbers': all_nums[:6], 'bonus': all_nums[6], 'method': 'p.num'}
    
    return None

if __name__ == '__main__':
    print(f"현재 회차: {get_current_round()}")
    print()
    
    # 1205회차 테스트
    print("1205회차 테스트:")
    result = get_lotto_result(1205)
    if result:
        print(f"✅ 크롤링 성공 (방법: {result['method']})")
        print(f"당첨번호: {result['numbers']}")
        print(f"보너스: {result['bonus']}")
    else:
        print("❌ 크롤링 실패")
        
    # 1204회차도 테스트 (DB에 있는 회차)
    print("\n1204회차 테스트:")
    result = get_lotto_result(1204)
    if result:
        print(f"✅ 크롤링 성공 (방법: {result['method']})")
        print(f"당첨번호: {result['numbers']}")
        print(f"보너스: {result['bonus']}")

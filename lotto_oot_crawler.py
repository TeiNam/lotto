#!/usr/bin/env python
"""lotto.oot.kr 사이트에서 당첨번호 크롤링"""
import requests
from bs4 import BeautifulSoup
import re

def get_lotto_from_oot(round_no):
    """lotto.oot.kr에서 특정 회차 당첨번호 가져오기"""
    url = f'https://lotto.oot.kr/?round={round_no}'
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 메타 태그에서 정보 추출
        meta_desc = soup.find('meta', {'name': 'description'})
        if not meta_desc:
            return None
        
        content = meta_desc.get('content', '')
        
        # 정규표현식으로 당첨번호 추출
        # 예: "당첨번호 로또번호 1,4,16,23,31,41 + 보너스 번호 2"
        number_pattern = r'당첨번호 로또번호 ([\d,]+)\s*\+\s*보너스 번호 (\d+)'
        match = re.search(number_pattern, content)
        
        if match:
            numbers_str = match.group(1)
            bonus_str = match.group(2)
            
            numbers = [int(n.strip()) for n in numbers_str.split(',')]
            bonus = int(bonus_str)
            
            # 추첨일 추출
            date_pattern = r'당첨결과 \(([^)]+)\)'
            date_match = re.search(date_pattern, content)
            draw_date = date_match.group(1) if date_match else ''
            
            return {
                'round': round_no,
                'date': draw_date,
                'numbers': numbers,
                'bonus': bonus
            }
        
        return None
        
    except Exception as e:
        print(f'오류 발생: {e}')
        return None

if __name__ == '__main__':
    # 1205회차 테스트
    print('1205회차 테스트:')
    result = get_lotto_from_oot(1205)
    if result:
        print(f"✅ 크롤링 성공!")
        print(f"회차: {result['round']}회")
        print(f"추첨일: {result['date']}")
        print(f"당첨번호: {result['numbers']}")
        print(f"보너스: {result['bonus']}")
    else:
        print('❌ 크롤링 실패')
    
    # 1204회차도 테스트
    print('\n1204회차 테스트:')
    result = get_lotto_from_oot(1204)
    if result:
        print(f"✅ 크롤링 성공!")
        print(f"회차: {result['round']}회")
        print(f"추첨일: {result['date']}")
        print(f"당첨번호: {result['numbers']}")
        print(f"보너스: {result['bonus']}")
    else:
        print('❌ 크롤링 실패')

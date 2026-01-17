#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
from collections import defaultdict

def get_lotto_info():
    """동행복권 사이트에서 최신 회차 데이터 가지고 오기"""
    site_url = 'https://www.dhlottery.co.kr/common.do?method=main&mainMode=default'
    ret_json = defaultdict(int)
    
    try:
        info_data = requests.get(site_url)
        print(f"Status Code: {info_data.status_code}")
        
        if info_data.status_code != 200:
            return False, {}
        
        bs = BeautifulSoup(info_data.text, 'html.parser')
        content_data = bs.find('div', {'class': 'content'})
        
        if not content_data:
            print("content div를 찾을 수 없습니다")
            return False, {}
        
        # 각 요소 찾기
        round_elem = content_data.find('strong', {'id': 'lottoDrwNo'})
        date_elem = content_data.find('span', {'id': 'drwNoDate'})
        
        print(f"회차 요소: {round_elem}")
        print(f"날짜 요소: {date_elem}")
        
        if not round_elem or not date_elem:
            print("필수 요소를 찾을 수 없습니다")
            return False, {}
        
        ret_json = {
            "round": int(round_elem.text),
            "round_date": date_elem.text.replace('-', '.').strip('(').strip(')').strip('추첨'),
            "drw_1st": int(content_data.find('span', {'id': 'drwtNo1'}).text),
            "drw_2nd": int(content_data.find('span', {'id': 'drwtNo2'}).text),
            "drw_3rd": int(content_data.find('span', {'id': 'drwtNo3'}).text),
            "drw_4th": int(content_data.find('span', {'id': 'drwtNo4'}).text),
            "drw_5th": int(content_data.find('span', {'id': 'drwtNo5'}).text),
            "drw_6th": int(content_data.find('span', {'id': 'drwtNo6'}).text),
            "drw_bnus": int(content_data.find('span', {'id': 'bnusNo'}).text)
        }
        
        return True, ret_json
        
    except Exception as err:
        print(f"오류 발생: {err}")
        import traceback
        traceback.print_exc()
        return False, ret_json

if __name__ == '__main__':
    print("동행복권 메인 페이지에서 최신 회차 정보 가져오기 테스트\n")
    
    success, data = get_lotto_info()
    
    if success:
        print("\n✅ 크롤링 성공!")
        print(f"회차: {data['round']}회")
        print(f"추첨일: {data['round_date']}")
        print(f"당첨번호: {data['drw_1st']}, {data['drw_2nd']}, {data['drw_3rd']}, {data['drw_4th']}, {data['drw_5th']}, {data['drw_6th']}")
        print(f"보너스: {data['drw_bnus']}")
    else:
        print("\n❌ 크롤링 실패")

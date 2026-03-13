#!/usr/bin/env python3
"""构建A股股票列表缓存
通过深交所API + 上交所API + push2his验证
"""
import requests
import re
import csv
import os
import time
import json

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_FILE = os.path.join(CACHE_DIR, 'stock_list.csv')

headers_szse = {'Referer': 'https://www.szse.cn/', 'User-Agent': 'Mozilla/5.0'}
headers_sse = {'Referer': 'https://www.sse.com.cn/', 'User-Agent': 'Mozilla/5.0'}


def fetch_szse():
    """从深交所获取A股列表"""
    codes = {}
    for page in range(1, 200):
        try:
            r = requests.get('https://www.szse.cn/api/report/ShowReport/data', params={
                'SHOWTYPE': 'JSON', 'CATALOGID': '1110', 'TABKEY': 'tab1',
                'PAGENO': page, 'PAGECOUNT': 50
            }, timeout=15, headers=headers_szse)
            data = r.json()[0]
            rows = data.get('data', [])
            if not rows:
                break
            for row in rows:
                code = row.get('agdm', '').strip()
                name = re.sub(r'<[^>]+>', '', row.get('agjc', '')).strip()
                if code and code[:2] in ('00', '30') and 'ST' not in name and '退' not in name:
                    codes[code] = name
            total = int(data['metadata']['pagecount'])
            if page >= total:
                break
            if page % 10 == 0:
                print(f"  SZSE page {page}/{total}, got {len(codes)}")
                time.sleep(1)  # 避免限频
            else:
                time.sleep(0.3)
        except Exception as e:
            print(f"  SZSE page {page} error: {e}, retrying after 5s...")
            time.sleep(5)
            try:
                r = requests.get('https://www.szse.cn/api/report/ShowReport/data', params={
                    'SHOWTYPE': 'JSON', 'CATALOGID': '1110', 'TABKEY': 'tab1',
                    'PAGENO': page, 'PAGECOUNT': 50
                }, timeout=15, headers=headers_szse)
                data = r.json()[0]
                for row in data.get('data', []):
                    code = row.get('agdm', '').strip()
                    name = re.sub(r'<[^>]+>', '', row.get('agjc', '')).strip()
                    if code and code[:2] in ('00', '30') and 'ST' not in name and '退' not in name:
                        codes[code] = name
            except:
                print(f"  SZSE page {page} retry failed, stopping")
                break
    return codes


def fetch_sse():
    """从上交所获取A股列表"""
    codes = {}
    try:
        r = requests.get('https://query.sse.com.cn/sseQuery/commonQuery.do', params={
            'sqlId': 'COMMON_SSE_CP_GPJCTPZ_GPLB_GP_L',
            'isPagination': 'true',
            'pageHelp.pageSize': 5000,
            'pageHelp.pageNo': 1,
            'pageHelp.beginPage': 1,
            'pageHelp.endPage': 1,
        }, headers=headers_sse, timeout=15)
        data = r.json()
        for item in data.get('pageHelp', {}).get('data', []):
            code = item.get('SECURITY_CODE_A', '') or item.get('A_STOCK_CODE', '')
            name = item.get('SECURITY_ABBR_A', '') or item.get('COMPANY_ABBR', '')
            if code and (code.startswith('6') or code.startswith('68')) and '退' not in name:
                codes[code] = name
    except Exception as e:
        print(f"  SSE API failed: {e}")
    return codes


def verify_via_push2his(codes_to_check, batch_size=50):
    """通过push2his验证代码是否有效（有K线数据）"""
    valid = {}
    for i, (code, name) in enumerate(codes_to_check.items()):
        if i >= batch_size:
            break
        market = 1 if code.startswith('6') else 0
        try:
            r = requests.get('https://push2his.eastmoney.com/api/qt/stock/kline/get', params={
                'secid': f'{market}.{code}',
                'fields1': 'f1,f12,f14',
                'fields2': 'f51',
                'klt': 101, 'fqt': 1, 'lmt': 1
            }, timeout=5)
            data = r.json().get('data')
            if data and data.get('klines'):
                real_name = data.get('name', name)
                valid[code] = real_name or name
        except:
            pass
        time.sleep(0.1)
    return valid


def build_list():
    print("=== 构建A股股票列表 ===")
    
    # 1. SSE
    print("\n[1/3] 获取上交所股票...")
    sse_codes = fetch_sse()
    print(f"  上交所: {len(sse_codes)} 只")
    
    # 如果SSE API返回太少，补充验证
    if len(sse_codes) < 500:
        print("  SSE API返回较少，通过push2his补充验证...")
        # 生成主要代码范围
        candidates = {}
        for i in range(600000, 604000):
            c = f'{i:06d}'
            if c not in sse_codes:
                candidates[c] = ''
        extra = verify_via_push2his(candidates, batch_size=200)
        sse_codes.update(extra)
        print(f"  补充后上交所: {len(sse_codes)} 只")
    
    # 2. SZSE
    print("\n[2/3] 获取深交所股票...")
    szse_codes = fetch_szse()
    print(f"  深交所: {len(szse_codes)} 只")
    
    # 3. Merge & save
    all_codes = {}
    all_codes.update(sse_codes)
    all_codes.update(szse_codes)
    
    # Filter out empty-name SSE codes that have no data
    print(f"\n[3/3] 合计: {len(all_codes)} 只")
    
    with open(CACHE_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for c, n in sorted(all_codes.items()):
            writer.writerow([c, n])
    
    print(f"已保存到: {CACHE_FILE}")
    print(f"  沪市: {sum(1 for c in all_codes if c.startswith('6'))}")
    print(f"  科创板: {sum(1 for c in all_codes if c.startswith('68'))}")
    print(f"  深主板: {sum(1 for c in all_codes if c.startswith('00'))}")
    print(f"  创业板: {sum(1 for c in all_codes if c.startswith('30'))}")
    
    return all_codes


if __name__ == '__main__':
    build_list()

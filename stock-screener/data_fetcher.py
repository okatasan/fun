"""数据获取模块 - 使用 baostock 获取60分钟K线数据"""
import baostock as bs
import pandas as pd
import os
import csv
import time
from datetime import datetime, timedelta

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

_logged_in = False

def _ensure_login():
    global _logged_in
    if not _logged_in:
        bs.login()
        _logged_in = True


def get_all_stock_codes():
    """获取全A股代码列表（排除ST、退市、指数）"""
    cache_file = os.path.join(CACHE_DIR, 'stock_list.csv')
    
    # 使用缓存（1天内有效）
    if os.path.exists(cache_file):
        age = time.time() - os.path.getmtime(cache_file)
        if age < 86400:
            codes = {}
            with open(cache_file, 'r') as f:
                for row in csv.reader(f):
                    if len(row) >= 2:
                        codes[row[0]] = row[1]
            if len(codes) > 100:
                return codes
    
    _ensure_login()
    today = datetime.now().strftime('%Y-%m-%d')
    rs = bs.query_stock_basic()
    
    codes = {}
    while rs.next():
        row = rs.get_row_data()
        # row: [code, code_name, ipoDate, outDate, type, status]
        bs_code = row[0]   # sh.600000 or sz.000001
        name = row[1]
        stock_type = row[2] if len(row) > 4 else ''
        status = row[5] if len(row) > 5 else '1'
        
        # 只要A股（type=1表示股票），且在市（status=1）
        if len(row) > 5 and row[4] == '1' and row[5] == '1':
            # 提取纯代码
            pure_code = bs_code.split('.')[1]
            if pure_code[:2] in ('60', '00', '30'):
                if 'ST' not in name and '退' not in name:
                    codes[pure_code] = name
    
    # 保存缓存
    with open(cache_file, 'w', newline='') as f:
        writer = csv.writer(f)
        for c, n in sorted(codes.items()):
            writer.writerow([c, n])
    
    return codes


def _to_bs_code(code):
    """转换为baostock代码格式"""
    prefix = 'sh' if code.startswith('6') else 'sz'
    return f'{prefix}.{code}'


def get_60min_kline(code, limit=120):
    """获取单只股票60分钟K线数据
    
    Returns:
        DataFrame: datetime, open, close, high, low, volume, amount, pct_chg
    """
    _ensure_login()
    bs_code = _to_bs_code(code)
    
    # 取最近3个月数据
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')
    
    rs = bs.query_history_k_data_plus(
        bs_code,
        "date,time,open,high,low,close,volume,amount",
        start_date=start_date, end_date=end_date,
        frequency="60", adjustflag="3"
    )
    
    rows = []
    while rs.next():
        row = rs.get_row_data()
        try:
            rows.append({
                'datetime': f"{row[0]} {row[1][8:10]}:{row[1][10:12]}",
                'open': float(row[2]),
                'high': float(row[3]),
                'low': float(row[4]),
                'close': float(row[5]),
                'volume': float(row[6]),
                'amount': float(row[7]) if row[7] else 0,
                'pct_chg': 0,  # 计算
            })
        except (ValueError, IndexError):
            continue
    
    if not rows:
        return None
    
    df = pd.DataFrame(rows)
    # 计算涨跌幅
    df['pct_chg'] = (df['close'] / df['close'].shift(1) - 1) * 100
    df = df.tail(limit).reset_index(drop=True)
    return df


def get_daily_kline(code, days=60):
    """获取日线数据"""
    _ensure_login()
    bs_code = _to_bs_code(code)
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days * 2)).strftime('%Y-%m-%d')
    
    rs = bs.query_history_k_data_plus(
        bs_code,
        "date,open,high,low,close",
        start_date=start_date, end_date=end_date,
        frequency="d", adjustflag="3"
    )
    
    rows = []
    while rs.next():
        row = rs.get_row_data()
        try:
            rows.append({
                'date': row[0],
                'open': float(row[1]),
                'high': float(row[2]),
                'low': float(row[3]),
                'close': float(row[4]),
            })
        except (ValueError, IndexError):
            continue
    
    if not rows:
        return None
    
    df = pd.DataFrame(rows)
    df['pct_chg'] = (df['close'] / df['close'].shift(1) - 1) * 100
    return df.tail(days).reset_index(drop=True)


def cleanup():
    global _logged_in
    if _logged_in:
        bs.logout()
        _logged_in = False


if __name__ == '__main__':
    codes = get_all_stock_codes()
    print(f"共 {len(codes)} 只A股")
    print(f"  沪市: {sum(1 for c in codes if c.startswith('6'))}")
    print(f"  深主板: {sum(1 for c in codes if c.startswith('00'))}")
    print(f"  创业板: {sum(1 for c in codes if c.startswith('30'))}")
    
    df = get_60min_kline('000001')
    if df is not None:
        print(f"\n000001 60min: {len(df)} 根")
        print(df.tail(3))
    
    cleanup()

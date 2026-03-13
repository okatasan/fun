"""回测模块 - 统计突破后5/10/20日收益率"""
import pandas as pd
import numpy as np
from data_fetcher import get_daily_kline


def backtest_stock(code, signal_date, signal_price):
    """对单只股票回测突破后收益
    
    Args:
        code: 股票代码
        signal_date: 信号日期 (str, YYYY-MM-DD)
        signal_price: 突破时收盘价
    
    Returns:
        dict with returns at 5d, 10d, 20d or None
    """
    df = get_daily_kline(code, days=60)
    if df is None:
        return None
    
    # 找到信号日期之后的数据
    df['date'] = pd.to_datetime(df['date'])
    signal_dt = pd.to_datetime(signal_date)
    future = df[df['date'] > signal_dt].reset_index(drop=True)
    
    if len(future) < 5:
        return None
    
    result = {'code': code, 'signal_date': signal_date, 'signal_price': signal_price}
    
    for days, label in [(5, 'ret_5d'), (10, 'ret_10d'), (20, 'ret_20d')]:
        if len(future) >= days:
            ret = (future.iloc[days-1]['close'] - signal_price) / signal_price * 100
            result[label] = round(ret, 2)
        else:
            result[label] = None
    
    # 最大回撤（20日内）
    if len(future) >= 5:
        n = min(20, len(future))
        lows = future.iloc[:n]['low'].values
        max_dd = min((lows - signal_price) / signal_price * 100)
        result['max_drawdown'] = round(max_dd, 2)
    
    return result


def summarize_backtest(results):
    """汇总回测结果"""
    if not results:
        return "无回测数据"
    
    df = pd.DataFrame(results)
    summary = []
    summary.append(f"回测样本数: {len(df)}")
    
    for col in ['ret_5d', 'ret_10d', 'ret_20d']:
        valid = df[col].dropna()
        if len(valid) > 0:
            win_rate = (valid > 0).sum() / len(valid) * 100
            summary.append(f"\n{col}:")
            summary.append(f"  胜率: {win_rate:.1f}%")
            summary.append(f"  均值: {valid.mean():.2f}%")
            summary.append(f"  中位: {valid.median():.2f}%")
            summary.append(f"  最大: {valid.max():.2f}%")
            summary.append(f"  最小: {valid.min():.2f}%")
    
    if 'max_drawdown' in df.columns:
        dd = df['max_drawdown'].dropna()
        if len(dd) > 0:
            summary.append(f"\n最大回撤均值: {dd.mean():.2f}%")
    
    return '\n'.join(summary)

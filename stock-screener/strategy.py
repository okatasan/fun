"""平台收敛突破选股策略"""
import numpy as np
from scipy import stats


def check_platform(df_90):
    """条件1: 平台识别 - 区间振幅在5%~11.5%"""
    high = df_90['high'].max()
    low = df_90['low'].min()
    avg = df_90['close'].mean()
    amplitude = (high - low) / avg
    return 0.05 <= amplitude <= 0.115, amplitude


def check_slope(df_90):
    """条件2: 平台上倾/走平 - 线性回归斜率>=0"""
    closes = df_90['close'].values
    x = np.arange(len(closes))
    slope, _, _, _, _ = stats.linregress(x, closes)
    return slope >= 0, slope


def check_convergence(df_90):
    """条件3: 后段收敛 - 后30根波动率 < 前60根"""
    front = df_90.iloc[:60]['close']
    back = df_90.iloc[60:]['close']
    vol_front = front.std() / front.mean()
    vol_back = back.std() / back.mean()
    return vol_back < vol_front, vol_front, vol_back


def check_narrow_bars(df_90):
    """条件4: 末端窄幅 - 后30根中至少1段连续>=2根窄幅K线"""
    back_30 = df_90.iloc[60:]
    narrow = ((back_30['high'] - back_30['low']) / back_30['open'] < 0.01).values
    
    # 找连续窄幅段
    segments = 0
    count = 0
    for v in narrow:
        if v:
            count += 1
        else:
            if count >= 2:
                segments += 1
            count = 0
    if count >= 2:
        segments += 1
    
    return segments >= 1, segments


def check_breakout(df_full, df_90):
    """条件5: 突破信号 - 最近1~3根有大阳线突破平台最高价（涨幅>=4.5%）
    
    如果没有突破，返回 stage='convergence' 表示仍在收敛阶段
    """
    platform_high = df_90['high'].max()
    
    # 最近1~3根
    recent = df_90.tail(3)
    
    for _, bar in recent.iterrows():
        pct = (bar['close'] - bar['open']) / bar['open'] * 100
        if pct >= 4.5 and bar['close'] > platform_high:
            return True, pct, bar['close'], platform_high, 'breakout'
    
    return False, 0, 0, platform_high, 'convergence'


def screen_stock(df):
    """对单只股票执行全部筛选条件
    
    Args:
        df: 60分钟K线DataFrame，至少90根
    
    Returns:
        (passed, details_dict)
    """
    if df is None or len(df) < 90:
        return False, {'reason': f'数据不足: {len(df) if df is not None else 0}根'}
    
    # 使用最后93根（90+3用于突破检测），若不足93根则用最后90根
    if len(df) >= 93:
        df_full = df.tail(93).reset_index(drop=True)
        df_90 = df_full.iloc[:90]
    else:
        df_full = df.tail(90).reset_index(drop=True)
        df_90 = df_full
    
    details = {}
    
    # 条件1
    ok, amp = check_platform(df_90)
    details['amplitude'] = f'{amp:.4f}'
    if not ok:
        return False, {**details, 'reason': f'振幅{amp:.4f}不在5%-11.5%'}
    
    # 条件2
    ok, slope = check_slope(df_90)
    details['slope'] = f'{slope:.6f}'
    if not ok:
        return False, {**details, 'reason': f'斜率{slope:.6f}<0'}
    
    # 条件3
    ok, vf, vb = check_convergence(df_90)
    details['vol_front'] = f'{vf:.6f}'
    details['vol_back'] = f'{vb:.6f}'
    if not ok:
        return False, {**details, 'reason': f'未收敛 前{vf:.6f} 后{vb:.6f}'}
    
    # 条件4
    ok, segs = check_narrow_bars(df_90)
    details['narrow_segments'] = segs
    if not ok:
        return False, {**details, 'reason': f'窄幅段仅{segs}段<1'}
    
    # 条件5
    ok, pct, close_price, plat_high, stage = check_breakout(df_full, df_90)
    details['breakout_pct'] = f'{pct:.2f}%'
    details['platform_high'] = plat_high
    details['stage'] = stage
    if not ok:
        # 收敛阶段，仍然返回为候选（标记为convergence）
        details['signal'] = 'CONVERGENCE'
        return True, details
    
    details['signal'] = 'BREAKOUT'
    return True, details

#!/usr/bin/env python3
"""A股平台收敛突破选股系统 - 主程序"""
import sys
import os
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from data_fetcher import get_all_stock_codes, get_60min_kline, cleanup
from strategy import screen_stock
from backtest import backtest_stock, summarize_backtest
try:
    from wechat_notify import send_notification_if_needed
except ImportError:
    def send_notification_if_needed():
        print("⚠️  企业微信通知模块未安装，跳过通知")
        return False


def run_screener(max_stocks=None, output_file=None):
    """执行全A股扫描
    
    Args:
        max_stocks: 限制扫描数量（调试用）
        output_file: 输出文件路径
    """
    print(f"[{datetime.now()}] 开始扫描...")
    
    # 获取股票列表
    code_name = get_all_stock_codes()
    codes = list(code_name.keys())
    if max_stocks:
        codes = codes[:max_stocks]
    
    print(f"共 {len(codes)} 只股票待扫描")
    
    hits = []
    errors = 0
    
    import sys as _sys
    for i, code in enumerate(codes):
        if (i + 1) % 20 == 0:
            print(f"  进度: {i+1}/{len(codes)}, 命中: {len(hits)}, 错误: {errors}", flush=True)
        
        try:
            df = get_60min_kline(code, limit=120)
            passed, details = screen_stock(df)
            if passed:
                details['code'] = code
                details['name'] = code_name.get(code, '')
                hits.append(details)
                print(f"  ✅ {code} {code_name.get(code,'')} - {details}")
        except Exception as e:
            errors += 1
        
        # baostock已有内在延迟，不需额外sleep
    
    print(f"\n[{datetime.now()}] 扫描完成!")
    print(f"总计: {len(codes)} 只, 命中: {len(hits)} 只, 错误: {errors}")
    
    # 输出结果
    if not output_file:
        output_file = os.path.join(os.path.dirname(__file__), 
                                    f'result_{datetime.now().strftime("%Y%m%d_%H%M")}.json')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(hits, f, ensure_ascii=False, indent=2)
    print(f"结果已保存到: {output_file}")
    
    # 生成文本报告
    report = format_report(hits, code_name)
    report_file = output_file.replace('.json', '.txt')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"报告已保存到: {report_file}")
    
    return hits, report


def format_report(hits, code_name=None):
    """格式化选股报告"""
    lines = []
    lines.append(f"📊 A股平台收敛突破扫描报告")
    lines.append(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"📈 命中: {len(hits)} 只\n")
    
    if not hits:
        lines.append("今日无符合条件的股票。")
    else:
        for h in hits:
            lines.append(f"🔥 {h.get('code','')} {h.get('name','')}")
            lines.append(f"   振幅: {h.get('amplitude','')}")
            lines.append(f"   突破: {h.get('breakout_pct','')}")
            lines.append(f"   平台高: {h.get('platform_high','')}")
            lines.append("")
    
    return '\n'.join(lines)


def run_backtest_on_hits(hits):
    """对命中股票执行回测"""
    if not hits:
        return "无命中，跳过回测"
    
    results = []
    for h in hits:
        code = h['code']
        # 从60min K线的最后日期提取信号日期
        signal_date = datetime.now().strftime('%Y-%m-%d')
        signal_price = float(h.get('platform_high', 0))
        
        r = backtest_stock(code, signal_date, signal_price)
        if r:
            results.append(r)
    
    return summarize_backtest(results)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='A股平台收敛突破选股')
    parser.add_argument('-n', '--max', type=int, default=None, help='最大扫描数量')
    parser.add_argument('-o', '--output', type=str, default=None, help='输出文件')
    parser.add_argument('--test', action='store_true', help='测试模式(扫描前50只)')
    parser.add_argument('--notify', action='store_true', default=True, help='发送企业微信通知（默认开启）')
    args = parser.parse_args()
    
    n = args.max or (50 if args.test else None)
    try:
        hits, report = run_screener(max_stocks=n, output_file=args.output)
        print("\n" + report)
        
        if hits:
            print("\n开始回测...")
            bt = run_backtest_on_hits(hits)
            print(bt)
    finally:
        cleanup()
        
        # 发送企业微信通知
        if args.notify:
            send_notification_if_needed()
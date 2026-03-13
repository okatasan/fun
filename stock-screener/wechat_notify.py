#!/usr/bin/env python3
"""企业微信webhook通知模块"""
import os
import json
import requests
from datetime import datetime


def send_wechat_work_webhook(webhook_url, title, content, result_file=None):
    """发送企业微信webhook通知
    
    Args:
        webhook_url: 企业微信机器人webhook URL
        title: 通知标题
        content: 通知内容
        result_file: 可选的结果文件路径，会作为markdown附件
    """
    try:
        # 构建消息
        text = f"**{title}**\n\n{content}"
        
        if result_file and os.path.exists(result_file):
            with open(result_file, 'r', encoding='utf-8') as f:
                result_data = json.load(f)
                hits = len(result_data)
                text += f"\n\n📈 命中股票数: {hits}"
                if hits > 0:
                    text += "\n\n🚀 命中股票:"
                    for i, stock in enumerate(result_data[:5]):  # 最多显示5只
                        text += f"\n{i+1}. {stock.get('code', '')} {stock.get('name', '')}"
                    if hits > 5:
                        text += f"\n... 等{hits}只股票"
        
        text += f"\n\n⏰ 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": text
            }
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ 企业微信通知发送成功")
            return True
        else:
            print(f"❌ 企业微信通知失败: {response.status_code} {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 发送企业微信通知时出错: {e}")
        return False


def send_notification_if_needed():
    """检查环境变量并发送通知（用于集成到main.py）"""
    webhook_url = os.environ.get('WECHAT_WORK_WEBHOOK')
    if not webhook_url:
        print("⚠️  未设置WECHAT_WORK_WEBHOOK环境变量，跳过通知")
        return False
    
    result_file = 'result.json'
    if not os.path.exists(result_file):
        result_file = None
        for f in os.listdir('.'):
            if f.startswith('result_') and f.endswith('.json'):
                result_file = f
                break
    
    content = "股票扫描任务已完成"
    if result_file:
        try:
            with open(result_file, 'r', encoding='utf-8') as f:
                hits = len(json.load(f))
                content = f"股票扫描完成，命中 {hits} 只股票"
        except:
            content = "股票扫描完成"
    
    return send_wechat_work_webhook(
        webhook_url,
        "🎯 A股平台收敛突破扫描结果",
        content,
        result_file
    )


if __name__ == '__main__':
    # 测试用
    webhook_url = os.environ.get('WECHAT_WORK_WEBHOOK')
    if webhook_url:
        send_wechat_work_webhook(
            webhook_url,
            "🎯 测试通知",
            "这是一条测试消息，验证企业微信webhook配置是否正常。"
        )
    else:
        print("请设置 WECHAT_WORK_WEBHOOK 环境变量")
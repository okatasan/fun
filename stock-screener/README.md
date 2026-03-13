# A股平台收敛突破选股系统

基于平台收敛突破策略的A股自动选股系统，每日自动扫描全市场股票，识别符合技术形态的候选标的。

## 功能特点

- 📈 **全市场扫描**：覆盖沪深A股（沪市、深主板、创业板）
- ⏰ **自动定时运行**：每日11:33和15:08自动执行（北京时间）
- 🔔 **即时通知**：通过企业微信机器人推送选股结果
- 📊 **数据验证**：使用baostock获取权威K线数据
- 🧪 **策略回测**：对命中股票进行简单回测分析

## 文件结构

```
stock-screener/
├── main.py                    # 主程序
├── data_fetcher.py           # 数据获取模块
├── strategy.py               # 选股策略逻辑
├── backtest.py               # 回测模块
├── build_stock_list.py       # 股票列表构建
├── wechat_notify.py          # 企业微信通知模块
├── requirements.txt          # Python依赖
├── .github/workflows/
│   └── stock-screener.yml    # GitHub Actions工作流
└── README.md                 # 本文档
```

## 快速开始

### 1. 环境配置

```bash
pip install -r requirements.txt
```

### 2. 本地测试

```bash
# 测试模式（扫描前50只股票）
python main.py --test

# 完整扫描（最多200只，避免超时）
python main.py --max 200
```

### 3. GitHub Actions配置

1. 将代码推送到GitHub仓库
2. 在仓库设置中配置secrets：
   - `WECHAT_WORK_WEBHOOK`: 企业微信机器人webhook URL
3. 工作流会自动在指定时间运行

## 配置说明

### 企业微信机器人配置

1. 在企业微信中创建群聊
2. 添加「群机器人」
3. 获取webhook URL
4. 在GitHub仓库的 Settings → Secrets → Actions 中添加：
   - Name: `WECHAT_WORK_WEBHOOK`
   - Value: 你的webhook URL

### 运行时间

- **北京时间周一至周五**
  - 11:33 (UTC 03:33)
  - 15:08 (UTC 07:08)

如需修改时间，编辑 `.github/workflows/stock-screener.yml` 中的cron表达式。

## 选股策略

基于「平台收敛突破」技术形态：
1. 识别股价在窄幅区间内震荡的平台期
2. 监测价格突破平台高点
3. 结合量能验证突破有效性

## 输出结果

每次运行生成：
- `result_YYYYMMDD_HHMM.json`: 详细的选股结果（JSON格式）
- `result_YYYYMMDD_HHMM.txt`: 简明的文本报告
- 企业微信通知：包含命中股票数量和前几名详情

## 注意事项

1. **数据源**：使用baostock免费数据，请遵守相关使用协议
2. **运行频率**：避免过于频繁请求，以免被限制
3. **策略验证**：本系统仅供技术参考，不构成投资建议
4. **网络要求**：GitHub Actions需要能够访问baostock API

## 故障排除

### 常见问题

1. **baostock登录失败**
   - 检查网络连接
   - 确认baostock服务正常

2. **企业微信通知未发送**
   - 检查`WECHAT_WORK_WEBHOOK`环境变量
   - 确认webhook URL有效

3. **运行超时**
   - GitHub Actions默认超时6小时
   - 如需调整，修改工作流中的`timeout-minutes`

## 许可证

本项目仅供学习研究使用。
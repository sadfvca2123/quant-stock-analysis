# -*- coding: utf-8 -*-
"""全局配置"""
import os
from dotenv import load_dotenv

load_dotenv()

# === 股票列表 ===
STOCK_LIST = os.getenv("STOCK_LIST", "000620,000657,002445,600032,002490,002498,002969")

# === DeepSeek AI 配置 ===
DEEPSEEK_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("OPENAI_MODEL", "deepseek-chat")

# === Tushare Token (可选) ===
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")

# === 企业微信推送 ===
WECHAT_WEBHOOK_URL = os.getenv("WECHAT_WEBHOOK_URL", "")

# === QMT 配置 (可选, 需要 miniQMT 客户端运行) ===
QMT_ENABLED = os.getenv("QMT_ENABLED", "false").lower() == "true"
QMT_DATA_PATH = os.getenv("QMT_DATA_PATH", "")

# === 数据源优先级 ===
# akshare | tushare | qmt
DATA_SOURCE_PRIORITY = os.getenv("DATA_SOURCE_PRIORITY", "akshare,tushare").split(",")

# === 量化参数 ===
MA_PERIODS = [5, 10, 20, 60, 120, 250]
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BOLL_PERIOD = 20
BOLL_STD = 2.0
KDJ_PERIOD = 9

# === 选股阈值 ===
# 多头排列: MA5 > MA10 > MA20
# 乖离率 > 5% 风险
BIAS_RISK_THRESHOLD = 5.0
# RSI 超买/超卖
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# === Web 服务 ===
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))

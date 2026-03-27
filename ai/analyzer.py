# -*- coding: utf-8 -*-
"""
===================================
AI 分析模块 - DeepSeek 驱动
===================================
使用 DeepSeek 大模型进行股票分析和推荐
"""
import httpx
from typing import List, Dict, Optional
import json
import config


class AIAnalyzer:
    """DeepSeek AI 分析器"""
    
    def __init__(self):
        self.api_key = config.DEEPSEEK_API_KEY
        self.base_url = config.DEEPSEEK_BASE_URL
        self.model = config.DEEPSEEK_MODEL
        self.client = httpx.Client(base_url=self.base_url, timeout=60.0)
    
    def _call_api(self, messages: List[Dict], temperature: float = 0.7) -> str:
        """调用 DeepSeek API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096
        }
        resp = self.client.post("/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    
    def analyze_stock(self, stock_code: str, stock_data: Dict) -> str:
        """分析单只股票"""
        prompt = f"""你是一位专业的A股分析师。请分析以下股票数据，给出投资建议。

股票代码: {stock_code}
股票名称: {stock_data.get('name', '未知')}
当前价格: {stock_data.get('close', 0):.2f}
涨跌幅: {stock_data.get('pct_change', 0):.2f}%

技术指标:
- MA5: {stock_data.get('MA5', 0):.2f}
- MA10: {stock_data.get('MA10', 0):.2f}
- MA20: {stock_data.get('MA20', 0):.2f}
- RSI: {stock_data.get('RSI', 0):.2f}
- MACD: {stock_data.get('MACD', 0):.4f}
- KDJ_K: {stock_data.get('KDJ_K', 0):.2f}
- 布林带位置: {stock_data.get('BOLL_POS', '中轨')}

请从以下维度分析:
1. 趋势判断 (多头/空头/震荡)
2. 买卖信号 (MACD金叉死叉/RSI超买超卖/KDJ交叉)
3. 风险提示 (乖离率/布林带突破)
4. 操作建议 (买入/观望/卖出, 附带价格区间)
5. 止盈止损位

请用简洁的格式输出，适合微信阅读。"""
        
        messages = [{"role": "user", "content": prompt}]
        return self._call_api(messages)
    
    def generate_report(self, analysis_results: List[Dict]) -> str:
        """生成汇总报告"""
        prompt = f"""你是一位专业的投资顾问。请根据以下股票分析结果，生成一份投资决策报告。

分析结果:
{json.dumps(analysis_results, ensure_ascii=False, indent=2)}

请生成:
1. 市场整体判断
2. 推荐买入的股票 (附理由)
3. 建议观望的股票
4. 需要规避的股票
5. 仓位建议

格式要求: 适合企业微信阅读，使用emoji，简洁明了。"""
        
        messages = [{"role": "user", "content": prompt}]
        return self._call_api(messages)
    
    def recommend_stocks(self, watchlist: List[str], market_data: Dict) -> List[str]:
        """AI 推荐股票"""
        prompt = f"""你是一位量化选股专家。请从以下股票池中推荐值得关注的股票。

股票池: {watchlist}

市场数据:
- 涨跌家数: {market_data.get('up_count', 0)}涨 / {market_data.get('down_count', 0)}跌
- 北向资金: {market_data.get('north_flow', 0):.2f}亿
- 热门板块: {market_data.get('hot_sectors', [])}

请推荐3-5只股票，并说明推荐理由。输出格式:
股票代码 | 推荐理由"""
        
        messages = [{"role": "user", "content": prompt}]
        return self._call_api(messages)
# -*- coding: utf-8 -*-
"""
===================================
智能量化选股分析系统 - 主程序
===================================
功能:
1. 多数据源获取行情 (AkShare / Tushare / QMT)
2. 量化因子计算 (MA, MACD, RSI, KDJ, BOLL等)
3. 多因子选股模型
4. AI 智能分析 (DeepSeek)
5. 企业微信推送
6. Web 服务 (FastAPI)
7. GitHub Actions 定时执行
"""
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
import config
from data import DataProvider
from quant import StockScreener
from ai import AIAnalyzer
from notify import WeChatNotifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_analysis(stock_list: list = None, send_notify: bool = True):
    """执行完整的选股分析流程"""
    
    # 1. 获取股票列表
    if stock_list is None:
        stock_list = [s.strip() for s in config.STOCK_LIST.split(',') if s.strip()]
    
    logger.info(f"开始分析股票: {stock_list}")
    
    # 2. 初始化数据提供者
    provider = DataProvider(source="akshare")
    
    # 3. 获取历史数据
    stock_data = {}
    for code in stock_list:
        try:
            df = provider.get_stock_history(code, days=250)
            if df is not None and len(df) > 60:
                stock_data[code] = df
                logger.info(f"获取 {code} 数据成功: {len(df)} 条")
            else:
                logger.warning(f"获取 {code} 数据失败或数据不足")
        except Exception as e:
            logger.error(f"获取 {code} 数据异常: {e}")
    
    if not stock_data:
        logger.error("没有获取到任何股票数据")
        return
    
    # 4. 多因子选股
    screener = StockScreener(stock_data)
    scores = screener.calc_factor_scores()
    recommendations = screener.get_recommendations(top_n=10)
    
    logger.info(f"选股结果: {len(recommendations)} 只")
    
    # 5. AI 深度分析
    ai_analyzer = AIAnalyzer()
    analysis_results = []
    
    for _, row in recommendations.iterrows():
        code = row['code']
        df = stock_data[code]
        latest = df.iloc[-1]
        
        stock_info = {
            'name': code,
            'close': latest.get('close', 0),
            'pct_change': latest.get('pct_change', 0),
            'MA5': latest.get('MA5', 0),
            'MA10': latest.get('MA10', 0),
            'MA20': latest.get('MA20', 0),
            'RSI': latest.get('RSI', 0),
            'MACD': latest.get('MACD', 0),
            'KDJ_K': latest.get('KDJ_K', 0),
        }
        
        try:
            ai_analysis = ai_analyzer.analyze_stock(code, stock_info)
            analysis_results.append({
                'code': code,
                'name': code,
                'close': latest.get('close', 0),
                'pct_change': latest.get('pct_change', 0),
                'score': row['total_score'],
                'advice': row.get('advice', '观望'),
                'emoji': '🟢' if row['total_score'] > 70 else ('🟡' if row['total_score'] > 50 else '🔴'),
                'ai_analysis': ai_analysis
            })
        except Exception as e:
            logger.error(f"AI分析 {code} 失败: {e}")
            analysis_results.append({
                'code': code,
                'name': code,
                'close': latest.get('close', 0),
                'pct_change': latest.get('pct_change', 0),
                'score': row['total_score'],
                'advice': row.get('advice', '观望'),
                'emoji': '🟢' if row['total_score'] > 70 else ('🟡' if row['total_score'] > 50 else '🔴'),
                'ai_analysis': 'AI分析失败'
            })
    
    # 6. 生成报告
    if send_notify and config.WECHAT_WEBHOOK_URL:
        notifier = WeChatNotifier()
        notifier.send_analysis(analysis_results)
        logger.info("报告已推送至企业微信")
    
    # 7. 打印摘要
    logger.info("\n" + "="*50)
    logger.info("📊 分析结果摘要")
    logger.info("="*50)
    for r in analysis_results:
        logger.info(f"{r['emoji']} {r['code']}: {r['advice']} (得分: {r['score']:.1f})")
    
    return analysis_results


def main():
    parser = argparse.ArgumentParser(description='智能量化选股分析系统')
    parser.add_argument('--stocks', type=str, help='股票代码，逗号分隔')
    parser.add_argument('--no-notify', action='store_true', help='不发送推送')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    stock_list = args.stocks.split(',') if args.stocks else None
    send_notify = not args.no_notify
    
    results = run_analysis(stock_list=stock_list, send_notify=send_notify)
    
    logger.info("\n✅ 分析完成!")
    return 0 if results else 1


if __name__ == '__main__':
    sys.exit(main())
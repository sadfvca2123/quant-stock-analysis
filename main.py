# -*- coding: utf-8 -*-
"""
===================================
智能量化选股分析系统 - 主程序
===================================
"""
import argparse
import logging
import sys
import config
from data.provider import DataProvider
from quant.factors import calc_all_factors
from quant.stock_screener import StockScreener
from ai.analyzer import AIAnalyzer
from notify.wechat import WeChatNotifier

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
    
    # 3. 获取历史数据并计算因子
    stock_data = {}
    for code in stock_list:
        try:
            df = provider.get_stock_history(code, days=250)
            if df is not None and len(df) > 60:
                df = calc_all_factors(df)
                stock_data[code] = df
                logger.info(f"获取 {code} 数据成功: {len(df)} 条")
            else:
                logger.warning(f"获取 {code} 数据失败或数据不足")
        except Exception as e:
            logger.error(f"获取 {code} 数据异常: {e}")
    
    if not stock_data:
        logger.error("没有获取到任何股票数据")
        return []
    
    # 4. 多因子选股
    screener = StockScreener(stock_data)
    scores = screener.calc_factor_scores()
    recommendations = screener.get_recommendations(top_n=10)
    
    logger.info(f"选股结果: {len(recommendations)} 只")
    
    if recommendations.empty:
        logger.warning("没有符合条件的股票")
        return []
    
    # 5. AI 深度分析
    ai_analyzer = AIAnalyzer()
    analysis_results = []
    
    for _, row in recommendations.iterrows():
        # 列名是 stock_code
        code = row.get('stock_code', row.get('code', ''))
        if not code:
            continue
            
        df = stock_data.get(code)
        if df is None:
            continue
            
        latest = df.iloc[-1]
        
        stock_info = {
            'name': code,
            'close': float(latest.get('close', 0)),
            'pct_change': float(latest.get('pct_change', 0)),
            'MA5': float(latest.get('MA5', 0)) if 'MA5' in latest.index else 0.0,
            'MA10': float(latest.get('MA10', 0)) if 'MA10' in latest.index else 0.0,
            'MA20': float(latest.get('MA20', 0)) if 'MA20' in latest.index else 0.0,
            'RSI': float(latest.get('RSI', 50)) if 'RSI' in latest.index else 50.0,
            'MACD': float(latest.get('MACD', 0)) if 'MACD' in latest.index else 0.0,
            'KDJ_K': float(latest.get('KDJ_K', 50)) if 'KDJ_K' in latest.index else 50.0,
        }
        
        score = float(row.get('total_score', 0))
        advice = row.get('reason', '综合评分')
        
        try:
            ai_analysis = ai_analyzer.analyze_stock(code, stock_info)
        except Exception as e:
            logger.error(f"AI分析 {code} 失败: {e}")
            ai_analysis = "AI分析暂时不可用"
        
        analysis_results.append({
            'code': code,
            'name': code,
            'close': stock_info['close'],
            'pct_change': stock_info['pct_change'],
            'score': score,
            'advice': advice,
            'emoji': '🟢' if score > 0.6 else ('🟡' if score > 0.4 else '🔴'),
            'ai_analysis': ai_analysis
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
        logger.info(f"{r['emoji']} {r['code']}: {r['advice']} (得分: {r['score']:.2f})")
    
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
# -*- coding: utf-8 -*-
"""
多因子选股模型模块
Multi-Factor Stock Screener

功能:
- 多因子综合打分选股
- 支持趋势、动量、量价、波动因子筛选
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional


class StockScreener:
    """
    多因子选股器
    
    因子权重配置:
    - 趋势因子(多头排列): 30%
    - 动量因子(RSI, MACD): 25%
    - 量价因子: 25%
    - 波动因子(ATR, BOLL): 20%
    """
    
    # 因子权重
    WEIGHTS = {
        'trend': 0.30,      # 趋势因子
        'momentum': 0.25,   # 动量因子
        'volume': 0.25,     # 量价因子
        'volatility': 0.20  # 波动因子
    }
    
    def __init__(self, df_dict: Dict[str, pd.DataFrame]):
        """
        初始化选股器
        
        Args:
            df_dict: 股票数据字典，格式: {stock_code: DataFrame}
                   DataFrame需包含列: 'close', 'open', 'high', 'low', 'volume'
        """
        self.df_dict = df_dict
        self.results = {}
        
    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        准备计算因子所需的基础数据
        
        Args:
            df: 原始DataFrame
            
        Returns:
            添加技术指标后的DataFrame
        """
        data = df.copy()
        
        # 计算移动平均线
        data['MA5'] = data['close'].rolling(window=5).mean()
        data['MA10'] = data['close'].rolling(window=10).mean()
        data['MA20'] = data['close'].rolling(window=20).mean()
        
        # 计算RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))
        
        # 计算MACD
        exp12 = data['close'].ewm(span=12, adjust=False).mean()
        exp26 = data['close'].ewm(span=26, adjust=False).mean()
        data['MACD'] = exp12 - exp26
        data['MACD_signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
        data['MACD_hist'] = data['MACD'] - data['MACD_signal']
        
        # 计算成交量均线
        data['VOL_MA5'] = data['volume'].rolling(window=5).mean()
        data['VOL_MA20'] = data['volume'].rolling(window=20).mean()
        
        # 计算ATR (Average True Range)
        high_low = data['high'] - data['low']
        high_close = np.abs(data['high'] - data['close'].shift())
        low_close = np.abs(data['low'] - data['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data['ATR'] = tr.rolling(window=14).mean()
        
        # 计算BOLL (Bollinger Bands)
        data['BOLL_MID'] = data['close'].rolling(window=20).mean()
        std = data['close'].rolling(window=20).std()
        data['BOLL_UPPER'] = data['BOLL_MID'] + 2 * std
        data['BOLL_LOWER'] = data['BOLL_MID'] - 2 * std
        data['BOLL_WIDTH'] = (data['BOLL_UPPER'] - data['BOLL_LOWER']) / data['BOLL_MID']
        
        return data
    
    def _calc_trend_score(self, data: pd.DataFrame) -> float:
        """
        计算趋势因子得分
        
        多头排列: MA5 > MA10 > MA20
        部分多头: MA5 > MA10 或 MA5 > MA20
        """
        if data.empty or pd.isna(data['MA5'].iloc[-1]):
            return 0.0
            
        ma5 = data['MA5'].iloc[-1]
        ma10 = data['MA10'].iloc[-1]
        ma20 = data['MA20'].iloc[-1]
        
        # 多头排列得分
        if ma5 > ma10 > ma20:
            return 1.0
        elif ma5 > ma10:
            return 0.7
        elif ma5 > ma20:
            return 0.5
        elif ma10 > ma20:
            return 0.3
        else:
            return 0.0
    
    def _calc_momentum_score(self, data: pd.DataFrame) -> float:
        """
        计算动量因子得分
        
        结合RSI和MACD
        """
        if data.empty or pd.isna(data['RSI'].iloc[-1]):
            return 0.0
            
        rsi = data['RSI'].iloc[-1]
        macd_hist = data['MACD_hist'].iloc[-1] if not pd.isna(data['MACD_hist'].iloc[-1]) else 0
        
        # RSI得分 (30-70区间内为正常，超出为超买/超卖)
        if rsi >= 30 and rsi <= 70:
            rsi_score = 0.5
        elif rsi < 30:
            rsi_score = 0.8  # 超卖，可能反弹
        else:  # rsi > 70
            rsi_score = 0.4  # 超买
            
        # MACD得分
        if macd_hist > 0:
            macd_score = min(1.0, 0.5 + macd_hist / data['close'].iloc[-1] * 10)
        else:
            macd_score = max(0.0, 0.5 + macd_hist / data['close'].iloc[-1] * 10)
        
        # 综合动量得分
        momentum_score = rsi_score * 0.5 + macd_score * 0.5
        return min(1.0, max(0.0, momentum_score))
    
    def _calc_volume_score(self, data: pd.DataFrame) -> float:
        """
        计算量价因子得分
        
        价涨量增为健康配合
        """
        if data.empty or pd.isna(data['VOL_MA5'].iloc[-1]):
            return 0.0
            
        # 近期涨跌幅
        if len(data) >= 5:
            price_change = (data['close'].iloc[-1] - data['close'].iloc[-5]) / data['close'].iloc[-5]
        else:
            price_change = 0.0
            
        # 成交量变化
        vol_ratio = data['volume'].iloc[-1] / data['VOL_MA5'].iloc[-1] if data['VOL_MA5'].iloc[-1] > 0 else 1.0
        
        # 价涨量增为最佳
        if price_change > 0 and vol_ratio > 1.0:
            return min(1.0, 0.7 + vol_ratio * 0.1)
        elif price_change > 0 and vol_ratio > 0.5:
            return 0.6
        elif price_change < 0 and vol_ratio < 1.0:
            return 0.4  # 价跌量缩，可能见底
        else:
            return 0.3
    
    def _calc_volatility_score(self, data: pd.DataFrame) -> float:
        """
        计算波动因子得分
        
        选取波动适中(BOLL收口)的股票
        """
        if data.empty or pd.isna(data['BOLL_WIDTH'].iloc[-1]):
            return 0.0
            
        boll_width = data['BOLL_WIDTH'].iloc[-1]
        
        # BOLL收口表示波动降低，可能蓄势
        if boll_width < 0.03:
            return 0.9  # 窄幅震荡，可能突破
        elif boll_width < 0.05:
            return 0.7
        elif boll_width < 0.10:
            return 0.5
        else:
            return 0.3
    
    def calc_factor_scores(self) -> Dict[str, Dict]:
        """
        计算每只股票的因子得分
        
        Returns:
            股票得分字典: {stock_code: {
                'trend_score': float,
                'momentum_score': float,
                'volume_score': float,
                'volatility_score': float,
                'total_score': float
            }}
        """
        results = {}
        
        for stock_code, df in self.df_dict.items():
            try:
                data = self._prepare_data(df)
                
                if len(data) < 20:  # 需要足够的历史数据
                    continue
                
                # 计算各因子得分
                trend_score = self._calc_trend_score(data)
                momentum_score = self._calc_momentum_score(data)
                volume_score = self._calc_volume_score(data)
                volatility_score = self._calc_volatility_score(data)
                
                # 计算加权总分
                total_score = (
                    trend_score * self.WEIGHTS['trend'] +
                    momentum_score * self.WEIGHTS['momentum'] +
                    volume_score * self.WEIGHTS['volume'] +
                    volatility_score * self.WEIGHTS['volatility']
                )
                
                results[stock_code] = {
                    'trend_score': round(trend_score, 3),
                    'momentum_score': round(momentum_score, 3),
                    'volume_score': round(volume_score, 3),
                    'volatility_score': round(volatility_score, 3),
                    'total_score': round(total_score, 3)
                }
                
            except Exception as e:
                print(f"Error processing {stock_code}: {e}")
                continue
        
        self.results = results
        return results
    
    def screen_by_trend(self) -> list:
        """
        筛选多头排列股票 (MA5 > MA10 > MA20)
        
        Returns:
            多头排列股票代码列表
        """
        trend_stocks = []
        
        for stock_code, df in self.df_dict.items():
            try:
                data = self._prepare_data(df)
                
                if len(data) < 20:
                    continue
                    
                ma5 = data['MA5'].iloc[-1]
                ma10 = data['MA10'].iloc[-1]
                ma20 = data['MA20'].iloc[-1]
                
                if ma5 > ma10 > ma20:
                    trend_stocks.append(stock_code)
                    
            except Exception:
                continue
                
        return trend_stocks
    
    def screen_by_rsi(self, oversold: float = 30, overbought: float = 70) -> Dict[str, str]:
        """
        RSI筛选
        
        Args:
            oversold: 超卖阈值，默认30
            overbought: 超买阈值，默认70
            
        Returns:
            股票代码及RSI状态: {stock_code: 'oversold'|'neutral'|'overbought'}
        """
        rsi_results = {}
        
        for stock_code, df in self.df_dict.items():
            try:
                data = self._prepare_data(df)
                
                if len(data) < 20:
                    continue
                    
                rsi = data['RSI'].iloc[-1]
                
                if pd.isna(rsi):
                    continue
                elif rsi < oversold:
                    rsi_results[stock_code] = 'oversold'
                elif rsi > overbought:
                    rsi_results[stock_code] = 'overbought'
                else:
                    rsi_results[stock_code] = 'neutral'
                    
            except Exception:
                continue
                
        return rsi_results
    
    def screen_by_volume(self) -> list:
        """
        量价配合筛选
        
        条件: 价涨量增 或 价跌量缩
        
        Returns:
            符合量价配合条件的股票列表
        """
        volume_stocks = []
        
        for stock_code, df in self.df_dict.items():
            try:
                data = self._prepare_data(df)
                
                if len(data) < 20:
                    continue
                
                # 近期涨跌幅
                price_change = (data['close'].iloc[-1] - data['close'].iloc[-5]) / data['close'].iloc[-5]
                
                # 成交量变化
                vol_ratio = data['volume'].iloc[-1] / data['VOL_MA5'].iloc[-1] if data['VOL_MA5'].iloc[-1] > 0 else 1.0
                
                # 价涨量增 或 价跌量缩
                if (price_change > 0 and vol_ratio > 1.0) or (price_change < 0 and vol_ratio < 1.0):
                    volume_stocks.append(stock_code)
                    
            except Exception:
                continue
                
        return volume_stocks
    
    def screen_by_macd(self) -> list:
        """
        MACD金叉筛选
        
        条件: MACD柱状图由负转正 (MACD > MACD_signal)
        
        Returns:
            符合MACD金叉条件的股票列表
        """
        macd_stocks = []
        
        for stock_code, df in self.df_dict.items():
            try:
                data = self._prepare_data(df)
                
                if len(data) < 20:
                    continue
                
                macd = data['MACD'].iloc[-1]
                signal = data['MACD_signal'].iloc[-1]
                
                # 前一时刻MACD柱状图
                if len(data) >= 2:
                    prev_macd = data['MACD'].iloc[-2]
                    prev_signal = data['MACD_signal'].iloc[-2]
                    
                    # 金叉: 当前MACD>signal，前一时刻MACD<=signal
                    if macd > signal and prev_macd <= prev_signal:
                        macd_stocks.append(stock_code)
                else:
                    if macd > signal:
                        macd_stocks.append(stock_code)
                        
            except Exception:
                continue
                
        return macd_stocks
    
    def get_recommendations(self, top_n: int = 10) -> pd.DataFrame:
        """
        综合打分推荐股票
        
        Args:
            top_n: 返回前N只股票，默认10
            
        Returns:
            包含股票代码、得分、推荐理由的DataFrame
            列: stock_code, total_score, trend_score, momentum_score, 
                volume_score, volatility_score, reason
        """
        if not self.results:
            self.calc_factor_scores()
        
        if not self.results:
            return pd.DataFrame(columns=[
                'stock_code', 'total_score', 'trend_score', 
                'momentum_score', 'volume_score', 'volatility_score', 'reason'
            ])
        
        # 转换为DataFrame
        df = pd.DataFrame([
            {'stock_code': k, **v} for k, v in self.results.items()
        ])
        
        # 按总分排序
        df = df.sort_values('total_score', ascending=False).head(top_n)
        
        # 生成推荐理由
        def generate_reason(row):
            reasons = []
            
            # 趋势
            if row['trend_score'] >= 0.7:
                reasons.append('多头排列')
            elif row['trend_score'] >= 0.5:
                reasons.append('短期均线向上')
            
            # 动量
            if row['momentum_score'] >= 0.7:
                reasons.append('动量强劲')
            elif row['momentum_score'] >= 0.5:
                reasons.append('动量温和')
            
            # 量价
            if row['volume_score'] >= 0.7:
                reasons.append('量价配合')
            elif row['volume_score'] >= 0.5:
                reasons.append('成交量正常')
            
            # 波动
            if row['volatility_score'] >= 0.7:
                reasons.append('波动收窄')
            
            return '; '.join(reasons) if reasons else '综合评分'
        
        df['reason'] = df.apply(generate_reason, axis=1)
        
        return df.reset_index(drop=True)


def create_sample_data() -> Dict[str, pd.DataFrame]:
    """
    创建示例股票数据用于测试
    
    Returns:
        模拟的股票数据字典
    """
    import random
    
    stocks = ['000001', '000002', '600000', '600016', '600036', 
              '601318', '601398', '000858', '600519', '300750']
    
    data_dict = {}
    
    for stock in stocks:
        # 生成60天的模拟数据
        dates = pd.date_range(end=pd.Timestamp.now(), periods=60, freq='D')
        
        # 随机初始价格
        base_price = random.uniform(10, 200)
        
        # 生成价格序列 (带趋势)
        trend = np.linspace(0, random.uniform(-0.1, 0.2), 60)
        noise = np.random.normal(0, 0.02, 60)
        prices = base_price * (1 + trend + noise)
        
        # 生成OHLC数据
        df = pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.uniform(-0.01, 0.01, 60)),
            'high': prices * (1 + np.random.uniform(0, 0.03, 60)),
            'low': prices * (1 + np.random.uniform(-0.03, 0, 60)),
            'close': prices,
            'volume': np.random.uniform(1e6, 1e8, 60)
        })
        
        data_dict[stock] = df
        
    return data_dict


if __name__ == '__main__':
    # 测试示例
    print("=== 多因子选股模型测试 ===\n")
    
    # 创建示例数据
    df_dict = create_sample_data()
    
    # 初始化选股器
    screener = StockScreener(df_dict)
    
    # 计算因子得分
    print("1. 计算因子得分...")
    scores = screener.calc_factor_scores()
    print(f"   完成 {len(scores)} 只股票评分\n")
    
    # 筛选多头排列
    print("2. 多头排列筛选...")
    trend_stocks = screener.screen_by_trend()
    print(f"   多头排列股票: {trend_stocks}\n")
    
    # RSI筛选
    print("3. RSI筛选...")
    rsi_results = screener.screen_by_rsi()
    oversold = [k for k, v in rsi_results.items() if v == 'oversold']
    print(f"   超卖股票: {oversold}\n")
    
    # MACD金叉筛选
    print("4. MACD金叉筛选...")
    macd_stocks = screener.screen_by_macd()
    print(f"   MACD金叉股票: {macd_stocks}\n")
    
    # 获取推荐
    print("5. 综合推荐 Top 10...")
    recommendations = screener.get_recommendations(top_n=10)
    print(recommendations.to_string(index=False))

# -*- coding: utf-8 -*-
"""
===================================
量化因子计算模块
===================================
计算各类技术指标和量化因子
"""
import pandas as pd
import numpy as np
from typing import List, Optional


def calc_ma(df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
    """
    计算移动平均线 MA
    
    Args:
        df: 包含 close 列的 DataFrame
        periods: 周期列表，默认 [5, 10, 20, 60, 120, 250]
    
    Returns:
        添加了 MA 列的 DataFrame
    """
    df = df.copy()
    if periods is None:
        periods = [5, 10, 20, 60, 120, 250]
    
    for period in periods:
        df[f'MA{period}'] = df['close'].rolling(window=period).mean()
    
    return df


def calc_ema(df: pd.DataFrame, period: int = 12) -> pd.DataFrame:
    """计算指数移动平均线 EMA"""
    df = df.copy()
    df[f'EMA{period}'] = df['close'].ewm(span=period, adjust=False).mean()
    return df


def calc_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    计算 MACD 指标
    
    MACD = EMA(12) - EMA(26)
    Signal = EMA(MACD, 9)
    Histogram = MACD - Signal
    """
    df = df.copy()
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    
    df['MACD'] = ema_fast - ema_slow
    df['MACD_SIGNAL'] = df['MACD'].ewm(span=signal, adjust=False).mean()
    df['MACD_HIST'] = df['MACD'] - df['MACD_SIGNAL']
    
    # MACD 金叉死叉信号
    df['MACD_CROSS'] = 0
    df.loc[(df['MACD'] > df['MACD_SIGNAL']) & (df['MACD'].shift(1) <= df['MACD_SIGNAL'].shift(1)), 'MACD_CROSS'] = 1  # 金叉
    df.loc[(df['MACD'] < df['MACD_SIGNAL']) & (df['MACD'].shift(1) >= df['MACD_SIGNAL'].shift(1)), 'MACD_CROSS'] = -1  # 死叉
    
    return df


def calc_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    计算相对强弱指标 RSI
    
    RSI = 100 - 100 / (1 + RS)
    RS = 平均上涨幅度 / 平均下跌幅度
    """
    df = df.copy()
    delta = df['close'].diff()
    
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # RSI 超买超卖信号
    df['RSI_SIGNAL'] = 0
    df.loc[df['RSI'] < 30, 'RSI_SIGNAL'] = 1   # 超卖
    df.loc[df['RSI'] > 70, 'RSI_SIGNAL'] = -1  # 超买
    
    return df


def calc_kdj(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
    """
    计算 KDJ 随机指标
    
    RSV = (Close - LowN) / (HighN - LowN) * 100
    K = SMA(RSV, M1)
    D = SMA(K, M2)
    J = 3K - 2D
    """
    df = df.copy()
    
    low_n = df['low'].rolling(window=n).min()
    high_n = df['high'].rolling(window=n).max()
    
    rsv = (df['close'] - low_n) / (high_n - low_n) * 100
    rsv = rsv.fillna(50)
    
    df['KDJ_K'] = rsv.ewm(alpha=1/m1, adjust=False).mean()
    df['KDJ_D'] = df['KDJ_K'].ewm(alpha=1/m2, adjust=False).mean()
    df['KDJ_J'] = 3 * df['KDJ_K'] - 2 * df['KDJ_D']
    
    # KDJ 金叉死叉
    df['KDJ_CROSS'] = 0
    df.loc[(df['KDJ_K'] > df['KDJ_D']) & (df['KDJ_K'].shift(1) <= df['KDJ_D'].shift(1)), 'KDJ_CROSS'] = 1
    df.loc[(df['KDJ_K'] < df['KDJ_D']) & (df['KDJ_K'].shift(1) >= df['KDJ_D'].shift(1)), 'KDJ_CROSS'] = -1
    
    return df


def calc_boll(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
    """
    计算布林带 BOLL
    
    MID = MA(Close, N)
    UPPER = MID + StdDev * N
    LOWER = MID - StdDev * N
    """
    df = df.copy()
    
    df['BOLL_MID'] = df['close'].rolling(window=period).mean()
    rolling_std = df['close'].rolling(window=period).std()
    
    df['BOLL_UPPER'] = df['BOLL_MID'] + std_dev * rolling_std
    df['BOLL_LOWER'] = df['BOLL_MID'] - std_dev * rolling_std
    df['BOLL_WIDTH'] = (df['BOLL_UPPER'] - df['BOLL_LOWER']) / df['BOLL_MID'] * 100
    
    # 布林带位置
    df['BOLL_POS'] = (df['close'] - df['BOLL_LOWER']) / (df['BOLL_UPPER'] - df['BOLL_LOWER'])
    
    return df


def calc_bias(df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
    """
    计算乖离率 BIAS
    
    BIAS = (Close - MA) / MA * 100
    """
    df = df.copy()
    if periods is None:
        periods = [5, 10, 20]
    
    for period in periods:
        ma = df['close'].rolling(window=period).mean()
        df[f'BIAS{period}'] = (df['close'] - ma) / ma * 100
    
    return df


def calc_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    计算平均真实波幅 ATR
    
    TR = max(High-Low, abs(High-PrevClose), abs(Low-PrevClose))
    ATR = MA(TR, N)
    """
    df = df.copy()
    
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift(1))
    low_close = abs(df['low'] - df['close'].shift(1))
    
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=period).mean()
    df['ATR_PCT'] = df['ATR'] / df['close'] * 100  # ATR占价格百分比
    
    return df


def calc_obv(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算能量潮 OBV
    
    OBV = 前日OBV + 今日成交量 * 方向
    方向: 上涨为正，下跌为负
    """
    df = df.copy()
    
    direction = np.where(df['close'] > df['close'].shift(1), 1,
                        np.where(df['close'] < df['close'].shift(1), -1, 0))
    df['OBV'] = (df['volume'] * direction).cumsum()
    df['OBV_MA'] = df['OBV'].rolling(window=20).mean()
    
    return df


def calc_volume_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算量比
    
    量比 = 今日成交量 / 过去5日平均成交量
    """
    df = df.copy()
    df['VOL_RATIO'] = df['volume'] / df['volume'].rolling(window=5).mean()
    return df


def calc_cci(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """
    计算 CCI 顺势指标
    
    CCI = (TP - MA) / (0.015 * MD)
    TP = (High + Low + Close) / 3
    """
    df = df.copy()
    
    tp = (df['high'] + df['low'] + df['close']) / 3
    ma = tp.rolling(window=period).mean()
    md = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
    
    df['CCI'] = (tp - ma) / (0.015 * md)
    
    return df


def calc_williams_r(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    计算威廉指标 Williams %R
    
    %R = (HighN - Close) / (HighN - LowN) * (-100)
    """
    df = df.copy()
    
    high_n = df['high'].rolling(window=period).max()
    low_n = df['low'].rolling(window=period).min()
    
    df['WILLR'] = (high_n - df['close']) / (high_n - low_n) * (-100)
    
    return df


def calc_all_factors(df: pd.DataFrame) -> pd.DataFrame:
    """
    一次性计算所有因子
    
    Args:
        df: 包含 open, high, low, close, volume 的 DataFrame
    
    Returns:
        添加了所有因子列的 DataFrame
    """
    df = df.copy()
    
    # 趋势因子
    df = calc_ma(df)
    df = calc_ema(df, period=12)
    df = calc_ema(df, period=26)
    
    # 动量因子
    df = calc_macd(df)
    df = calc_rsi(df)
    df = calc_kdj(df)
    df = calc_cci(df)
    df = calc_williams_r(df)
    
    # 波动因子
    df = calc_boll(df)
    df = calc_atr(df)
    
    # 量价因子
    df = calc_obv(df)
    df = calc_volume_ratio(df)
    
    # 乖离率
    df = calc_bias(df)
    
    # 涨跌幅
    df['pct_change'] = df['close'].pct_change() * 100
    
    return df


# 导出所有函数
__all__ = [
    'calc_ma',
    'calc_ema', 
    'calc_macd',
    'calc_rsi',
    'calc_kdj',
    'calc_boll',
    'calc_bias',
    'calc_atr',
    'calc_obv',
    'calc_volume_ratio',
    'calc_cci',
    'calc_williams_r',
    'calc_all_factors'
]

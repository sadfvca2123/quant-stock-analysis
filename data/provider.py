# -*- coding: utf-8 -*-
"""
===================================
数据获取模块
===================================
支持多数据源: AkShare, Tushare
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional
from functools import lru_cache
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataProvider:
    """
    数据提供者 - 支持多数据源
    
    数据源优先级:
    1. akshare (免费, 无需注册)
    2. tushare (需要token)
    """
    
    def __init__(self, source: str = "akshare", tushare_token: str = None):
        """
        初始化数据提供者
        
        Args:
            source: 数据源 ("akshare" 或 "tushare")
            tushare_token: Tushare API Token
        """
        self.source = source
        self.tushare_token = tushare_token
        
        # 初始化 akshare
        if source == "akshare":
            try:
                import akshare as ak
                self.ak = ak
                logger.info("AkShare 初始化成功")
            except ImportError:
                raise ImportError("请安装 akshare: pip install akshare")
        
        # 初始化 tushare
        elif source == "tushare":
            try:
                import tushare as ts
                self.ts = ts
                if tushare_token:
                    ts.set_token(tushare_token)
                    self.pro = ts.pro_api()
                logger.info("Tushare 初始化成功")
            except ImportError:
                raise ImportError("请安装 tushare: pip install tushare")
    
    def _retry(self, func, max_retries: int = 3, delay: float = 1.0, *args, **kwargs):
        """重试机制"""
        last_error = None
        for i in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning(f"第 {i+1} 次尝试失败: {e}")
                time.sleep(delay * (i + 1))
        raise last_error
    
    def get_stock_history(self, code: str, days: int = 250) -> Optional[pd.DataFrame]:
        """
        获取股票历史K线数据
        
        Args:
            code: 股票代码 (如 "000001")
            days: 获取天数
        
        Returns:
            包含 open, high, low, close, volume 的 DataFrame
        """
        try:
            if self.source == "akshare":
                return self._get_stock_history_akshare(code, days)
            else:
                return self._get_stock_history_tushare(code, days)
        except Exception as e:
            logger.error(f"获取 {code} 历史数据失败: {e}")
            return None
    
    def _get_stock_history_akshare(self, code: str, days: int) -> pd.DataFrame:
        """AkShare 获取历史数据"""
        def _fetch():
            # 判断市场
            if code.startswith(('6', '5', '9')):
                symbol = f"sh{code}"
            else:
                symbol = f"sz{code}"
            
            # 获取日K线
            df = self.ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                adjust="qfq"  # 前复权
            )
            
            if df is None or len(df) == 0:
                return None
            
            # 标准化列名
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'amount',
                '涨跌幅': 'pct_change'
            })
            
            # 确保必要列存在
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in df.columns:
                    logger.error(f"缺少列: {col}")
                    return None
            
            # 取最近N天
            df = df.tail(days).reset_index(drop=True)
            
            return df
        
        return self._retry(_fetch)
    
    def _get_stock_history_tushare(self, code: str, days: int) -> pd.DataFrame:
        """Tushare 获取历史数据"""
        def _fetch():
            # 转换代码格式
            if code.startswith('6'):
                ts_code = f"{code}.SH"
            else:
                ts_code = f"{code}.SZ"
            
            # 计算日期范围
            end_date = pd.Timestamp.now().strftime('%Y%m%d')
            start_date = (pd.Timestamp.now() - pd.Timedelta(days=days*1.5)).strftime('%Y%m%d')
            
            df = self.pro.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or len(df) == 0:
                return None
            
            # 按日期排序
            df = df.sort_values('trade_date').reset_index(drop=True)
            
            # 标准化列名
            df = df.rename(columns={
                'trade_date': 'date',
                'vol': 'volume'
            })
            
            # 取最近N天
            df = df.tail(days).reset_index(drop=True)
            
            return df
        
        return self._retry(_fetch)
    
    def get_stock_realtime(self, codes: List[str]) -> Dict[str, dict]:
        """
        获取实时行情
        
        Args:
            codes: 股票代码列表
        
        Returns:
            {code: {close, pct_change, volume, amount, ...}}
        """
        result = {}
        
        if self.source == "akshare":
            try:
                df = self.ak.stock_zh_a_spot_em()
                
                for code in codes:
                    row = df[df['代码'] == code]
                    if len(row) > 0:
                        result[code] = {
                            'name': row['名称'].values[0],
                            'close': float(row['最新价'].values[0]),
                            'pct_change': float(row['涨跌幅'].values[0]),
                            'volume': float(row['成交量'].values[0]),
                            'amount': float(row['成交额'].values[0]),
                            'high': float(row['最高'].values[0]),
                            'low': float(row['最低'].values[0]),
                            'open': float(row['今开'].values[0]),
                        }
            except Exception as e:
                logger.error(f"获取实时行情失败: {e}")
        
        return result
    
    def get_stock_info(self, code: str) -> dict:
        """获取股票基本信息"""
        info = {'code': code, 'name': code}
        
        try:
            if self.source == "akshare":
                df = self.ak.stock_individual_info_em(symbol=code)
                if df is not None:
                    for _, row in df.iterrows():
                        info[row['item']] = row['value']
        except Exception as e:
            logger.warning(f"获取 {code} 信息失败: {e}")
        
        return info
    
    def get_index_data(self, index_code: str = "000001") -> Optional[pd.DataFrame]:
        """
        获取指数数据
        
        Args:
            index_code: 指数代码 (默认上证指数)
        """
        try:
            if self.source == "akshare":
                # 上证指数
                if index_code == "000001":
                    df = self.ak.stock_zh_index_daily(symbol="sh000001")
                # 深证成指
                elif index_code == "399001":
                    df = self.ak.stock_zh_index_daily(symbol="sz399001")
                # 创业板指
                elif index_code == "399006":
                    df = self.ak.stock_zh_index_daily(symbol="sz399006")
                else:
                    df = self.ak.stock_zh_index_daily(symbol=f"sh{index_code}")
                
                return df.tail(250)
        except Exception as e:
            logger.error(f"获取指数数据失败: {e}")
            return None
    
    def get_market_overview(self) -> dict:
        """获取市场概览"""
        overview = {
            'up_count': 0,
            'down_count': 0,
            'limit_up': 0,
            'limit_down': 0,
            'north_flow': 0,
            'hot_sectors': []
        }
        
        try:
            if self.source == "akshare":
                # 涨跌统计
                df = self.ak.stock_zh_a_spot_em()
                overview['up_count'] = len(df[df['涨跌幅'] > 0])
                overview['down_count'] = len(df[df['涨跌幅'] < 0])
                overview['limit_up'] = len(df[df['涨跌幅'] >= 9.9])
                overview['limit_down'] = len(df[df['涨跌幅'] <= -9.9])
                
                # 北向资金
                try:
                    north = self.ak.stock_hsgt_north_net_flow_in_em()
                    if len(north) > 0:
                        overview['north_flow'] = float(north.iloc[-1]['当日净流入'])
                except:
                    pass
                
                # 热门板块
                try:
                    sectors = self.ak.stock_board_concept_name_em()
                    hot = sectors.head(5)['板块名称'].tolist()
                    overview['hot_sectors'] = hot
                except:
                    pass
        
        except Exception as e:
            logger.error(f"获取市场概览失败: {e}")
        
        return overview


__all__ = ['DataProvider']

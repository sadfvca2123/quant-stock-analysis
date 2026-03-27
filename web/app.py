# -*- coding: utf-8 -*-
"""
===================================
FastAPI Web 服务
===================================
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import config
from data import DataProvider
from quant import StockScreener
from ai import AIAnalyzer

app = FastAPI(title="智能量化选股系统", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StockRequest(BaseModel):
    codes: List[str]
    top_n: Optional[int] = 10


class StockAnalysis(BaseModel):
    code: str
    name: str
    close: float
    pct_change: float
    score: float
    advice: str
    factors: dict


@app.get("/")
async def root():
    return {"message": "智能量化选股系统 API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/stocks/{code}")
async def get_stock(code: str):
    """获取单只股票数据"""
    provider = DataProvider(source="akshare")
    df = provider.get_stock_history(code, days=60)
    if df is None:
        raise HTTPException(status_code=404, detail="Stock not found")
    return {
        "code": code,
        "data": df.tail(30).to_dict(orient="records")
    }


@app.post("/api/analyze")
async def analyze_stocks(req: StockRequest):
    """分析多只股票"""
    provider = DataProvider(source="akshare")
    screener_data = {}
    
    for code in req.codes:
        df = provider.get_stock_history(code, days=250)
        if df is not None:
            screener_data[code] = df
    
    if not screener_data:
        raise HTTPException(status_code=400, detail="No valid data")
    
    screener = StockScreener(screener_data)
    scores = screener.calc_factor_scores()
    recommendations = screener.get_recommendations(top_n=req.top_n)
    
    return {
        "total": len(recommendations),
        "data": recommendations.to_dict(orient="records")
    }


@app.get("/api/market")
async def market_overview():
    """市场概览"""
    provider = DataProvider(source="akshare")
    overview = provider.get_market_overview()
    return overview


@app.post("/api/ai/analyze")
async def ai_analyze(code: str):
    """AI 深度分析"""
    provider = DataProvider(source="akshare")
    df = provider.get_stock_history(code, days=250)
    if df is None:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    latest = df.iloc[-1]
    screener = StockScreener({code: df})
    scores = screener.calc_factor_scores()
    
    stock_data = {
        'name': code,
        'close': latest.get('close', 0),
        'pct_change': latest.get('pct_change', 0),
        'MA5': latest.get('MA5', 0),
        'MA10': latest.get('MA10', 0),
        'MA20': latest.get('MA20', 0),
        'RSI': latest.get('RSI', 0),
        'MACD': latest.get('MACD', 0),
    }
    
    analyzer = AIAnalyzer()
    analysis = analyzer.analyze_stock(code, stock_data)
    
    return {
        "code": code,
        "analysis": analysis
    }


def run_server(host: str = None, port: int = None):
    host = host or config.WEB_HOST
    port = port or config.WEB_PORT
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
# -*- coding: utf-8 -*-
"""
===================================
企业微信推送模块
===================================
"""
import httpx
import config


class WeChatNotifier:
    """企业微信消息推送"""
    
    def __init__(self):
        self.webhook_url = config.WECHAT_WEBHOOK_URL
    
    def send(self, content: str, msg_type: str = "markdown") -> bool:
        """发送消息到企业微信"""
        if not self.webhook_url:
            print("未配置企业微信 Webhook")
            return False
        
        if msg_type == "markdown":
            payload = {
                "msgtype": "markdown",
                "markdown": {"content": content}
            }
        else:
            payload = {
                "msgtype": "text",
                "text": {"content": content}
            }
        
        try:
            resp = httpx.post(self.webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            return resp.json().get("errcode", -1) == 0
        except Exception as e:
            print(f"发送失败: {e}")
            return False
    
    def send_analysis(self, results: list) -> bool:
        """发送分析结果"""
        lines = ["## 📊 智能量化分析报告\n"]
        
        for r in results:
            emoji = r.get("emoji", "⚪")
            lines.append(f"**{emoji} {r['name']}({r['code']})**")
            lines.append(f"> 价格: {r['close']:.2f} | 涨跌: {r['pct_change']:.2f}%")
            lines.append(f"> 建议: {r['advice']} | 得分: {r['score']:.1f}")
            lines.append("")
        
        return self.send("\n".join(lines))
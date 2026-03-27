$gh = "C:\Program Files\GitHub CLI\gh.exe"

# 复用之前的 Secrets
& $gh secret set OPENAI_API_KEY --repo sadfvca2123/quant-stock-analysis --body "sk-0677ffcfc9924601860051bccc2f5aa9" 2>&1
& $gh secret set OPENAI_BASE_URL --repo sadfvca2123/quant-stock-analysis --body "https://api.deepseek.com/v1" 2>&1
& $gh secret set OPENAI_MODEL --repo sadfvca2123/quant-stock-analysis --body "deepseek-chat" 2>&1
& $gh secret set STOCK_LIST --repo sadfvca2123/quant-stock-analysis --body "000620,000657,002445,600032,002490,002498,002969" 2>&1
& $gh secret set WECHAT_WEBHOOK_URL --repo sadfvca2123/quant-stock-analysis --body "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=a2106cae-074c-4585-a52d-5b9b3a09822e" 2>&1

Write-Host "Secrets configured!"

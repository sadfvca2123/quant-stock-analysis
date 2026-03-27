Set-Location "C:\Users\Administrator\.qclaw\workspace\quant-stock-analysis"
git init
git add .
git commit -m "feat: smart quant stock analysis v1.0"
git branch -M main
git remote add origin https://github.com/sadfvca2123/quant-stock-analysis.git
git push -u origin main --force
Write-Host "Push completed!"

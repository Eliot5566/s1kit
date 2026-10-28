# s1kit

**用你自己的資料，測試、校準與路由 System One 決策模型。**

Jev、Laya、kev，以及 llama.cpp、Ollama 上的決策模型，都使用同一個 `/v1/systemone` API，
回傳附帶信心值的結構化答案。換模型只要改一行，但該不該換、換了會不會更差，需要數據回答。
s1kit 處理你第一天就會遇到的四個問題：

1. **哪個模型在我的資料上最準？** `s1kit test` 用同一份測試案例同時比較所有模型。
2. **信心多少才能相信？** `s1kit calibrate` 依你要的準確率，替每個問題算出信心門檻。
3. **低於門檻怎麼辦？** `s1kit.Router` 先問最便宜的模型，信心不足才升級到更強的模型。
4. **這次修改有沒有變差？** GitHub Action 會在準確率下降時讓 CI 失敗。

## 快速開始

```bash
pip install s1kit
s1kit init      # 產生 s1kit.yaml：10 張客服單、3 個問題
s1kit test
s1kit calibrate results.jsonl --target 0.95
```

範例不需要網路與 API key：內建的 `keyword` 是用字詞重疊判斷的基準模型，
真正的模型至少要贏過它。在 `s1kit.yaml` 取消註解一個真的模型（例如 laya-serve，
預設在 `http://localhost:8000`），就能並排比較。

- `s1kit test -j 8`：同時送出 8 個請求。
- HTTP 模型遇到 429、5xx 或連線中斷會自動重試；伺服器沒開會立刻提示，不會卡住。
- `--fail-under 0.9`：準確率低於 90% 時回傳失敗，適合放進 CI。

## 放進 GitHub Actions

```yaml
- uses: Eliot5566/s1kit@v0.2.0
  with:
    suite: s1kit.yaml
    fail-under: "0.9"
```

結果表格會顯示在 job summary。測試案例格式、Router 用法與完整指令請見[英文 README](README.md)。

> 狀態：alpha（0.2.0），1.0 之前 API 可能變動。歡迎從標記
> [good first issue](https://github.com/Eliot5566/s1kit/labels/good%20first%20issue) 的議題開始貢獻。

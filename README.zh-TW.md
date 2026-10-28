# s1kit

**用你自己的資料，測試、校準與路由 System One 決策模型。**

Jev、Laya、kev，以及 llama.cpp、Ollama 上的決策模型，都使用同一個 `/v1/systemone` API，
回傳附帶信心值的結構化答案。s1kit 處理你第一天就會遇到的三個問題：

1. **哪個模型在我的資料上最準？** `s1kit test` 用同一份測試案例同時比較所有模型。
2. **信心多少才能相信？** `s1kit calibrate` 依你要的準確率，替每個問題算出信心門檻。
3. **低於門檻怎麼辦？** `s1kit.Router` 先問最便宜的模型，信心不足才升級到更強的模型。

範例不需要網路與 API key：內建的 `keyword` 是用字詞重疊判斷的基準模型，
真正的模型至少要贏過它。

```bash
pip install s1kit
s1kit test examples/support-tickets.yaml
s1kit calibrate results.jsonl --target 0.95
```

測試案例格式、Router 用法與指令說明請見[英文 README](README.md)。

> 狀態：alpha（0.1.0），1.0 之前 API 可能變動。

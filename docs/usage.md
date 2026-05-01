# 使用说明

## 1. 安装依赖
```bash
pip install -r requirements.txt
```

## 2. 启动项目
```bash
streamlit run app.py
```

## 3. 运行测试
```bash
python -m pytest
```

## 4. 交互流程
1. 在左侧选择政策场景
2. 设置 Agent 数量、模拟轮数、信息干预方式和随机种子
3. 点击“运行模拟”
4. 查看摘要指标、图表、代表性发言和治理分析报告

## 5. 参考语料说明
- 项目运行默认不依赖大文件语料
- 若仓库中保留 `sample_reference.jsonl`，页面可展示轻量参考语料概览
- `train.jsonl` 与 `validation.jsonl` 不建议随仓库上传

## 6. API Key 说明
本项目当前版本默认使用规则模型和模板报告，不依赖真实 API Key；未来可扩展 LLM 生成代表性发言和分析报告。


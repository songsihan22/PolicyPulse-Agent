# PolicyPulse-Agent

A multi-agent simulator for public opinion dynamics in governance scenarios.

<p align="center">
  <img src="./assets/policypulse_simulation_overview_infographic.png" alt="PolicyPulse Overview" width="100%">
</p>

<p align="center">
  <em>Multi-agent public policy simulation workflow: scenarios, heterogeneous agents, attitude dynamics, and governance insights.</em>
</p>

## Overview
PolicyPulse-Agent 是一个面向公共政策与 AI 治理场景的轻量级多智能体模拟项目。它通过可解释的规则模型，展示不同类型公众在政策议题、信息干预和社会互动共同作用下的态度演化过程。当前版本提供可运行的 Streamlit 页面、基础测试、统一指标模块和自动生成的分析文本。

## Why This Project
生成式 AI 正在进入高校教学、内容平台、公共数据开放和金融风控等场景。围绕这些议题，现实中的争论不只关于技术效果，还涉及公众接受度、制度信任、风险感知、权益保护以及政策沟通方式。

本项目并不试图预测真实舆情，而是搭建一个解释性原型，用于帮助观察：
- 不同公众画像是否会对同一政策议题产生不同反应
- 正式解释、专家说明或负面冲击会怎样改变群体态度
- 群体平均态度变化的同时，是否伴随分化加剧或缓和

## Features
- 内置多个治理场景：生成式 AI 进入高校课堂、生成式 AI 内容监管、城市公共摄像头治理、金融 AI 风控透明度、公共数据开放治理
- 内置六类异质性公众画像：技术乐观型、风险敏感型、制度信任型、权益保护型、功利效率型、中立观望型
- 支持多种信息干预方式：官方政策解释、专家理性说明、负面新闻冲击、社交媒体情绪传播、平衡型公共讨论
- 提供多轮社会互动与态度更新
- 提供图表、指标卡、代表性发言和治理分析报告
- 提供基础测试与 GitHub Actions 测试流程

## How It Works
每个 Agent 都有初始态度、制度信任、风险敏感度、收益敏感度、从众倾向、开放性和表达强度等属性。每轮模拟中，态度更新遵循可解释框架：

`新态度 = 原态度 + 政策信息影响 + 社交互动影响 + 随机扰动`

为避免所有个体迅速收敛到极端位置，更新逻辑中加入了：
- 画像差异化响应
- 向初始画像的有限回拉
- 单轮变化上限
- 随态度绝对值增强的阻尼机制

态度标签规则：
- `attitude > 0.2`：支持
- `attitude < -0.2`：反对
- 其他：中立

## Metrics
项目当前集中计算以下指标：
- 支持率：最终轮支持者比例
- 中立率：最终轮中立者比例
- 反对率：最终轮反对者比例
- 平均态度：最终轮 `attitude` 均值
- 个体分化程度：最终轮 `attitude` 标准差
- 群体分化程度：不同 persona 平均态度最大值与最小值之差
- 沟通效果：最终平均态度与初始平均态度之差
- 支持率变化：最终支持率与初始支持率之差

页面会展示其中的关键摘要指标，包括支持率、中立率、反对率、群体分化程度和沟通效果变化。

## Quick Start
Install dependencies:

```bash
pip install -r requirements.txt
```

Run the Streamlit app:

```bash
streamlit run app.py
```

Run tests:

```bash
python -m pytest
```

## Example Scenario
推荐演示参数：
- 场景：生成式 AI 进入高校课堂
- Agent 数量：60
- 模拟轮数：12
- 信息干预：平衡型公共讨论
- 随机种子：42

在这个设置下，通常可以看到技术乐观型和功利效率型更容易转向支持，而风险敏感型和权益保护型保持相对谨慎，中立观望型则更容易受到群体互动影响。

## Project Structure
```text
PolicyPulse-Agent/
├── .github/workflows/tests.yml
├── assets/
├── docs/
│   ├── architecture.md
│   ├── model_assumptions.md
│   └── usage.md
├── examples/
│   ├── demo_case_ai_governance.md
│   └── demo_case_education.md
├── src/
│   ├── charts.py
│   ├── metrics.py
│   ├── models.py
│   ├── report.py
│   ├── scenarios.py
│   ├── simulator.py
│   └── utils.py
├── tests/
│   ├── test_metrics.py
│   ├── test_models.py
│   └── test_simulator.py
├── AGENTS.md
├── LICENSE
├── README.md
├── app.py
├── requirements.txt
└── sample_reference.jsonl
```

## Tests
当前测试覆盖以下基础内容：
- Pydantic 模型能正常创建
- 非法场景名会触发校验错误
- 模拟结果非空且行数正确
- 固定随机种子下模拟结果可复现
- 支持 / 中立 / 反对比例会加总为 1
- 指标模块能正确返回最终轮和沟通效果指标

运行命令：

```bash
python -m pytest
```

## Limitations
- 本项目是解释性、探索性的模拟原型，不构成对真实社会行为或政策结果的预测
- Agent 参数和更新规则属于研究化抽象，不代表真实人口结构
- 社会互动网络经过简化，未引入复杂网络拓扑和真实平台传播机制
- 报告与代表性发言为规则生成结果，更适合作为展示型输出，而不是正式政策评估文本

## Roadmap
- 补充更多政策场景与更细粒度公众画像
- 丰富图表和指标解释
- 根据真实问卷或公开研究结果对参数做更细致校准
- 在 `assets/` 中补充真实页面截图，完善仓库展示材料

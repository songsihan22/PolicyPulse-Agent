# AGENTS

## 项目定位
PolicyPulse-Agent 是一个面向公共治理场景的轻量级多智能体态度演化模拟原型，强调解释性、可视化与教学展示价值。

## 开发约定
- 使用 Python 3.11。
- 保持无数据库、无复杂后端框架的轻量结构。
- 核心逻辑集中在 `src/` 目录。
- 模拟更新规则应保持可解释，不引入黑箱式依赖。
- 所有对外文案默认使用中文，风格正式、克制。

## 常用命令
- 安装依赖：`pip install -r requirements.txt`
- 启动页面：`streamlit run app.py`
- 运行测试：`pytest`

## 模块说明
- `src/models.py`：Pydantic 数据模型
- `src/scenarios.py`：场景、干预方式、Agent 模板
- `src/simulator.py`：多智能体生成与态度更新逻辑
- `src/charts.py`：Plotly 图表
- `src/report.py`：代表性发言与治理分析报告
- `src/utils.py`：通用工具函数


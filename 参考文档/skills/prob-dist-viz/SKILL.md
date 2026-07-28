---
name: prob-dist-viz
description: 概率论与数理统计可视化与知识点 Skill。当用户给出概率分布相关输入（分布函数表达式、常见分布名称及参数、概率密度函数、口头描述、自定义公式等）并希望得到「标准分布描述 + 核心知识点 + 动态可视化动画」时使用。This skill should be used when users want to parse a probability distribution from any prompt format, output its key properties (mean, variance, characteristic function, applications), and generate an interactive HTML animation (PDF/PMF drawing, CDF demo, parameter sensitivity).
agent_created: true
---

# 概率分布可视化与知识点（prob-dist-viz）

将用户**多种格式**的概率分布输入，统一解析为标准分布描述，输出核心知识点，并生成
**自包含交互式 HTML 动画**（密度/质量曲线动态绘制、分布函数动态演示、参数滑块实时变形 + 可手动输入参数值；公式由 KaTeX 专业排版，含概率密度函数与分布函数）。

## 何时使用
触发场景（命中任一即启用本 Skill）：
- 用户给出「正态分布 N(0,1)」「泊松分布 λ=3」「Binomial(10,0.5)」「beta(2,3)」等名称+参数。
- 用户给出密度/分布函数表达式：`f(x)=λe^{-λx}`、`F(x)=1-e^{-λx}`。
- 用户口头描述：「描述独立随机事件发生间隔的分布」「单位时间内的稀有事件数」。
- 用户给出自定义公式或要求「画一下这个分布」「做个动画看看参数影响」。
- 用户要求讲解某分布的均值、方差、特征函数、典型应用等。

## 内置分布（精选常用集，约 15 种）
连续：normal、uniform、exponential、gamma、beta、chi_square、student_t、weibull、laplace、lognormal
离散：bernoulli、binomial、poisson、geometric、negative_binomial
（不在目录的分布会进入 `formula` 模式仅做可视化，知识点可走 IMA 知识库补充。）

## 三步工作流

### 第 1 步 · 解析标准化（Parse）
目标：把任意输入变成统一的「标准分布描述 JSON」。

1. 先用语义理解判断分布类型与参数（口头描述按语义匹配，如「独立事件间隔」→ exponential）。
2. 调用解析脚本生成并**校验**标准 JSON：
   ```bash
   python <skill>/scripts/parse_input.py --input "<用户原文>" --out dist.json
   ```
   脚本会自动：扫描别名/关键词识别类型 → 正则提取参数（支持 μ/σ/λ/α/β/ν/k/p/n 及 `N(0,1)`、`λ=2` 等写法）→ 失败则进入 `formula` 模式。
3. **复核** 输出的 JSON（`distribution_type`、`params`、`domain`、`mode`）。可用 `--type` / `--params-json` 显式覆盖解析结果。
   标准 JSON 结构示例：
   ```json
   {"distribution_type":"normal","display_name":"正态分布","is_discrete":false,
    "params":{"mu":0,"sigma":1},"domain":[-4,4],"mode":"catalog","raw_formula":null,"source_input":"N(0,1)"}
   ```

### 第 2 步 · 知识点输出（Knowledge）
- **2a（默认 · 本地知识库）**：按 `distribution_type` 在
  `<skill>/references/distributions_knowledge.md` 中定位对应 `## <type>` 小节，
  向用户输出：公式、均值、方差、特征函数、矩母函数、典型应用、关键性质、与其他分布关系。
  生成结果 HTML 的「④ 核心知识点」面板也会自动展示这些字段。
- **2b（按需 · IMA 知识库）**：当分布**不在目录内**，或用户要求「对照教材 / 核实 / 更详细」时，
  调用 IMA 知识库检索权威片段并融合进讲解，注明来源。两个知识库：
  - `7335578605455675` —「概率论」（含浙大第4版、陈希孺、茆诗松等 PDF 教材）
  - `7409962292609361` —「概率论与数理统计」（已解析富文本库）
  调用范式（从空 cursor 开始）：
  ```
  mcp__ima-mcp__search_knowledge(knowledge_base_id="<上述id>", query="<分布名> 均值 方差 特征函数")
  ```
  将检索到的教材片段作为权威佐证融入讲解，并标注「来源：IMA 知识库《xxx》」。

### 第 3 步 · 可视化生成（Visualize）
把第 1 步的 JSON 生成自包含 HTML 动画：
```bash
python <skill>/scripts/generate_visualization.py dist.json --out <分布名>.html
```
随后用 `present_files` 把生成的 HTML 呈现给用户（应用内可直接预览）。
动画包含三个面板：
- ① 密度/质量曲线动态绘制（连续描线、离散柱状，从左到右动画揭示）
- ② 分布函数 F(x)=P(X≤x) 动态演示（由对密度数值积分得到，扫过并填充面积）
- ③ 参数敏感性：交互滑块实时重绘；右侧数字输入框可手动键入参数值，滑块与输入框双向联动（已取消自动播放；初始参数取用户给出的取值）

## 输入形态速查
| 用户给的 | 示例 | 解析结果 |
|---|---|---|
| 名称+参数 | `正态分布 N(0,1)` | catalog: normal |
| 密度函数 | `f(x)=λe^{-λx}, x≥0` | formula 模式 |
| 分布函数 | `F(x)=1-e^{-λx}` | catalog: exponential（识别为指数 CDF） |
| 口头描述 | `描述独立随机事件发生间隔的分布` | catalog: exponential |
| 自定义公式 | `f(x)=x*exp(-x/2)` | formula 模式 |

## 目录资源
- `scripts/distributions_catalog.py` — 分布目录（参数/定义域/pdf 的 JS+Python 实现/结构化知识），单一数据源。
- `scripts/parse_input.py` — 多格式输入 → 标准 JSON。
- `scripts/generate_visualization.py` — 标准 JSON → 自包含 HTML 动画（注入 JS_HELPERS：gamma/lgamma/beta/comb）。
- `references/distributions_knowledge.md` — 各分布知识点详解（与 IMA 教材对齐）。

## 注意事项
- 解析若识别有误，直接用 `--type` / `--params-json` 覆盖后再生成，无需重跑语义判断。
- `formula` 模式只做函数曲线绘制，不保证是合法密度（需归一化）；知识点请走 2b（IMA）。
- 公式渲染使用 **KaTeX（CDN 引入）**：PDF 与 CDF 函数、均值/方差/特征函数/矩母函数均以专业排版呈现；
  若处于离线环境或 KaTeX 加载失败，会自动回退为纯文本显示。HTML 仍为单文件，便于分享到课件/文档。
- **参数初始值**：若用户在输入中已给出参数（如 `N(0,1)`、`λ=2`），图像初始参数即为该取值；
  当取值超出默认滑块范围时，滑块范围会自动扩展以包含该值。
- 显示名、参数、公式均来自 `distributions_catalog.py` 与 `references/distributions_knowledge.md`，二者保持一致即可。

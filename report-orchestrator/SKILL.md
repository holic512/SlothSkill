---
name: report-orchestrator
description: 基于当前项目目录自动生成实验报告、课程设计报告、数据库设计报告等 Markdown 文档，并在可能时将 PlantUML 渲染为图片、回填到 Markdown，再导出为 Word。适用于用户只给一句简短要求，希望自动分析目录、补全约束并直接产出最终报告的场景。
metadata:
  short-description: 自动编排报告生成与文档导出
---

# Report Orchestrator

这个 skill 用于把“手工整理提示词、生成 Markdown、手动转图片、再手动转 Word”的重复流程收敛成一次编排。

当用户只给出一句简短要求时，你要自行完成目录扫描、题目归纳、证据提取、模板选择、Markdown 生成、PlantUML 渲染、图片回填、可选 DOCX 导出与结果自检。输出目标是最终报告，而不是中间提示词。

## 触发意图

以下场景默认使用本 skill：

- 用户希望基于当前目录生成实验报告、课程设计报告、数据库设计报告、Linux 项目报告或项目管理类报告
- 用户强调“自动分析目录”“自动补全章节/图表/约束”“不想重复写提示词”
- 用户要的是最终 `.md` 报告，或进一步想得到可交付的 `.docx`

## 默认输入协议

用户通常只会给一句话，例如：

`请基于当前目录生成一份 Java 课程设计实验报告，要求 3500 字以上，并输出 Word。`

从这句话中尽量提取以下参数；缺失时按默认值执行：

- `report_type`：显式指定时优先；未指定则自动识别
- `report_name`：可选；未指定则按题目或项目名归一化
- `topic`：优先使用用户题目；未给时从目录名、任务书、提示词标题、文档标题归纳
- `min_words`：可选；未指定时沿用模板默认要求
- `keep_plantuml_source`：默认 `true`
- `try_export_docx`：默认 `true`
- `output_dir`：默认 `docx/<报告名>/`

Word 导出模板约定：

- 模板清单位于 [assets/docx-templates/manifest.json](assets/docx-templates/manifest.json)
- 用户未给出明确样式要求时，默认使用 `0-general.docx`
- 用户给出接近模板特征的排版条件时，优先匹配最接近的 Word 模板

## 执行流程

### 1. 解析用户输入

先从用户请求里提取报告类型、题目、字数要求、输出名和是否导出 Word。

如果题目没有明确给出，优先从这些位置归纳：

- 当前目录名称
- 任务书、课程要求、现有报告标题
- 旧提示词文件标题
- README 或说明文档标题

题目一旦归纳出来，后续“需求分析”优先围绕题目和业务目标展开。

### 2. 双源建模：题目驱动 + 代码校正

先建立“题目/任务目标模型”，用于这些章节：

- 开发背景
- 研究意义
- 用户需求
- 应用场景
- 需求分析
- 目标功能

再建立“目录/代码证据模型”，用于这些章节：

- 总体设计
- 详细设计
- 数据结构与数据库设计
- 编码实现
- 运行说明
- 测试验证

必须明确：

- 需求分析不能退化成代码功能解释
- 设计与实现不能脱离目录证据乱写
- 没有测试证据时，可以写“测试设计”或“验证方案”，不能伪装成已经真实执行过的结果

具体扫描点见 [references/inspection-checklist.md](references/inspection-checklist.md)。

### 3. 生成原始 Markdown 报告

先输出一份带 PlantUML 代码块的源码版 Markdown，作为后处理输入。

源码版要求：

- 文件路径为 `docx/<报告名>/report.source.md`
- 保留 PlantUML 代码块
- 保留图题、表题、正文引用
- 截图不足时继续使用“截图占位”
- 严格使用正确的 Markdown 标题层级

Markdown 标题层级映射必须固定：

- 章级标题使用 `#`
  - 例如：`# 第1章 需求分析`
  - 例如：`# 一、需求分析`
- 节级标题使用 `##`
  - 例如：`## 1.1 背景与目标`
  - 例如：`## （一）系统开发背景与意义`
- 小节标题使用 `###`
  - 例如：`### 1.1.1 用户角色`
  - 例如：`### 1. 功能模块划分`

禁止把“第1章/第一章/一、需求分析”这类章级标题写成 `##` 或 `###`。

文案表达要自然，不要出现这些句式：

- “根据当前仓库中的真实代码实现”
- “根据代码分析可知”
- “结合仓库内容可见”
- 任何明显的提示词腔、分析腔、AI 腔

### 4. 渲染 PlantUML 图片

使用 skill 自带的 `plantuml-1.2026.2.jar` 渲染 Markdown 中的每个 `plantuml` 代码块，输出到：

- `docx/<报告名>/images/plantuml-001.png`
- `docx/<报告名>/images/plantuml-002.png`

优先使用以下脚本：

- [scripts/render_plantuml.py](scripts/render_plantuml.py)

执行前必须先确认：

- 已安装 `java`
- 已安装 Graphviz，并且 `dot` 可执行
- PlantUML JAR 存在

如果缺少任一项，立即停止任务，并明确要求用户先安装依赖后再继续。

### 5. 回填 Markdown

将原始 PlantUML 代码块替换为 Markdown 图片引用，生成最终交付版：

- `docx/<报告名>/report.md`

优先使用以下脚本：

- [scripts/rewrite_markdown_with_images.py](scripts/rewrite_markdown_with_images.py)

回填时：

- 使用相对路径引用 `images/`
- 保留图题和正文引用
- 默认不在最终交付版中保留原始 PlantUML 代码块

如果任一 PlantUML 图渲染失败，立即停止任务，并返回具体错误原因。

### 6. 可选导出 DOCX

探测 `pandoc`；若存在，则将 `report.md` 导出为：

- `docx/<报告名>/<报告名>.docx`

优先使用以下脚本：

- [scripts/export_docx.py](scripts/export_docx.py)

导出前应先从 [assets/docx-templates/manifest.json](assets/docx-templates/manifest.json) 选择最匹配的参考模板。

执行前必须确认系统已安装 `pandoc`。

如果不存在 `pandoc`，立即停止任务，并明确要求用户先安装 `pandoc` 后再继续。

## 建议执行顺序

生成 Markdown 后，按以下顺序执行后处理：

1. 先将源码版写入 `docx/<报告名>/report.source.md`
2. 使用 `scripts/render_plantuml.py` 渲染图片
3. 使用 `scripts/rewrite_markdown_with_images.py` 回填为 `report.md`
4. 如需 Word，使用 `scripts/export_docx.py` 导出 `.docx`

如果想一次完成，可以使用：

- [scripts/postprocess_report.py](scripts/postprocess_report.py)

## 输出原则

- 需求分析优先围绕题目、背景、用户与目标，不直接复述代码功能
- 总体设计、实现、测试优先依据真实目录证据
- 对同目录旧提示词文件，只作为结构或风格参考，不原样拼接
- 所有产物统一放在 `docx/<报告名>/`
- Markdown 标题层级必须与章节层级一一对应，不能为了视觉效果随意降级

## 失败处理

- 未找到 `java`：立即停止，并提示安装 Java
- 未找到 Graphviz `dot`：立即停止，并提示安装 Graphviz
- 未找到 JAR：立即停止，并提示检查 skill 内置资源
- 未找到 `pandoc`：立即停止，并提示安装 pandoc
- PlantUML 某一图渲染失败：立即停止，并返回具体错误
- 输出目录已存在：允许覆盖同名中间产物，但不要删除目录外文件

## 内部对象约定

实现时可按以下概念组织信息：

- `ReportIntent`：题目、报告类型、字数要求、输出名、导出偏好
- `EvidenceModel`：目录结构、技术栈、数据库证据、界面素材、测试证据、旧模板参考
- `ReportDraft`：`report.source.md`、`report.md`、`images/`、`.docx`
- `PostProcessStatus`：`java_available`、`plantuml_jar_found`、`pandoc_available`、`rendered_image_count`、`docx_exported`

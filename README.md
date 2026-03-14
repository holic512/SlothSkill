# SlothSkill

这是一个用于沉淀和管理实用技能模块的仓库，目前主要包含两个能力方向：

- `report-orchestrator`：自动编排实验报告、课程设计报告、数据库设计报告等 Markdown 文档生成流程，并在条件满足时完成 PlantUML 渲染、图片回填和 Word 导出。
- `wechat_artical_publisher_skill-main`：用于将 Markdown 文章发送到微信公众号草稿箱或直接发布，支持图片上传、样式渲染、发布状态查询与已发布记录查询。
- `wechat-content-workshop`：面向微信生态的内容工坊，负责围绕主题生成公众号图文内容包、归档素材、接入 Pollinations 生图与文字保底图，并与发布器衔接。

## 目录说明

### 1. report-orchestrator

`report-orchestrator` 侧重于报告生成与交付自动化，适合需要基于项目目录快速整理课程实验、课程设计、数据库设计等文档的场景。

主要功能包括：

- 自动分析项目目录与已有材料
- 生成结构化 Markdown 报告
- 渲染 PlantUML 图并回填到文档
- 在环境满足时导出为 Word 文档

### 2. wechat_artical_publisher_skill-main

`wechat_artical_publisher_skill-main` 侧重于微信公众号文章发布，适合把本地 Markdown 内容整理后发送到草稿箱，或在确认后直接提交发布。

主要功能包括：

- 使用微信公众号官方 API 创建草稿并支持直接发布
- 自动上传 Markdown 中引用的本地图片
- 处理文章样式与基础排版
- 优化移动端显示兼容性
- 支持发布状态轮询与已发布历史查询

### 3. wechat-content-workshop

`wechat-content-workshop` 侧重于公众号内容生产与归档，不直接替代发布器，而是在发布器之前补足“选题 -> 文案 -> 配图 -> 归档 -> 微信成稿”的上层工作流。

主要功能包括：

- 根据主题生成标题、摘要、正文、封面文案、分享语、结尾引导语
- 固化低 AI 味写作规则，强化场景、细节、观点与段落节奏
- 以“单篇选题包”为单位归档文章、封面、配图、草稿、成稿和元数据
- 接入 Pollinations Key 鉴权生图、额度提示与文字保底图
- 导出兼容微信公众号发布器的最终 Markdown

## 来源与致谢

微信公众号发布模块 `wechat_artical_publisher_skill-main` 来源于开源项目：

- 上游仓库：[aximof/wechat_artical_publisher_skill](https://github.com/aximof/wechat_artical_publisher_skill)
- 上游许可证：MIT License

感谢原作者开放这个项目并采用 MIT 许可证进行授权，这为后续学习、扩展和二次开发提供了很大帮助。当前仓库在保留来源与许可证信息的前提下进行整理与后续功能调整，后续我也会继续按自己的使用需求迭代相关功能。

## 后续维护说明

这个仓库后续会继续围绕现有两个模块进行扩展，包括文档能力增强、功能微调以及更适合个人工作流的适配改造。为避免后续修改时丢失来源信息，README 中已保留微信公众号模块的来源与许可说明。

---
name: wechat-content-workshop
description: Generate WeChat-ready content packages with archiving, image planning, and publish-ready Markdown
---

# 微信生态内容工坊

这个技能用于围绕微信生态生成中文内容，默认面向微信公众号，重点输出“可发布、可归档、可复用”的标准内容包，而不是直接代替发布器完成微信 API 发布。

## 适用场景

- 用户只给一个主题，希望直接产出公众号图文内容
- 需要同时生成标题、摘要、正文、封面文案、配图建议、分享语、结尾引导语
- 需要降低 AI 味，强化真实细节、场景感和作者立场
- 需要把稿件和素材归档，后续继续发公众号、朋友圈、社群
- 需要和现有微信公众号发布器顺畅衔接

## 工作原则

1. 默认主渠道是“公众号”
2. 默认输出“单篇选题包”
3. 写作要优先保留温度、口语感、细节和立场
4. 图片流程必须先获取额度，再判断是否允许远程 AI 生图
5. 即使 AI 生图失败，也必须保住完整文案和配图建议
6. 最终输出必须兼容仓库中的微信发布器与标准内容包接口
7. 首次使用前先安装 `Pillow`，用于中文文字保底图渲染
8. 如果要启用 Pollinations AI 生图，优先通过 `.env` 配置 `POLLINATIONS_API_KEY`

## 依赖安装

首次使用前请先执行：

```bash
python3 -m pip install --user --break-system-packages Pillow
```

如果在虚拟环境中运行，可以改为：

```bash
python3 -m pip install -r wechat-content-workshop/requirements.txt
```

## 主要命令

### 生成内容包

```bash
python3 wechat-content-workshop/scripts/content_workshop.py generate --topic "主题"
```

推荐先准备 `.env`：

```bash
cp wechat-content-workshop/.env.example .env
```

### 导出公众号成稿

```bash
python3 wechat-content-workshop/scripts/content_workshop.py export-markdown --package-dir "/path/to/package"
```

### 给发布器准备标准内容包

```bash
python3 wechat-content-workshop/scripts/content_workshop.py publish-draft --package-dir "/path/to/package"
```

这个兼容命令现在只输出下一步建议，不再直接调用发布器。

推荐直接执行发布器：

```bash
python3 wechat_artical_publisher_skill-main/scripts/wechat_direct_api.py publish --mode draft --package-dir "/path/to/package"
```

## 输出要求

生成结果至少覆盖：

- 标题
- 正文
- 摘要
- 封面文案
- 配图建议
- 分享语
- 结尾引导语

同时归档：

- 主题
- 日期
- 类型
- 渠道
- 系列栏目
- 图片来源、生成策略、决策原因、失败原因与额度查询摘要
- 发布所需元数据，如作者、摘要、评论开关建议、图片资产清单

## 内容风格

请优先使用 `references/writing-rules.md` 里的写作规范，尤其注意：

- 不要空话和套话
- 不要标准答案腔
- 开头要有场景或情绪
- 文中要有具体细节
- 观点要明确，但不要端着说教

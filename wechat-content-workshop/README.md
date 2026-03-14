# 微信生态内容工坊

一个面向微信公众号的内容生产工作流，负责把简短主题整理成可归档、可复用、可继续发布到微信草稿箱的完整内容包。

## 目标

- 输出适合公众号的中文内容成品
- 降低模板感和 AI 味，强化场景、细节、观点与作者口吻
- 建立清晰的内容归档结构
- 接入免费、免登录、可扩展的多源图像能力
- 与现有 `wechat_artical_publisher_skill-main` 发布器保持兼容

## 目录

```text
wechat-content-workshop/
├── README.md
├── SKILL.md
├── references/
│   └── writing-rules.md
└── scripts/
    └── content_workshop.py
```

## 快速使用

```bash
python3 wechat-content-workshop/scripts/content_workshop.py generate \
  --topic "为什么越来越多人重新爱上菜市场" \
  --series "城市观察" \
  --region "杭州" \
  --audience "在大城市打拼的年轻上班族"
```

执行后会在默认内容根目录下生成一份“单篇选题包”，包含：

- 公众号成稿 Markdown
- 标题备选、摘要、封面文案、分享语、结尾引导语
- 配图计划、封面图和插图资产记录
- JSON/YAML 元数据
- 可直接传给微信发布器的最终稿件

## 常用命令

### 1. 生成内容包

```bash
python3 wechat-content-workshop/scripts/content_workshop.py generate --topic "主题"
```

可选参数：

- `--audience`
- `--region`
- `--series`
- `--tone`
- `--channel`
- `--content-root`
- `--inline-image-count`
- `--cover-width`
- `--cover-height`
- `--skip-images`

### 2. 只导出微信兼容 Markdown

```bash
python3 wechat-content-workshop/scripts/content_workshop.py export-markdown \
  --package-dir "/path/to/package"
```

### 3. 调用现有微信发布器发布到草稿箱

```bash
python3 wechat-content-workshop/scripts/content_workshop.py publish-draft \
  --package-dir "/path/to/package"
```

说明：

- 该命令会调用仓库内已有的 `wechat_artical_publisher_skill-main/scripts/wechat_direct_api.py`
- 仍需提前配置微信 `AppID`、`AppSecret` 与 IP 白名单

## 图像策略

图像层采用“多源适配 + 代理重试 + 本地兜底”：

- 优先尝试免登录的远程图像源
- 每个图像源会按“直连 -> `127.0.0.1:7890` 代理 -> 再次直连”顺序重试
- 成功时下载到本地归档目录
- 如果远程全部失败，会在本地直接生成 PNG 占位图，保证内容包里一定有可用图片文件
- 同时保留失败原因，方便后续排查代理或网络问题

当前内置源：

- `pollinations`
- `placehold`
- `dummyimage`

## 兼容说明

最终稿件默认落在：

```text
final/wechat_article.md
```

它会保留本地图片相对路径，兼容现有微信发布器的图片扫描与上传逻辑。

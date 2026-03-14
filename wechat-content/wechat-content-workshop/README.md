# 微信生态内容工坊

一个面向微信公众号的内容生产工作流，负责把简短主题整理成可归档、可复用、可继续发送到微信草稿箱或直接发布的完整内容包。

## 目标

- 输出适合公众号的中文内容成品
- 降低模板感和 AI 味，强化场景、细节、观点与作者口吻
- 建立清晰的内容归档结构
- 接入 Pollinations Key 鉴权生图，并提供额度提示与文字保底图
- 与现有 `wechat_artical_publisher_skill-main` 发布器保持兼容

## 目录

```text
wechat-content-workshop/
├── README.md
├── SKILL.md
├── references/
│   └── writing-rules.md
├── scripts/
│   ├── content_workshop.py
│   └── workshop/
│       ├── common.py
│       ├── fallback_renderers.py
│       ├── image_generation.py
│       ├── models.py
│       ├── package_builder.py
│       └── pollinations.py
└── tests/
    ├── test_content_workshop.py
    ├── test_image_generation.py
    └── test_pollinations.py
```

## 快速使用

首次使用前，请先安装中文保底图依赖：

```bash
python3 -m pip install --user --break-system-packages Pillow
```

如果你在虚拟环境里运行，则使用：

```bash
python3 -m pip install Pillow
```

1. 复制示例配置并填写 Pollinations Key：

```bash
cp wechat-content-workshop/.env.example .env
```

2. 直接生成内容包：

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

### 3. 只测试图片生成

```bash
python3 wechat-content-workshop/scripts/content_workshop.py test-image \
  --topic "测试图片主题"
```

说明：

- 默认输出到仓库根目录下的 `wechat-content-workshop-image-test/`
- 会生成图片文件和一份 `image_test_report.md`
- Pollinations 图片接口按官方教程走 `?key=YOUR_API_KEY`

### 4. 调用现有微信发布器发送到草稿箱

```bash
python3 wechat-content-workshop/scripts/content_workshop.py publish-draft \
  --package-dir "/path/to/package"
```

说明：

- 该命令会调用仓库内已有的 `wechat_artical_publisher_skill-main/scripts/wechat_direct_api.py`
- 为避免交互卡住，它会显式使用 `--mode draft`
- 仍需提前配置微信 `AppID`、`AppSecret` 与 IP 白名单

## 图像策略

图像层采用“额度前置判断 + AI 生图 + 本地保底图”的降级策略：

- 第一步：先查询 Pollinations Key 状态和余额
- 第二步：根据额度决策是否允许远程 AI 生图
- 第三步：若缺少 Key、鉴权失败、额度不足，则直接生成本地文字保底图
- 第四步：若额度查询失败，则仍尝试远程 AI 生图；单张失败后再自动降级到本地文字保底图
- 请求仍按“直连 -> `127.0.0.1:7890` 代理 -> 再次直连”顺序重试
- 每次执行 `generate` / `test-image` 时，都会先输出账户额度摘要和本次图片策略决策
- 归档时持续记录每张图的 `source`、`generation_strategy`、`decision_reason` 和 `failure_reason`

## `.env` 配置

支持在当前目录、父目录，或 `wechat-content-workshop` 目录放置 `.env`：

```env
POLLINATIONS_API_KEY=sk_your_pollinations_key
# Optional
# POLLINATIONS_API_BASE=https://gen.pollinations.ai
# POLLINATIONS_ACCOUNT_API_BASE=https://gen.pollinations.ai
# POLLINATIONS_IMAGE_MODEL=zimage
```

说明：

- `POLLINATIONS_API_KEY`：必填，生图与额度查询共用
- `POLLINATIONS_API_BASE`：可选，默认 `https://gen.pollinations.ai`
- `POLLINATIONS_ACCOUNT_API_BASE`：可选，默认同上
- `POLLINATIONS_IMAGE_MODEL`：可选，默认 `zimage`

## 依赖说明

- 必需依赖：`Pillow`
- 作用：三级保底图的中文文字渲染
- 推荐安装：

```bash
python3 -m pip install --user --break-system-packages Pillow
```

- 虚拟环境安装：

```bash
python3 -m pip install -r wechat-content-workshop/requirements.txt
```

## 兼容说明

最终稿件默认落在：

```text
final/wechat_article.md
```

它会保留本地图片相对路径，兼容现有微信发布器的图片扫描与上传逻辑。

## 测试

运行全部测试：

```bash
python3 -m unittest discover -s wechat-content-workshop/tests -p 'test_*.py'
```

覆盖重点：

- CLI 生成、导出与图片测试命令回归
- Pollinations 额度判定与图片策略选择
- 远程生图失败后的本地保底图降级

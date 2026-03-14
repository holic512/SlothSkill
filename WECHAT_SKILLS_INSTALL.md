# 微信文章生成与发布技能安装说明

## 结论

如果你要实现“自动生成文章并发布”，最少需要放这 3 个目录到同一层级：

```text
<skills-root>/
├── wechat-content-workshop/
├── wechat_artical_publisher_skill-main/
└── shared/
```

原因：

- `wechat-content-workshop` 负责生成公众号内容包
- `wechat_artical_publisher_skill-main` 负责把内容发布到微信公众号
- `shared` 是两个技能共用的核心模块，里面有文章解析、frontmatter 解析、内容包读取、`.env` 加载等公共逻辑

这 3 个目录必须是同级目录。当前脚本就是按这个目录关系解析导入的。

## 推荐安装目录

如果你是安装到 Codex 的技能目录，推荐放到：

```text
$CODEX_HOME/skills/
├── wechat-content-workshop/
├── wechat_artical_publisher_skill-main/
└── shared/
```

不要把 `shared` 放到某一个技能目录内部，否则两个技能都会找不到公共模块。

## 按用途选择

### 1. 只想生成文章，不发布

放这 2 个目录即可：

```text
<skills-root>/
├── wechat-content-workshop/
└── shared/
```

### 2. 只想发布现成 Markdown，不生成内容

放这 2 个目录即可：

```text
<skills-root>/
├── wechat_artical_publisher_skill-main/
└── shared/
```

### 3. 想从“生成文章”直接走到“发布草稿箱”

必须放这 3 个目录：

```text
<skills-root>/
├── wechat-content-workshop/
├── wechat_artical_publisher_skill-main/
└── shared/
```

## 每个目录里哪些文件要保留

### `wechat-content-workshop` 必须保留

```text
wechat-content-workshop/
├── SKILL.md
├── .env.example
├── requirements.txt
├── references/
│   └── writing-rules.md
└── scripts/
    ├── content_workshop.py
    └── workshop/
        ├── __init__.py
        ├── common.py
        ├── fallback_renderers.py
        ├── image_generation.py
        ├── models.py
        ├── package_builder.py
        └── pollinations.py
```

### `wechat_artical_publisher_skill-main` 必须保留

```text
wechat_artical_publisher_skill-main/
├── SKILL.md
├── .env.example
├── styles/
│   └── custom.css
└── scripts/
    ├── wechat_direct_api.py
    ├── parse_markdown.py
    └── publisher/
        ├── __init__.py
        ├── article_loader.py
        ├── cli.py
        ├── publish_service.py
        └── wechat_api_client.py
```

### `shared` 必须保留

```text
shared/
├── __init__.py
└── wechat_content/
    ├── __init__.py
    ├── article_loader.py
    └── common.py
```

## 哪些内容可以不一起打包

这些不是运行必需项，安装时可以不带：

- `tests/`
- `README.md`
- `README_zh-CN.md`
- `__pycache__/`
- `.DS_Store`
- 本地 `.env`

说明：

- `.env.example` 建议保留，方便安装后复制配置
- 真正的 `.env` 应该由使用者在目标机器上自行填写

## 安装步骤

### 1. 复制目录

把下面三个目录复制到同一个技能根目录下：

```text
wechat-content-workshop/
wechat_artical_publisher_skill-main/
shared/
```

### 2. 安装内容工坊依赖

如果需要内容生成与图片保底图：

```bash
python3 -m pip install -r wechat-content-workshop/requirements.txt
```

如果只缺 `Pillow`，也可以单独安装：

```bash
python3 -m pip install Pillow
```

### 3. 配置发布器环境变量

复制发布器环境模板：

```bash
cp wechat_artical_publisher_skill-main/.env.example wechat_artical_publisher_skill-main/.env
```

填写至少这几个变量：

```ini
WECHAT_APPID=你的公众号AppID
WECHAT_APPSECRET=你的公众号AppSecret
WECHAT_AUTHOR=你的作者名
WECHAT_NEED_OPEN_COMMENT=1
WECHAT_ONLY_FANS_CAN_COMMENT=0
```

### 4. 可选配置内容工坊环境变量

如果要启用 Pollinations 生图：

```bash
cp wechat-content-workshop/.env.example wechat-content-workshop/.env
```

然后填写：

```ini
POLLINATIONS_API_KEY=你的Key
```

## 使用方式

### 先生成内容包

```bash
python3 wechat-content-workshop/scripts/content_workshop.py generate --topic "选题"
```

生成完成后会输出内容包目录，以及下一步发布命令。

### 再发布到公众号草稿箱

```bash
python3 wechat_artical_publisher_skill-main/scripts/wechat_direct_api.py publish --mode draft --package-dir "/path/to/package"
```

### 直接发布现成 Markdown

```bash
python3 wechat_artical_publisher_skill-main/scripts/wechat_direct_api.py publish --mode draft --markdown "/path/to/article.md"
```

## 目录关系检查

如果你安装后发现导入失败，先检查是不是这个问题：

错误示例：

```text
skills/
└── wechat-content-workshop/
    └── shared/
```

这是错的，因为 `shared` 不能嵌在某个技能里面。

正确示例：

```text
skills/
├── wechat-content-workshop/
├── wechat_artical_publisher_skill-main/
└── shared/
```

## 最小可运行组合

要实现“自动生成文章并发布”，最小可运行组合就是：

```text
wechat-content-workshop/
wechat_artical_publisher_skill-main/
shared/
```

少了 `shared`，两个技能都会失效。
少了 `publisher`，只能生成不能发布。
少了 `workshop`，只能发布不能自动产文。

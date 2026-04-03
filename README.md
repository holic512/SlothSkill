# SlothSkill

`SlothSkill` 是一个技能仓库，当前重点维护两条工作流：

- 微信公众号内容生成与发布
- 实验/课程/数据库类报告自动编排

同时新增了两个项目级独立技能：

- `frontend-visual-workshop`
- `jdbc-schema-assistant`

如果你现在的目标是“自动生成公众号文章并发布到微信公众号”，重点看这 3 个目录：

- `wechat-content-workshop`
- `wechat_artical_publisher_skill-main`
- `shared`

## 微信工作流概览

这套微信能力现在是分层设计，不是一个大而全的单体技能。

### 1. `wechat-content-workshop`

负责内容生产层：

- 生成标题、摘要、正文、封面文案、分享语、结尾引导语
- 生成标准内容包
- 归档图片计划、素材、成稿和元数据
- 输出兼容发布器的 `final/wechat_article.md`

### 2. `wechat_artical_publisher_skill-main`

负责发布执行层：

- 读取 Markdown 或标准内容包
- 上传本地图片
- 上传封面
- 渲染微信样式
- 创建草稿 / 直接发布 / 查询历史

### 3. `shared`

负责公共核心：

- `.env` 加载
- frontmatter 解析
- 内容包元数据读取
- 文章对象装载
- Markdown 图片与结构解析

## 目录关系

如果你要跑通“生成文章并发布”，目录必须是这个关系：

```text
<skills-root>/
├── wechat-content-workshop/
├── wechat_artical_publisher_skill-main/
└── shared/
```

`shared` 必须和两个技能目录平级。

错误放法：

```text
skills/
└── wechat-content-workshop/
    └── shared/
```

这样两个技能都会导入失败。

## 快速开始

### 1. 复制目录

最小可运行组合：

```text
wechat-content-workshop/
wechat_artical_publisher_skill-main/
shared/
```

### 2. 安装依赖

内容工坊依赖：

```bash
python3 -m pip install -r wechat-content-workshop/requirements.txt
```

如果只需要图片保底图能力，至少安装：

```bash
python3 -m pip install Pillow
```

### 3. 配置微信公众号发布器

```bash
cp wechat_artical_publisher_skill-main/.env.example wechat_artical_publisher_skill-main/.env
```

填写：

```ini
WECHAT_APPID=你的公众号AppID
WECHAT_APPSECRET=你的公众号AppSecret
WECHAT_AUTHOR=你的作者名
WECHAT_NEED_OPEN_COMMENT=1
WECHAT_ONLY_FANS_CAN_COMMENT=0
```

### 4. 可选配置内容工坊

如果要启用 Pollinations 生图：

```bash
cp wechat-content-workshop/.env.example wechat-content-workshop/.env
```

填写：

```ini
POLLINATIONS_API_KEY=你的Key
```

## 使用流程

### 1. 生成公众号内容包

```bash
python3 wechat-content-workshop/scripts/content_workshop.py generate --topic "为什么越来越多人重新爱上菜市场"
```

输出结果会包含：

- 内容包目录
- 公众号成稿路径
- 下一步发布命令

### 2. 发布到公众号草稿箱

```bash
python3 wechat_artical_publisher_skill-main/scripts/wechat_direct_api.py publish --mode draft --package-dir "/path/to/package"
```

### 3. 直接发布现成 Markdown

如果你已经有文章，不走内容工坊，也可以直接发布：

```bash
python3 wechat_artical_publisher_skill-main/scripts/wechat_direct_api.py publish --mode draft --markdown "/path/to/article.md"
```

## 安装组合

### 只生成，不发布

需要：

- `wechat-content-workshop`
- `shared`

### 只发布，不生成

需要：

- `wechat_artical_publisher_skill-main`
- `shared`

### 生成并发布

需要：

- `wechat-content-workshop`
- `wechat_artical_publisher_skill-main`
- `shared`

## 必须保留的目录

### 内容工坊

```text
wechat-content-workshop/
├── SKILL.md
├── .env.example
├── requirements.txt
├── references/
└── scripts/
```

### 发布器

```text
wechat_artical_publisher_skill-main/
├── SKILL.md
├── .env.example
├── styles/
└── scripts/
```

### 公共层

```text
shared/
└── wechat_content/
```

## 可以不打包的内容

这些不属于运行必需项：

- `tests/`
- `README_zh-CN.md`
- `__pycache__/`
- `.DS_Store`
- 本地 `.env`

## 详细安装文档

更完整的安装说明见：

- [WECHAT_SKILLS_INSTALL.md](./WECHAT_SKILLS_INSTALL.md)

这个文档已经拆清楚了：

- 必须带哪些目录
- 每个目录里哪些文件必须保留
- 哪些文件可以不打包
- 只生成 / 只发布 / 生成+发布 三种安装方式

## 其他技能

### `frontend-visual-workshop`

用于在前端页面、文章页、落地页或产品介绍页已经基本成形后，按需补齐视觉资产。它是项目级独立 skill，不在 `wechat-content/` 工作流内，也不依赖 `wechat-content-workshop`、`wechat_artical_publisher_skill-main` 或 `shared`。

适用场景：

- 需要补 `logo`、`favicon`、`hero`、`feature`、`empty-state`、`cover`
- 需要统一提示词结构，降低 AI 味，保留中文标题覆盖空间
- 需要带远程生图失败回退和本地保底图能力
- 想先生成计划和提示词，再决定是否实际生图

目录位置：

```text
frontend-visual-workshop/
├── SKILL.md
├── .env.example
├── scripts/
└── tests/
```

#### `frontend-visual-workshop` 运行环境

运行这个 skill 需要：

- Python 3.10 及以上
- 可访问 Pollinations 接口的网络环境
- 可选代理：
  - `POLLINATIONS_PROXY_ENABLED=1`
  - `POLLINATIONS_PROXY_URL=http://127.0.0.1:7890`
- 可选环境变量：
  - `POLLINATIONS_API_KEY`
  - `POLLINATIONS_API_BASE`
  - `POLLINATIONS_ACCOUNT_API_BASE`
  - `POLLINATIONS_IMAGE_MODEL`

说明：

- 不配置 `POLLINATIONS_API_KEY` 也能运行，但会直接回退为本地保底图
- 当前脚本不依赖第三方 Python 包，标准库即可运行

准备环境变量：

```bash
cp frontend-visual-workshop/.env.example frontend-visual-workshop/.env
```

只生成资产计划和提示词：

```bash
python3 frontend-visual-workshop/scripts/visual_workshop.py plan \
  --topic "AI 简历助手" \
  --brand "SlothSkill" \
  --page-type "landing" \
  --asset-types "logo,hero,feature"
```

实际生成图片：

```bash
python3 frontend-visual-workshop/scripts/visual_workshop.py generate \
  --topic "AI 简历助手" \
  --brand "SlothSkill" \
  --page-type "landing" \
  --asset-types "logo,hero,feature,empty-state,cover,favicon"
```

单独测试某类资产：

```bash
python3 frontend-visual-workshop/scripts/visual_workshop.py test-image \
  --topic "AI 简历助手" \
  --brand "SlothSkill" \
  --page-type "landing" \
  --asset-types "logo,cover"
```

输出内容：

- `assets/`: 最终图片
- `prompts/`: 每张图的最终提示词
- `package.json`: 资产计划和元数据
- `report.md`: 资产决策、提示词版本、来源、失败原因、回退说明

### `experiment-report-md`

Used to generate English experiment-report Markdown from repository evidence. It is intended for coursework, lab, and project experiment reports that should stop at `report.source.md`.

### `plantuml-professional-diagrams`

Used to create professional PlantUML diagrams, especially sequence and interaction diagrams, render them into images, and rewrite Markdown to reference those rendered images.

### `jdbc-schema-assistant`

用于读取 Spring 配置或显式 JDBC MySQL 连接信息，自动探查数据库、表、字段、索引、外键与样例数据，并进一步生成 CRUD、分页查询、条件筛选和逻辑删除建议。

适用场景：

- Spring / Spring Boot 项目中需要从 `application.yml`、`application.yaml`、`application.properties` 读取数据源
- 需要快速理解真实 MySQL 库表结构
- 需要给 MyBatis / JPA / 手写 SQL 开发提供结构化 JSON 和 CRUD 规划

### `jdbc-schema-assistant` 运行环境

运行这个 skill 需要：

- Python 3.10 及以上
- 可访问的 MySQL 5.7+ 或 MySQL 8.x
- Python 依赖：
  - `PyMySQL`
  - `PyYAML`

安装依赖：

```bash
python3 -m pip install -r jdbc-schema-assistant/requirements.txt
```

如果你的 Python 环境启用了 PEP 668 限制，且你明确接受当前环境安装依赖，可以改用：

```bash
python3 -m pip install --user --break-system-packages -r jdbc-schema-assistant/requirements.txt
```

注意：

- 这个 skill 第一版只支持 MySQL
- 默认只读，不执行 `INSERT`、`UPDATE`、`DELETE`、`DDL`
- 不要求创建虚拟环境，但需要当前 Python 环境里已安装依赖

### `jdbc-schema-assistant` 使用方式

1. 从 Spring 配置读取：

```bash
python3 jdbc-schema-assistant/scripts/db_inspector.py inspect-config --project-dir /path/to/project
```

2. 显式传 JDBC 信息：

```bash
python3 jdbc-schema-assistant/scripts/db_inspector.py inspect-url \
  --url "jdbc:mysql://localhost:3306/a-20?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai" \
  --username root \
  --password 123456
```

3. 基于探查结果生成 CRUD 规划：

```bash
python3 jdbc-schema-assistant/scripts/crud_planner.py plan --input /path/to/schema.json
```

输出内容包括：

- schema JSON
- 表结构摘要
- CRUD SQL 模板
- 条件查询与排序建议
- Java 字段类型与参数提示

## 来源与致谢

微信公众号发布模块 `wechat_artical_publisher_skill-main` 基于开源项目继续整理与扩展：

- 上游仓库：[aximof/wechat_artical_publisher_skill](https://github.com/aximof/wechat_artical_publisher_skill)
- 上游许可证：MIT License

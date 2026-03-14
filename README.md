# SlothSkill

`SlothSkill` 是一个技能仓库，当前重点维护两条工作流：

- 微信公众号内容生成与发布
- 实验/课程/数据库类报告自动编排

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

### `report-orchestrator`

用于实验报告、课程设计报告、数据库设计报告等文档自动编排，适合从项目目录直接生成结构化 Markdown 报告，并在条件满足时补齐图表与导出结果。

## 来源与致谢

微信公众号发布模块 `wechat_artical_publisher_skill-main` 基于开源项目继续整理与扩展：

- 上游仓库：[aximof/wechat_artical_publisher_skill](https://github.com/aximof/wechat_artical_publisher_skill)
- 上游许可证：MIT License

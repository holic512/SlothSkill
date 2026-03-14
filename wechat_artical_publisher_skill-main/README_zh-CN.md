[English](README.md) | 中文

# 微信公众号发布器

一个强大的独立工具，可通过微信官方 API 将 Markdown 文章直接发布到微信公众号草稿箱。

![License](https://img.shields.io/badge/license-MIT-blue.svg)

## ✨ 特性

- **直连官方 API**：无需第三方代理，使用你自己的 AppID/AppSecret。
- **自动上传图片**：自动识别 Markdown 中的本地图片，上传到微信服务器 (`mmbiz.qpic.cn`) 并替换链接。
- **精美排版**：内置 `bm.md` API 集成，支持"绿色简约"主题。
- **移动端优化**：自动修复微信移动端列表渲染异常等 Bug。
- **开箱即用**：纯 Python 实现，无外部依赖。

## 📋 前置条件

1. **微信公众号**（服务号或订阅号）
2. **Python 3.8+**
3. **AppID 和 AppSecret**：从微信公众平台 > 开发 > 基本配置中获取。
4. **IP 白名单**：在微信公众平台中将你的服务器公网 IP 添加到白名单。

## 🚀 快速开始

### 1. 克隆并配置

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/wechat-article-publisher.git
cd wechat-article-publisher

# 从模板创建配置文件
cp .env.example .env

# 编辑 .env 填入你的凭证
# WECHAT_APPID=wxXXXXXXXXXXXXXXXX
# WECHAT_APPSECRET=你的appsecret
```

### 2. 发布你的第一篇文章

```bash
cd scripts
python wechat_direct_api.py publish --markdown "/path/to/your/article.md"
```

完成！你的文章将出现在微信公众号的草稿箱中。

## 📂 目录结构

```
wechat-article-publisher/
├── scripts/
│   ├── wechat_direct_api.py   # 核心发布脚本
│   └── parse_markdown.py      # Markdown 解析工具
├── styles/
│   └── custom.css             # 内置样式（绿色简约主题）
├── .env.example               # 凭证模板
├── .gitignore
├── SKILL.md                   # Agent 技能定义
└── README.md
```

## 🔧 可用命令

| 命令 | 说明 |
|------|------|
| `python wechat_direct_api.py publish --markdown <文件>` | 发布 Markdown 文件到草稿箱 |
| `python wechat_direct_api.py test-token` | 验证 API 凭证和 IP 白名单 |
| `python wechat_direct_api.py upload-image <文件>` | 上传单张图片到微信素材库 |

## 🐛 常见问题

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `invalid ip` / `40164` | IP 未加入白名单 | 在微信公众平台 > IP 白名单中添加报错提示的 IP |
| `invalid appid` | 凭证错误 | 检查 `.env` 中的 `WECHAT_APPID` |
| 手机端列表序号显示空白 | 微信移动端渲染 Bug | 本工具已自动将列表转换为段落格式修复此问题 |

## 🤖 作为 Agent 技能使用

本项目包含 `SKILL.md` 文件，可与 Claude Code 等 AI Agent 配合使用。只需将文件夹放入 Agent 的技能目录，然后告诉 Agent "发布到微信公众号" 即可。

## 📄 许可证

MIT License - 可自由使用、修改和分发。

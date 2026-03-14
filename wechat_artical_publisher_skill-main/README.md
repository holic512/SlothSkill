English | [中文](README_zh-CN.md)

# WeChat Article Publisher (微信公众号发布器)

A powerful, standalone skill/tool to publish Markdown articles directly to WeChat Official Account drafts via the official WeChat API.

![License](https://img.shields.io/badge/license-MIT-blue.svg)

## ✨ Features

- **Direct API Integration**: No third-party proxies. Uses your own AppID/AppSecret.
- **Auto Image Upload**: Automatically finds local images in Markdown, uploads them to WeChat's servers (`mmbiz.qpic.cn`), and replaces links.
- **Smart Formatting**: Built-in integration with `bm.md` API for professional styling (Green Simple theme).
- **Mobile Optimized**: Automatically fixes WeChat mobile rendering bugs (e.g., list styling, image captions).
- **Standalone**: All-in-one package. No external dependencies.

## 📋 Prerequisites

1. **WeChat Official Account** (Service or Subscription Account)
2. **Python 3.8+**
3. **AppID & AppSecret**: Obtained from WeChat Admin Panel > Development > Basic Configuration.
4. **IP Whitelist**: Add your machine's public IP to the IP Whitelist in WeChat Admin Panel.

## 🚀 Quick Start

### 1. Clone and Configure

```bash
# Clone this repository (or copy the folder)
git clone https://github.com/YOUR_USERNAME/wechat-article-publisher.git
cd wechat-article-publisher

# Create your .env file from the template
cp .env.example .env

# Edit .env with your credentials
# WECHAT_APPID=wxXXXXXXXXXXXXXXXX
# WECHAT_APPSECRET=your_appsecret_here
```

### 2. Publish Your First Article

```bash
cd scripts
python wechat_direct_api.py publish --markdown "/path/to/your/article.md"
```

That's it! Your article will appear in your WeChat Official Account draft box.

## 📂 Directory Structure

```
wechat-article-publisher/
├── scripts/
│   ├── wechat_direct_api.py   # Core publishing script
│   └── parse_markdown.py      # Markdown parsing utilities
├── styles/
│   └── custom.css             # Built-in styling (Green Simple theme)
├── .env.example               # Credential template
├── .gitignore
├── SKILL.md                   # Agent skill definition
└── README.md
```

## 🔧 Available Commands

| Command | Description |
|---------|-------------|
| `python wechat_direct_api.py publish --markdown <file>` | Publish a Markdown file to drafts |
| `python wechat_direct_api.py test-token` | Verify API credentials and IP whitelist |
| `python wechat_direct_api.py upload-image <file>` | Upload a single image to WeChat |

## 🐛 Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `invalid ip` / `40164` | IP not whitelisted | Add the IP shown in the error to WeChat Admin Panel > IP Whitelist |
| `invalid appid` | Wrong credentials | Check `WECHAT_APPID` in `.env` |
| Lists show empty numbers on phone | Mobile rendering bug | The tool auto-converts lists to paragraphs to fix this |

## 🤖 Use as an Agent Skill

This package includes a `SKILL.md` file, making it compatible with AI agents like Claude Code. Simply place the folder in your agent's skill directory and instruct the agent to "publish to WeChat".

## 📄 License

MIT License - feel free to use, modify, and distribute.

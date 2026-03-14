---
name: wechat-article-publisher
description: Publish Markdown articles to WeChat Official Account (微信公众号) via Official API
---

# WeChat Article Publisher (Direct API Version)

A powerful, standalone tool to send Markdown articles to WeChat Official Account drafts or directly publish them via the official WeChat API.

**Key Features:**
- **Direct API Integration**: No third-party proxies. Uses your own AppID/AppSecret.
- **Auto Image Upload**: Automatically finds local images in Markdown, uploads them to WeChat's servers (`mmbiz.qpic.cn`), and replaces links. 
- **Smart Formatting**: Built-in integration with `bm.md` API for professional styling (Green Simple theme).
- **Mobile Optimized**: Automatically fixes WeChat mobile rendering bugs (e.g., list styling, image captions).
- **Draft / Direct Publish / History**: Supports draft creation, direct publish submission, publish status polling, and published-history queries.
- **Standalone**: All-in-one package. No external skill dependencies.

## Agent Behavior

When the user asks to publish:

1. Ask first: send to drafts, direct publish, or view published history.
2. If the user chooses drafts, run the draft flow.
3. If the user chooses direct publish, create a draft first, then submit it for publishing and poll status.
4. If the user asks to review published records, use the history query flow.
5. When AI is helping generate or refine the Markdown, it should also assess whether these fields are reasonable:
   - `author`
   - `need_open_comment`
   - `only_fans_can_comment`

Use conservative defaults:
- `need_open_comment=1` for most content/opinion/tutorial articles
- `need_open_comment=0` for notices, rule pages, or low-interaction announcements
- `only_fans_can_comment=0` unless the user explicitly wants stricter audience control

## Prerequisites

1.  **WeChat Official Account** (Service or Subscription Account)
2.  **Python 3.8+**
3.  **AppID & AppSecret**: Obtained from WeChat Admin Panel > Development > Basic Configuration.
4.  **IP Whitelist**: Add your machine's public IP to the IP Whitelist in WeChat Admin Panel.

## Configuration

The tool uses a `.env` file in the skill directory for configuration.

**File Location:** `scripts/.env` or parent directories.

```ini
# Required: WeChat Official Account Credentials
WECHAT_APPID=wxXXXXXXXXXXXXXXXX
WECHAT_APPSECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional: Article defaults
WECHAT_AUTHOR=Your Name
WECHAT_NEED_OPEN_COMMENT=1
WECHAT_ONLY_FANS_CAN_COMMENT=0
```

## Usage

All commands are run via `scripts/wechat_direct_api.py`.

### 1. Publish Article (Main Command)

This single command handles the entire workflow: image upload -> cover upload -> formatting -> draft creation, and can optionally continue to direct publish.

```bash
cd scripts
python wechat_direct_api.py publish --markdown "/path/to/your/article.md"
python wechat_direct_api.py publish --mode draft --markdown "/path/to/your/article.md"
python wechat_direct_api.py publish --mode publish --markdown "/path/to/your/article.md"
```

**What happens:**
1.  **Token**: Automatically gets/refreshes Access Token.
2.  **Images**: Scans Markdown for local images, uploads them to WeChat material library.
3.  **Cover**: Uploads the first image (or specified cover) as the article thumb.
4.  **Formatting**: Renders Markdown to HTML using `bm.md` API with custom CSS.
5.  **Fixes**: Applies mobile compatibility fixes (lists to paragraphs, hidden captions).
6.  **Metadata**: Resolves `author`, `need_open_comment`, and `only_fans_can_comment` from CLI args, frontmatter, or `.env`.
7.  **Draft / Publish**: Creates a draft, then either stops there or submits it for direct publish and polls the result.

### Frontmatter Support

You can place article metadata at the top of the Markdown:

```yaml
---
author: 张三
need_open_comment: 1
only_fans_can_comment: 0
---
```

### 2. Test Token & IP Whitelist

Use this to verify your API credentials and IP whitelisting status.

```bash
python wechat_direct_api.py test-token
```

### 3. Upload Single Image

Upload a local image to WeChat and get its URL (useful for testing).

```bash
python wechat_direct_api.py upload-image "/path/to/image.jpg"
```

### 4. Query Published History

```bash
python wechat_direct_api.py history --offset 0 --count 20
```

## Directory Structure

```text
wechat-article-publisher/
├── scripts/
│   └── wechat_direct_api.py   # Core logic script
├── styles/
│   └── custom.css             # Built-in styling file (Green Simple)
├── .env                       # Config file (User created)
└── SKILL.md                   # This documentation
```

## Troubleshooting

| Error | Cause | Solution |
| :--- | :--- | :--- |
| `invalid ip` / `40164` | IP not whitelisted | Add the IP shown in the error message to WeChat Admin Panel > Basic Configuration > IP Whitelist. |
| `invalid appid` | Wrong credentials | Check `WECHAT_APPID` in `.env`. |
| `invalid media_id` | Image upload failed | Ensure cover image path is correct/accessible. |
| Lists show empty numbers on phone | Mobile rendering bug | The tool now auto-converts lists to paragraphs to fix this. Ensure you are using the latest version. |

## Advanced: Customizing Styles

The styling is defined in `styles/custom.css`. You can modify this file to change fonts, colors, or spacing. The script automatically loads this file during the formatting process.

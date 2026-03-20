---
name: frontend-visual-workshop
description: Generate frontend visual assets including logos, hero images, illustrations, empty states, and cover art with prompt tuning and fallback rendering
---

# 前端视觉资产工坊

这个技能用于在前端内容已经基本成形、但视觉支撑不足时，按需生成必要资产。目标不是“为了更丰富而多做几张图”，而是补齐能提升表达和完成度的封面、插图、 logo、hero 图、空状态图和小图标。

## 何时触发

- 页面或文章已经有清晰主题，但缺少关键视觉承载
- 需要封面、页面 hero、功能说明插图、空状态图、logo、favicon
- 需要中文排版友好的视觉留白和标题覆盖空间
- 需要带额度检查、失败回退和本地保底图流程的生图能力

不要在这些情况下触发：

- 用户只是在改文案或代码，视觉并不是当前阻塞点
- 现有页面已经有足够明确、统一的视觉资产
- 只是想“多来几张图看看”，但没有清晰用途

## 工作顺序

1. 先判断是否真的缺视觉资产
2. 明确资产类型和用途，不把不同角色混成一张图
3. 用脚本生成计划和精调后的提示词
4. 只有必要时再实际生图
5. 输出 `assets/`、`prompts/`、`report.md`，保留决策和失败原因

## 视觉原则

- 服务表达，不做无关装饰
- 避免强 AI 味、廉价科技蓝紫渐变、过度 3D、无意义漂浮元素
- 保留中文标题覆盖区和安全留白
- logo / favicon 优先单图形、强识别、小尺寸可读
- 功能插图和空状态图优先信息结构，不堆细节

## 常用命令

先准备环境变量：

```bash
cp frontend-visual-workshop/.env.example .env
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
  --asset-types "logo,cover"
```

## 资产类型说明

- `logo`: 品牌主标识，扁平、几何、强识别
- `favicon`: 小尺寸图标，单元素、高对比
- `hero`: 首页主视觉，要给中文标题留空间
- `feature`: 功能说明插图，强调结构和动作
- `empty-state`: 轻量、友好、低干扰
- `cover`: 面向文章封面或分享预览图，横版、安全裁切、适合标题覆盖

## 脚本输出

- `assets/`: 最终图片
- `prompts/`: 每张图最终提示词
- `report.md`: 资产决策、提示词版本、来源、失败原因、回退说明

如果需要看提示词模板或修改分支规则，优先读脚本 `scripts/visual_workshop.py`。

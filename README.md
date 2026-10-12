# QUSEIT 示例智能体

这个仓库收集 [QUSEIT](https://agent.quseit.com) 平台的**示例智能体**。每个示例都是一份可以照着在 QUSEIT 后台从零复现的完整素材：技能文件、页面与运行配置、记录表定义、图文步骤说明，以及一个可选的一键发布脚本。

适合这样用：

- 想了解 QUSEIT 能做出什么样的智能体，直接看示例的 README 和线上地址；
- 想做类似的智能体，复制示例文件夹当模板，改技能和配置；
- 平台运营想批量搭建 / 恢复示例，用示例里的脚本。

## QUSEIT 是什么

QUSEIT（Q Agent as a Service）是一个智能体发布平台：创作者把自己的**技能**（一个含 `SKILL.md` 的文件夹，写明做事的方法与规则）发布成可分享、可收费的对外智能体，访客通过链接或二维码直接对话；创作者在后台看对话数据、版本和收入。

## 目录约定

**每个示例一个文件夹**，文件夹名即示例名（小写字母 + 连字符），放在仓库根目录下。文件夹内结构固定：

```
<example-name>/
├── README.md              # 必备：目标与适用场景、对话设计要点、配置与字段说明、在后台从零创建发布的步骤、线上地址
├── skill/                 # 必备：技能目录，里面至少有 SKILL.md；上传到后台「技能库」的就是它
│   └── SKILL.md
├── agent.json             # 必备：页面与运行配置（见下）
├── record_schema.json     # 可选：记录表定义；示例不收集结构化数据就不放
└── scripts/
    └── publish_in_container.py   # 可选：给平台运营用的一键发布脚本
```

约定：

- `agent.json` 与 `record_schema.json` 是**线上版本的事实源**：线上配置有改动时，同步改这里。
- JSON 用 UTF-8、2 空格缩进、中文不转义。
- **不放任何密钥、token、密码、账号、内部 id（用户 / 页面 / 版本 id）、服务器地址**。模型凭据由创作者在后台自己配置，配置里只写模型名与供应商。
- 文档与示例内容默认使用中文（zh-CN）。

`agent.json` 的字段：

| 字段 | 含义 |
| --- | --- |
| `title` / `slug` / `description` | 名称 / 访问地址后缀（对外为 `/s/<slug>`，全平台唯一）/ 一句话描述 |
| `greeting` | 开场白，访客进来看到的第一句话 |
| `starter_questions` | 引导问题，`[{label, prompt}]`：按钮上的字 / 点击后发出的话 |
| `input_placeholder` | 输入框提示语（对话页底部输入框里的灰色字） |
| `engine` | 运行引擎，`chat` = 对话（无沙箱），其余引擎见平台后台 |
| `model` / `default_provider` | 模型名 / 供应商 |
| `temperature` | 温度 |
| `pricing_mode` / `free_rounds` | 收费方式（如 `free`）/ 免费轮次 |
| `web_search_enabled` | 是否允许联网搜索 |
| `is_service_page_enabled` / `is_api_enabled` | 是否开启对外页面 / API 接入 |

`record_schema.json` 的格式为 `{"version": 1, "scope": "session", "fields": [...]}`，每个字段有 `key`、`label`、`type`（`single_choice` / `multi_choice` / `number` / `boolean` / `text` / `long_text`）、`description`（写给 AI 的判断说明），以及按需的 `options`、`required`、`pii`、`show_in_table`、`min`、`max`。记录表只对 `engine=chat` 的智能体生效。

## 怎么新增一个示例

1. 复制一个现有示例文件夹（如 `ai-scene-advisor/`）改名，或按上面的结构新建。
2. 写技能：`skill/SKILL.md`（开头 front matter 带 `name` 与 `description`），把对话规则写清楚。
3. 在 QUSEIT 后台按示例 README 的步骤实际发布一遍，确认效果满意。
4. 把线上最终使用的配置回填到 `agent.json`（和 `record_schema.json`），保证与线上一致。
5. 写示例 `README.md`，必须让没参与过开发的人能照着在后台从零复现：每一步写清在哪个页面、点哪个按钮、填什么，并写明记录表字段含义、「更新版本后才生效」之类的注意事项，以及怎么查看数据。
6. 如需脚本发布，参照 `ai-scene-advisor/scripts/publish_in_container.py` 做参数化（不得硬编码邮箱、id、密钥）。
7. 提交前自查敏感信息，例如：`grep -rnE "sk-|token|password|[0-9a-f]{8}-[0-9a-f]{4}-" .`，并在本文件的示例清单里加一行。

## 示例清单

| 名称 | 场景 | 引擎 | 是否用记录表 | 线上地址 |
| --- | --- | --- | --- | --- |
| [AI 场景顾问](ai-scene-advisor/) | 轻松聊几轮访客的工作 / 学习，当场给出 AI 用法建议，并把明确说出的信息记进记录表（线索收集 / 访谈） | 对话（无沙箱，`chat`） | 是（7 个字段） | https://agent.quseit.com/s/ai-advisor |

<div align="center">

# ↗ Codex History

### 好不容易得到的答案，不该淹没在终端滚屏里。

找到那个问题。回到那段对话。让代码、公式和答案都好好呈现。

[![MIT License](https://img.shields.io/badge/license-MIT-d6c18e)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-477c93)](#安装)
[![默认离线](https://img.shields.io/badge/local-offline%20by%20default-697b67)](#聊天记录留在本机)
[![Checks](https://github.com/YijingGuo-June/codex-history/actions/workflows/checks.yml/badge.svg)](https://github.com/YijingGuo-June/codex-history/actions/workflows/checks.yml)

[English](README.md) · **简体中文** · [安装](#安装) · [常见问题](#常见问题)

![Codex History：左侧问题目录，右侧连续阅读](docs/images/reader-light.png)

*截图全部使用合成示例，不含真实聊天记录。*

</div>

你记得问过一个问题，也记得 AI 给过一个不错的答案。但它现在夹在几百行过程记录中，往上翻很久也找不到。

**Codex History 把当前会话变成一份可以搜索、跳转、舒服阅读的文档。** 选中问题、按下回车，就回到那次问答。前后的上下文仍然保留；想只看结果时，把过程记录收起来就好。

## 像选文件一样，找到那次提问

![问题选择器：搜索、上下选择、回车定位](docs/images/question-picker.png)

每个已保存的问题都是一个导航点。输入关键词，用 **↑ / ↓** 选择，按 **Enter** 跳转。定位后仍可上下滚动，查看相邻问答，不会把一段对话切成孤立的搜索结果。

| 找得快 | 读得清 | 留得住 |
| :--- | :--- | :--- |
| 问题目录与搜索 | Markdown、表格、代码高亮 | 单文件 HTML 导出 |
| 键盘操作与定位 | 行内和独立 LaTeX 公式 | 字体和渲染资源随文件提供 |
| 连续完整的上下文 | 只看最终回答 | 浏览器离线阅读 |
| 精确选择当前会话 | 浅色与深色主题 | 原始记录只读 |

## 让公式回到它应该有的样子

![中文、LaTeX 公式和 Markdown 表格的真实渲染效果](docs/images/math-and-markdown.png)

支持 `$…$`、`$$…$$`、`\(…\)` 和 `\[…\]`。代码有高亮和复制按钮，表格有清晰的行列，中英文可以自然地出现在同一个回答中。渲染资源已经打包，无需访问 CDN。

<details>
<summary><strong>深夜继续读？展开看看深色主题。</strong></summary>

![Codex History 深色主题](docs/images/reader-dark.png)

</details>

## 安装

需要已有的 **支持插件的 Codex CLI、Python 3.9+ 和现代浏览器**。使用者无需执行 npm 或 pip 安装，也不需要为阅读器配置 API key。导出的 HTML 只需要浏览器。

```sh
git clone https://github.com/YijingGuo-June/codex-history.git
cd codex-history
codex plugin marketplace add .
codex plugin add codex-history@personal
```

新开一个 Codex 会话，输入并选择：

```text
$codex-history:history
```

也可以输入 `$history` 搜索本插件的技能，或通过 `/skills` 查找。

程序会生成离线 HTML 快照，并请求默认浏览器打开。默认模式**不监听端口、不启动后台服务**；如果宿主阻止打开浏览器，会返回生成文件的路径。再次调用即可包含新消息。

> 这是标准 Codex 插件提供的**本地浏览器阅读页**，不替换 Codex 程序，也不注册原生 `/history` 命令。接口依据 Codex CLI `0.155.0-alpha.9` 检查。

### 先看效果，再决定安装

在克隆的仓库目录运行，仅读取合成示例：

```sh
python3 plugins/codex-history/scripts/history.py open --demo
```

也可以下载仓库，用浏览器打开其中的 **[demo.html](demo.html)**。GitHub 文件页展示的是源码，保存到本地后打开才是可操作的阅读器。这个示例不需要 Python，也可以离线打开。

### 不想等模型调用？直接使用本地命令

`$history` 是技能，会经过一轮模型调用来执行脚本。希望立即启动时，可以使用 Codex CLI 的 **`!` 本地命令模式**。

macOS / Linux 用户可以在仓库根目录执行一次：

```sh
mkdir -p "$HOME/.local/bin"
ln -s "$PWD/plugins/codex-history/scripts/history.py" "$HOME/.local/bin/codex-history"
```

确保 `~/.local/bin` 在终端的 `PATH` 中，然后启动 Codex，输入：

```text
!codex-history
```

该入口直接执行本地程序，Codex 会传入当前会话 ID。快捷命令需要单独设置，安装插件不会自动添加它；设置后请保留仓库所在位置。

不设置快捷命令也可以输入 `!python3 /仓库绝对路径/plugins/codex-history/scripts/history.py open`。Windows 可将 `python3` 换为 `py -3`。

## 常用操作

| 操作 | 快捷键 |
| :--- | :--- |
| 打开问题列表 | **⌘K / Ctrl+K**，或非输入状态下的 **/** |
| 选择问题 | **↑ / ↓** |
| 跳转到问答 | **Enter** |
| 关闭列表 | **Escape** |
| 显示 / 隐藏过程记录 | **Alt+H**；浏览器允许时也可用 **Ctrl+H** |

右上角 **Answers only** 隐藏已保存的推理摘要、工具输出和过程更新；关闭后可重新查看。它只改变页面呈现，不修改原始记录和模型思考设置。部分浏览器占用了 Ctrl+H，此时使用按钮或 Alt+H。

## 聊天记录留在本机

```text
Codex 会话记录             Codex History                 你的浏览器
SQLite / rollout JSONL ──▶ 本地只读程序 ────────────────▶ 离线 HTML 快照
                           精确选择当前会话               Markdown · 代码 · 公式
```

- 阅读器没有遥测、统计、远程渲染服务或网络模型调用。`$history` 技能本身仍经过 Codex 正常的模型调用流程。
- 字体和渲染库全部随插件提供；远程图片不自动加载，外部链接由你点击后打开。
- 只读原始记录，不修改数据库、不迁移会话、不更改 Codex 配置。
- 使用 `CODEX_THREAD_ID` 选择会话，不猜测“最近更新的聊天”。
- 默认快照保存在私有临时目录，包含会话内容，由你或系统的临时文件清理机制删除。分享前请确认内容。
- 原始 HTML 显示为文本，生成的 Markdown 经过清理，KaTeX 使用 `trust: false`。不展示原始或加密推理字段。

### 需要实时更新时

```sh
python3 plugins/codex-history/scripts/history.py open --thread-id 会话UUID --live
```

页面发现新消息后提示你加载，并保留阅读位置。此模式仅监听 `127.0.0.1`，每次使用随机访问令牌，检查 Host / Origin，两小时后自动退出。沙箱可能阻止本地服务；默认离线模式不需要这项权限。

## 指定会话或导出

```sh
# 打开指定会话
python3 plugins/codex-history/scripts/history.py open --thread-id 会话UUID

# 读取明确选择的旧版 rollout 文件
python3 plugins/codex-history/scripts/history.py open --file /路径/rollout.jsonl

# 导出可离线阅读的 HTML；不会覆盖已有文件
python3 plugins/codex-history/scripts/history.py export \
  --thread-id 会话UUID --output /保存位置/conversation.html
```

`--home` / `CODEX_HOME` 指定 Codex 数据目录；自定义 SQLite 目录可用 `--sqlite-home`。SSH 用户可以导出并复制 HTML 到本机，或给实时模式使用已有端口转发；本插件不自动建立隧道。

## 常见问题

<details>
<summary><strong>输入 $history 提示 no matches</strong></summary>

尝试完整名称 `$codex-history:history`，并在安装后退出、重开 CLI。用实际聊天时的启动命令检查插件：

```sh
codex plugin list --json
```

如果使用 `codex-jd` 等带独立 `CODEX_HOME` 的启动器，安装时也要使用它。在本仓库目录运行：

```sh
codex-jd plugin marketplace add .
codex-jd plugin add codex-history@personal
```

普通 Codex、桌面端和自定义启动器可能使用不同数据目录，插件不会跨目录自动共享。

</details>

<details>
<summary><strong>输入技能后开始聊天，没有立刻弹出窗口</strong></summary>

技能本来就由模型执行。它会运行附带的本地脚本并返回文件链接；宿主可能阻止自动打开浏览器，此时可以手动打开生成的 HTML。想绕过模型调用，使用上面的可选 `!codex-history` 快捷命令。

</details>

<details>
<summary><strong>已经有另一个叫 personal 的 marketplace</strong></summary>

仓库保留了最初的 `personal` 名称。如果与你已有的另一个 marketplace 冲突，请在注册前，为此克隆的 `.agents/plugins/marketplace.json` 设置唯一名称，并在安装命令的 `@` 后使用该名称。无需删除已有的 marketplace。

</details>

<details>
<summary><strong>能否注册 /history，直接在原生终端跳转？</strong></summary>

检查过的 Codex 版本没有向插件开放原生斜杠命令注册和终端聊天滚动接口。因此本版本的问题选择器和定位在浏览器中。原生终端版本需要上游开放接口，或维护修改后的 CLI。

</details>

<details>
<summary><strong>兼容性和附件有什么限制？</strong></summary>

Codex 内部存储格式不是永久稳定的公共 API。阅读器优先使用 SQLite，兼容旧版 JSONL，并处理重复事件和未写完的末行。进行中的会话可能尚未保存最终回答。缺少 assistant phase 元数据的旧记录无法可靠区分所有过程更新。图片附件显示为占位文字，当前重点是文本、代码和公式阅读。

</details>

## 一起完善它

运行时仅依赖 **Python 标准库和静态页面**。JavaScript 依赖已经固定版本并随插件打包，只有更新渲染资源时才需要 npm。

```sh
python3 -m unittest discover -s tests -v
node --check plugins/codex-history/assets/viewer.js
```

CI 在 Linux、macOS、Windows 上运行测试，覆盖记录解析、会话选择、快照生成、脚本转义、浏览器启动失败和本地服务访问控制。贡献说明和资源重建方法见 [CONTRIBUTING.md](CONTRIBUTING.md) 与 [English README](README.md)。

欢迎贡献新版 Codex 格式兼容、无障碍体验、长会话性能和安装体验改进。Issue 和 PR 请使用合成数据，不要附上私人聊天记录。

如果它帮你省下了翻终端的时间，欢迎点一个 **Star**，让更多 Codex 用户找到它。

---

[MIT 开源协议](LICENSE) · [第三方依赖声明](THIRD_PARTY_NOTICES.md) · 独立社区项目，与 OpenAI 无隶属或官方背书关系。

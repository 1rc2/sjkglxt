# AGENTS.md — 给 AI 开发助手的说明要求

本文件是给 **AI 编码助手**（Claude / Trae / Cursor 等）看的项目规范。任何 AI 在本仓库执行任务前，必须先阅读并遵守以下要求。

## 一、项目是什么

- 大学生竞赛成果管理系统（手机 APP 版）：Python Flask 后端 + 移动端网页界面，可打包为安卓 APK。
- 后端入口：`server.py`（Flask，端口 5000）；数据库封装：`db.py`（pymysql 单例）；建库脚本：`database.sql`。
- 数据库：MySQL，库名 `competition_db`，5 张表（depart / student / competition / award / record）。
- 下载页：`https://1rc2.github.io/` 自动读取本仓库 GitHub Releases，**不要手动改下载页**。

## 二、发布新版本流程（AI 必须遵守）

当用户要求"更新版本 / 发布新版本 / 出新版"时，AI 应按此流程执行：

1. **改代码**：按需求修改 `server.py` / `db.py` / `app/` 下的代码；
2. **打包 APK**：执行 `powershell -ExecutionPolicy Bypass -File android\build_apk.ps1`，产物为根目录 `sjkglxt.apk`；
3. **校验产物**：确认 `sjkglxt.apk` 存在、文件名后缀是 `.apk`、大小合理（正常约 25KB）；
4. **发布 Release**：通过 GitHub API 创建 Release：
   - `tag_name` 遵循 `v主版本.次版本.修订号`（如当前 `v1.0.0`，下个版本应为 `v1.0.1` 或 `v1.1.0`，禁止重复用旧 tag）；
   - `name` 与 tag 相同；`body` 写本次更新说明（改了什么、修了什么）；
   - `prerelease` 必须为 `false`，`draft` 必须为 `false`；
5. **上传资产**：把 `sjkglxt.apk` 作为资产上传到该 Release；
6. **告知用户**：发布成功后说明下载页约 1~10 分钟自动更新，无需改网页。

## 三、代码修改规范

- **禁止改动**：`database.sql` 的初始测试数据与表结构（除非用户明确要求）、`android/` 打包脚本的核心逻辑；
- **数据库连接**：`db.py` 中 `DB_CONFIG` 是本地测试账号（默认 `root / 041632qwe`），改配置时先和用户确认；
- **接口风格**：新增 API 保持现有 REST 风格（JSON 响应、CORS 已开启），登录保持 `admin / admin123` 默认账号；
- **前端**：`app/` 目录配色、布局与原桌面版一致（主色 #4e9acd），新增页面需保持视觉一致；
- **注释**：代码注释用中文；关键逻辑必须写注释。

## 四、安全与操作红线

- **token 是敏感信息**：任何 GitHub Token 严禁写入代码、README、AGENTS.md 或任何被提交的文件；
- **不删除文件**：未获用户明确同意，不得删除仓库内任何文件（含 README、脚本、测试数据）；
- **不覆盖历史**：不得修改已发布的 Release 内容或回退版本号；
- **先确认再动手**：涉及数据库结构变更、打包脚本改动、删除文件等高风险操作，先向用户确认再执行。

## 五、给用户的提醒（AI 每次协助后）

- 发布新版本只需：改代码 → 打包 APK → 在 Releases 上传新版 APK；
- 下载页自动同步，无需改网页代码；
- 旧版本会保留在下载页「历史版本」区。

# 大学生竞赛成果管理系统 —— 手机 APP 版

原项目为 PyQt5 桌面程序，现改写为**手机 APP**：`Python Flask 后端 API + 移动端网页界面`，界面风格、业务逻辑、数据库功能与原桌面版完全一致，并可一键打包为安卓 APK。

---

## 一、系统架构

```
手机浏览器 / 安卓 APP (app/ 目录, 复刻 PyQt5 界面)
        │  HTTP / JSON
        ▼
Python Flask 后端 (server.py, 端口 5000)
        │  复用原数据库逻辑 (db.py)
        ▼
MySQL 数据库 (competition_db, 5 张表)
```

- 后端：`server.py`（登录 / 五表 CRUD / 联合查询 / 统计 / 报表导出）
- 数据库：`db.py` + `database.sql`（原桌面版文件原样保留）
- 界面：`app/` 目录，与桌面版配色、布局、文案一致

## 二、目录结构

```
├── server.py          # Flask 后端 API 服务（主入口，含 CORS）
├── db.py              # 数据库封装（pymysql 单例，原版保留）
├── database.sql       # 建库建表 + 测试数据（原版保留）
├── requirements.txt   # 依赖：flask / pymysql
├── start_server.bat   # 一键启动后端（Windows）
├── sjkglxt.apk        # 已打包好的安卓安装包
├── app/               # 移动端界面
│   ├── index.html     # 页面结构（登录页 / 主界面 / 弹窗）
│   ├── css/style.css  # 样式（复刻 PyQt5 配色）
│   └── js/app.js      # 逻辑（登录/CRUD/查询/图表/导出/服务器配置）
├── android/           # 安卓 APK 打包工程
│   ├── AndroidManifest.xml
│   ├── src/           # WebView 壳源码 (MainActivity.java)
│   ├── build_apk.ps1  # 本机一键打包脚本
│   └── icon_char.txt  # 应用图标文字
└── README.md
```

## 三、环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | 3.8+ | 运行后端 |
| MySQL | 8.0+ | CHECK 约束需 8.0.16+ |
| flask | 2.0+ | Web 服务 |
| pymysql | 1.0+ | MySQL 驱动 |

## 四、部署步骤（在电脑上运行）

### 第 1 步：安装依赖

```bash
pip install flask pymysql -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 第 2 步：确认数据库

- 打开 [db.py](db.py)，按本机 MySQL 修改 `DB_CONFIG`（默认 `root / 041632qwe`）。
- 确保 MySQL 已启动。
- 若数据库 `competition_db` 尚未初始化，执行一次：

```bash
python db.py
```

> 该命令会自动执行 `database.sql`：建库、建 5 张表、导入测试数据。

### 第 3 步：启动后端

双击 `start_server.bat`，或命令行执行：

```bash
python server.py
```

启动成功后会打印手机访问地址，例如：`http://192.168.1.100:5000`

### 第 4 步：手机访问

1. 手机和电脑连接**同一个 Wi-Fi**；
2. 手机浏览器打开 `http://电脑IP:5000`（电脑 IP 见后端启动日志）；
3. 登录：默认账号 `admin`，密码 `admin123`。

> ⚠️ Windows 防火墙：首次启动时如弹出防火墙提示，请勾选"允许访问"，否则手机无法访问 5000 端口。
> 也可以在"控制面板 → Windows Defender 防火墙 → 允许应用通过防火墙"中手动放行 Python。

## 五、功能对照（与原桌面版一致）

| 桌面版功能 | 手机 APP |
|-----------|---------|
| 登录窗口（admin/admin123，回车登录） | 登录页（Enter 键登录） |
| 顶部欢迎栏 | 顶部蓝色栏显示当前用户 |
| 数据管理 Tab：5 张表 CRUD | 底部"数据管理"页，表切换 + 刷新/新增/修改/删除 |
| 多条件联合查询（3 行，= / 包含，AND） | 查询卡片，字段×运算符×值三行 |
| 各院系获奖人数统计（柱状图） | Canvas 柱状图（同配色 #4e9acd） |
| 历年参赛人数统计（折线图） | Canvas 折线图（同配色 #e67e22） |
| 导出统计报表（txt） | 查看 / 一键复制 / 下载 txt |
| 输入校验（学号 10 位、电话 11 位、年份 2000~2026 等） | 前后端双重校验 |
| 外键约束删除保护提示 | 删除被引用记录时明确提示 |

5 张表：院系表 depart、学生表 student、竞赛表 competition、奖项表 award、参赛记录表 record。

## 六、打包成安卓 APK

**方式一：本机一键打包（已测试通过，推荐）**

本机已具备 Android SDK 时，直接在项目目录执行：

```bash
powershell -ExecutionPolicy Bypass -File android\build_apk.ps1
```

脚本自动完成：复制界面资源 → 生成图标 → 资源编译 → Java 编译 → 打包 → 签名，
产物为项目根目录 `sjkglxt.apk`（约 25KB），可直接安装到安卓手机。

APK 特点：
- 界面资源内置在 APK（离线加载，秒开）；
- 首次打开会弹出"服务器设置"，填写电脑端地址（如 `http://192.168.1.247:5000`），
  数据即走该后端访问 MySQL（登录页左下角 ⚙ 服务器设置 可随时修改）；
- 已加 CORS 支持，APK 内页面可跨源访问后端 API。

**方式二：HBuilderX 云打包（免本机环境）**

1. 下载安装 [HBuilderX](https://www.dcloud.io/hbuilderx.html)（免费）；
2. 新建项目：`文件 → 新建 → 项目`，模板选 **5+ App（HTML5+）**，名称如 `sjkglxt`；
3. 将本仓库 `app/` 下的 `index.html`、`css/`、`js/` 复制到项目根目录（覆盖原文件）；
4. 打开 `manifest.json`：填写应用名称（如"竞赛成果管理系统"）、设置应用图标；
5. 点击菜单 `发行 → 原生App-云打包`，选择 **Android**，证书选"使用公共测试证书"，点打包；
6. 打包完成后下载 APK，安装到手机即可。

> 说明：无论哪种方式，正式使用建议将后端部署到云服务器，并在 APP 的服务器设置中改为服务器域名。
> 手机与电脑需同一局域网；Windows 防火墙需放行 5000 端口。

## 七、数据恢复

清空数据恢复初始测试状态：

```bash
python db.py   # 重新执行 database.sql（会重建全部表与测试数据）
```

## 八、上传到 GitHub（操作步骤）

在项目目录（本仓库根目录）打开命令行：

```bash
# 1. 初始化仓库（若尚未初始化）
git init

# 2. 添加全部文件到暂存区
git add .

# 3. 提交（修改为自己的信息）
git commit -m "大学生竞赛成果管理系统 - 手机APP版"

# 4. 关联远程仓库（替换为你的仓库地址）
git remote add origin https://github.com/你的用户名/sjkglxt.git

# 5. 推送到 GitHub（首次推送加 -u）
git push -u origin main
```

若已配置过远程仓库，直接执行 `git add . && git commit -m "..." && git push` 即可。

**私有仓库方式（推荐，密码不复用）**：
GitHub → 你的仓库 → Settings → Developer settings → Personal access tokens → 生成 token（勾选 `repo` 权限），推送时用：

```bash
git push https://<你的用户名>:<token>@github.com/你的用户名/sjkglxt.git main
```

> ⚠️ token 等同密码，切勿提交到代码仓库或分享给他人。

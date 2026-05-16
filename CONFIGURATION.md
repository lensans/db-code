# 配置文档

> 寻根溯源族谱管理系统 — 环境变量、数据库连接、脚本参数与启动方式说明

---

## 目录

1. [环境变量](#1-环境变量)
2. [启动脚本参数](#2-启动脚本参数)
3. [数据库配置](#3-数据库配置)
4. [数据初始化配置](#4-数据初始化配置)
5. [PostgreSQL 导入脚本配置](#5-postgresql-导入脚本配置)
6. [应用参数说明](#6-应用参数说明)
7. [配置速查表](#7-配置速查表)

---

## 1. 环境变量

系统主要通过环境变量配置，默认不需要修改源码。

| 变量名 | 说明 | 默认值 | 是否必填 |
|---|---|---|---|
| `SECRET_KEY` | Flask Session 加密密钥 | `dev-secret-key` | 生产环境必填 |
| `DATABASE_URL` | SQLAlchemy 数据库连接串 | `sqlite:///genealogy_demo.db` | 否 |
| `FLASK_APP` | Flask 入口文件 | `app.py` | 启动脚本会自动设置 |
| `FLASK_DEBUG` | 调试模式，`1` 开启，`0` 关闭 | `0` | 否 |
| `APP_MODE` | 应用模式标记，可用 `demo` / `full` | `demo` | 否 |

PowerShell 临时设置示例：

```powershell
$env:SECRET_KEY = "change-this-secret"
$env:DATABASE_URL = "postgresql+psycopg2://postgres@localhost:5432/genealogy_db"
$env:FLASK_APP = "app.py"
$env:FLASK_DEBUG = "0"
```

---

## 2. 启动脚本参数

项目提供 `start_app.ps1`，用于统一设置环境变量并启动 Flask。

```powershell
powershell -ExecutionPolicy Bypass -File .\start_app.ps1 `
  -BindHost "127.0.0.1" `
  -Port 5000 `
  -SecretKey "dev-key" `
  -DatabaseUrl "" `
  -Debug
```

| 参数 | 说明 | 默认值 |
|---|---|---|
| `BindHost` | Flask 监听地址 | `127.0.0.1` |
| `Port` | Flask 监听端口 | `5000` |
| `SecretKey` | 写入 `SECRET_KEY` 环境变量 | `dev-key` |
| `DatabaseUrl` | 写入 `DATABASE_URL`，为空则使用 SQLite | 空字符串 |
| `Debug` | 是否开启 Flask Debug | 关闭 |

停止服务：

```powershell
powershell -ExecutionPolicy Bypass -File .\stop_app.ps1 -Port 5000
```

---

## 3. 数据库配置

### 3.1 SQLite 默认配置

不设置 `DATABASE_URL` 时，应用使用：

```text
sqlite:///genealogy_demo.db
```

Flask-SQLAlchemy 会将相对 SQLite 数据库放在 `instance/` 目录下，因此实际文件通常是：

```text
instance/genealogy_demo.db
```

适用场景：

- 快速演示
- 本地开发
- 不安装 PostgreSQL 的课堂展示

### 3.2 PostgreSQL 配置

PostgreSQL 连接串格式：

```text
postgresql+psycopg2://用户名:密码@主机:端口/数据库名
```

无密码本机示例：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_app.ps1 `
  -DatabaseUrl "postgresql+psycopg2://postgres@localhost:5432/genealogy_db"
```

带密码示例：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_app.ps1 `
  -DatabaseUrl "postgresql+psycopg2://postgres:postgres@localhost:5432/genealogy_db"
```

---

## 4. 数据初始化配置

### 4.1 SQLite 演示数据

执行：

```powershell
python seed_demo_data.py
```

脚本会清空当前数据库中的业务表并重新生成演示数据。

当前参数在 `seed_demo_data.py` 中：

```python
SURNAMES = ["王", "李", "张", "赵", "刘", "陈", "杨", "黄", "周", "吴"]

genealogy_specs = [
    (f"{surname}氏演示族谱", surname, 2020 + index, 30, 34)
    for index, surname in enumerate(SURNAMES, start=1)
]
```

| 参数 | 当前值 | 说明 |
|---|---:|---|
| 族谱数量 | 10 | 10 个姓氏 |
| 每个族谱代数 | 30 | 满足多代传承演示 |
| 每代成员数 | 34 | 每族 1020 人 |
| 总成员数 | 10200 | 适合浏览器演示 |

### 4.2 交付数据生成脚本

课程交付数据生成脚本位于：

```text
交付物/scripts/generate_data.py
```

生成结果位于：

```text
交付物/data/generated_demo
交付物/data/generated_full
```

其中 `generated_full` 已包含 100000 名成员，用于 PostgreSQL 批量导入与性能测试。

---

## 5. PostgreSQL 导入脚本配置

导入脚本：

```text
import_generated_full.ps1
```

完整参数：

```powershell
powershell -ExecutionPolicy Bypass -File .\import_generated_full.ps1 `
  -PsqlPath "psql" `
  -Database "genealogy_db" `
  -Username "postgres" `
  -DataDir ".\交付物\data\generated_full" `
  -SkipIndexes:$false
```

| 参数 | 说明 | 默认值 |
|---|---|---|
| `PsqlPath` | `psql` 可执行文件路径 | `psql` |
| `Database` | 目标数据库名 | `genealogy_db` |
| `Username` | PostgreSQL 用户名 | `postgres` |
| `DataDir` | CSV 数据目录 | `交付物/data/generated_full` |
| `SkipIndexes` | 是否跳过索引创建 | 不跳过 |

如果 `psql` 不在 PATH 中，可传绝对路径：

```powershell
powershell -ExecutionPolicy Bypass -File .\import_generated_full.ps1 `
  -PsqlPath "$env:USERPROFILE\scoop\apps\postgresql\current\bin\psql.exe"
```

---

## 6. 应用参数说明

### 6.1 分页大小

成员列表分页大小在 `genealogy_app/routes.py`：

```python
PAGE_SIZE = 50
```

如果希望每页显示更多成员，可调整为 `100`。不建议在大数据模式下设置过大。

### 6.2 树状展示最大层数

族谱树预览路由限制最大展开层数：

```python
max_depth = min(max(max_depth, 1), 5)
```

这样可以避免一次渲染过多节点导致浏览器卡顿。

### 6.3 成员搜索候选数

成员选择下拉接口默认最多返回 30 条，最大 50 条：

```python
limit = min(max(request.args.get("limit", default=30, type=int), 1), 50)
```

适用位置：

- 新增成员时选择父亲、母亲、配偶
- 关系维护
- 树状展示选择根成员
- 祖先查询
- 亲缘路径查询

### 6.4 亲缘路径查询

亲缘路径查询位于 `genealogy_app/services.py` 的 `find_kinship_path`。它会基于亲子关系和婚姻关系构建图并执行 BFS。

大数据场景下建议：

- 先通过姓名搜索确认成员
- 使用较小范围的演示族谱做课堂演示
- 如需继续优化，可将 BFS 改为按需查询邻接点，而不是一次加载全族谱关系

---

## 7. 配置速查表

| 场景 | 命令 |
|---|---|
| 安装依赖 | `python -m pip install -r requirements.txt` |
| 初始化演示数据 | `python seed_demo_data.py` |
| SQLite 启动 | `powershell -ExecutionPolicy Bypass -File .\start_app.ps1` |
| PostgreSQL 启动 | `powershell -ExecutionPolicy Bypass -File .\start_app.ps1 -DatabaseUrl "postgresql+psycopg2://postgres@localhost:5432/genealogy_db"` |
| 停止服务 | `powershell -ExecutionPolicy Bypass -File .\stop_app.ps1` |
| 导入 10 万级数据 | `powershell -ExecutionPolicy Bypass -File .\import_generated_full.ps1 -Database genealogy_db -Username postgres` |
| 默认访问地址 | `http://127.0.0.1:5000` |
| 演示账号 | `demo / demo123` |

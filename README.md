# 寻根溯源 · 族谱管理系统

> 数据库课程大作业  
> 后端框架：Python Flask + Flask-SQLAlchemy  
> 数据库：SQLite（本地演示默认）/ PostgreSQL（课程交付与大数据导入）

---

## 目录

1. [项目概述](#1-项目概述)
2. [功能说明](#2-功能说明)
3. [系统架构](#3-系统架构)
4. [数据库设计](#4-数据库设计)
5. [目录结构](#5-目录结构)
6. [环境准备](#6-环境准备)
7. [快速启动](#7-快速启动)
8. [演示账号与演示数据](#8-演示账号与演示数据)
9. [SQL 查询说明](#9-sql-查询说明)
10. [索引优化说明](#10-索引优化说明)
11. [PostgreSQL 大数据导入](#11-postgresql-大数据导入)
12. [页面访问说明](#12-页面访问说明)
13. [常见问题](#13-常见问题)

---

## 1. 项目概述

**寻根溯源**是一套族谱管理系统，支持多用户、多族谱、成员维护、亲属关系维护、树状族谱展示、祖先追溯和亲缘路径查询。

项目默认使用 SQLite，方便任何人从 Git 仓库克隆后快速启动；如需展示课程要求的大规模数据，可切换到 PostgreSQL 并导入 `交付物/data/generated_full` 中的 10 万级 CSV 数据。

---

## 2. 功能说明

- 用户注册、登录、退出
- 创建族谱、删除族谱、邀请协作者
- 成员新增、编辑、删除、分页展示
- 新增成员时直接录入父亲、母亲、配偶关系
- 成员选择支持输入姓名搜索，不需要手动输入成员 ID
- 亲子关系、婚姻关系维护
- 族谱树状展示，支持选择根成员和展示层数
- 祖先查询
- 两名成员之间的亲缘路径查询
- 演示数据：10 个族谱，每个族谱 1020 人，合计 10200 人
- 交付数据：10 个族谱，合计 100000 名成员，其中最大单族谱 50000 人

---

## 3. 系统架构

```text
浏览器
  │ HTTP
  ▼
Flask 路由层 genealogy_app/routes.py
  │
  ├─ Jinja2 模板 templates/
  │
  ├─ 业务查询 genealogy_app/services.py
  │
  ▼
SQLAlchemy ORM
  │
  ├─ SQLite: instance/genealogy_demo.db
  └─ PostgreSQL: genealogy_db
```

---

## 4. 数据库设计

### 4.1 ER 概述

系统围绕“用户 - 族谱 - 成员 - 亲属关系”建模，核心实体和关系如下：

| 表名 | 含义 |
|---|---|
| `users` | 系统用户，用于注册、登录和族谱所有权 |
| `genealogies` | 族谱主表，记录族谱名称、姓氏、修谱年份和创建者 |
| `genealogy_collaborators` | 用户与族谱的协作关系表 |
| `members` | 族谱成员表，记录姓名、性别、生卒年、代际和简介 |
| `parent_child_relations` | 亲子关系表，记录父亲/母亲到子女的关系 |
| `marriages` | 婚姻关系表，记录配偶双方 |

### 4.2 表结构说明

```sql
users(user_id, username, password_hash, created_at)

genealogies(genealogy_id, title, surname, revision_year,
            owner_user_id, created_at)

genealogy_collaborators(id, genealogy_id, user_id, role)

members(member_id, genealogy_id, name, gender, birth_year,
        death_year, biography, generation_no)

parent_child_relations(relation_id, genealogy_id, parent_id,
                       child_id, parent_type)

marriages(marriage_id, genealogy_id, spouse1_id,
          spouse2_id, married_year)
```

完整建表脚本位于：

```text
交付物/sql/schema.sql
```

### 4.3 主外键设计

| 表 | 主键 | 关键外键 |
|---|---|---|
| `users` | `user_id` | 无 |
| `genealogies` | `genealogy_id` | `owner_user_id -> users.user_id` |
| `genealogy_collaborators` | `id` | `genealogy_id -> genealogies.genealogy_id`, `user_id -> users.user_id` |
| `members` | `member_id` | `genealogy_id -> genealogies.genealogy_id` |
| `parent_child_relations` | `relation_id` | `parent_id -> members.member_id`, `child_id -> members.member_id` |
| `marriages` | `marriage_id` | `spouse1_id -> members.member_id`, `spouse2_id -> members.member_id` |

### 4.4 约束与数据一致性

数据库层包含以下约束：

- `users.username` 唯一，避免重复账号。
- `genealogy_collaborators(genealogy_id, user_id)` 唯一，避免重复协作邀请。
- `members.gender` 限制为 `M` 或 `F`。
- `members.death_year` 必须为空，或不早于 `birth_year`。
- `parent_child_relations.parent_id <> child_id`，避免自己成为自己的父母。
- `marriages.spouse1_id <> spouse2_id`，避免自己与自己结婚。
- `parent_child_relations(genealogy_id, parent_id, child_id, parent_type)` 唯一，避免重复亲子关系。
- `marriages(genealogy_id, spouse1_id, spouse2_id)` 唯一，避免重复婚姻关系。

### 4.5 触发器设计

触发器脚本位于：

```text
交付物/sql/triggers.sql
```

触发器负责补充复杂约束：

| 触发器 | 作用 |
|---|---|
| `trg_validate_parent_child` | 校验父母和子女存在、属于同一族谱、父亲必须为男、母亲必须为女、父母出生年早于子女 |
| `trg_validate_marriage` | 校验配偶双方存在且属于同一族谱 |

### 4.6 范式说明

系统表结构满足第三范式：

- 用户、族谱、成员、关系表职责分离。
- 成员基本信息只存放在 `members` 表中。
- 亲子关系和婚姻关系单独建表，避免在成员表中重复存储多个父母或配偶字段。
- 协作者关系通过中间表建模，支持多用户协作同一族谱。

---

## 5. 目录结构

```text
.
├── app.py                         # Flask 入口
├── requirements.txt               # Python 依赖
├── start_app.ps1                  # Windows 一键启动脚本
├── stop_app.ps1                   # Windows 停止服务脚本
├── seed_demo_data.py              # SQLite 演示数据初始化脚本
├── import_generated_full.ps1      # PostgreSQL 大数据导入脚本
├── CONFIGURATION.md               # 配置文档
├── genealogy_app/
│   ├── __init__.py                # Flask 应用工厂与配置
│   ├── models.py                  # 数据模型
│   ├── routes.py                  # 页面路由与表单处理
│   └── services.py                # 查询服务
├── templates/                     # 页面模板
└── 交付物/
    ├── sql/                       # 建表、索引、触发器、查询 SQL
    ├── scripts/                   # 数据生成脚本
    ├── data/                      # generated_demo / generated_full CSV
    ├── report/                    # 实验报告与性能记录
    └── export/                    # 导入导出与备份示例
```

---

## 6. 环境准备

### 6.1 Python

推荐 Python 3.10 及以上。

```powershell
python --version
```

### 6.2 安装依赖

```powershell
python -m pip install -r requirements.txt
```

依赖包括：

| 依赖 | 用途 |
|---|---|
| Flask | Web 应用框架 |
| Flask-SQLAlchemy | ORM 与数据库连接 |
| psycopg2-binary | PostgreSQL 驱动 |

### 6.3 PostgreSQL（可选）

如果只运行本地演示，可以不安装 PostgreSQL，默认会使用 SQLite。

如果需要导入 10 万级交付数据，请先安装 PostgreSQL，并确保 `psql` 可用：

```powershell
psql --version
```

---

## 7. 快速启动

### 7.1 推荐方式：一键启动

```powershell
powershell -ExecutionPolicy Bypass -File .\start_app.ps1
```

启动后访问：

```text
http://127.0.0.1:5000
```

### 7.2 停止服务

```powershell
powershell -ExecutionPolicy Bypass -File .\stop_app.ps1
```

### 7.3 手动启动

```powershell
$env:FLASK_APP = "app.py"
python -m flask run --host 127.0.0.1 --port 5000
```

---

## 8. 演示账号与演示数据

默认演示账号：

```text
用户名：demo
密码：demo123
```

如需重新生成 SQLite 演示数据：

```powershell
python seed_demo_data.py
```

当前脚本会生成：

| 项目 | 数量 |
|---|---:|
| 用户 | 1 |
| 族谱 | 10 |
| 成员 | 10200 |
| 每个族谱成员 | 1020 |
| 每个族谱代数 | 30 |

---

## 9. SQL 查询说明

课程查询 SQL 位于：

```text
交付物/sql/queries.sql
```

### 9.1 查询 1：给定成员的配偶和所有子女

用途：展示成员的一度亲属关系。

实现思路：

- 从 `marriages` 中查找配偶。
- 从 `parent_child_relations` 中查找子女。
- 使用 `UNION ALL` 合并两类结果。

核心参数：

```sql
:member_id
```

### 9.2 查询 2：递归查询所有祖先

用途：查询某个成员的全部祖先链。

实现思路：

- 使用 PostgreSQL `WITH RECURSIVE`。
- 从当前成员的父母开始递归向上追溯。
- 返回祖先成员 ID、姓名和深度。

核心参数：

```sql
:member_id
```

### 9.3 查询 3：平均寿命最长的一代人

用途：统计各代成员寿命差异。

实现思路：

- 过滤 `death_year IS NOT NULL` 的成员。
- 按 `generation_no` 分组。
- 计算 `AVG(death_year - birth_year)`。
- 按平均寿命倒序取第一名。

### 9.4 查询 4：年龄超过 50 岁且没有配偶的男性成员

用途：组合过滤与反连接查询。

实现思路：

- `members.gender = 'M'`。
- 当前年份减出生年大于 50。
- 使用 `NOT EXISTS` 排除出现在婚姻关系中的成员。

### 9.5 查询 5：出生年份早于本代平均出生年份的成员

用途：展示分组统计和成员明细联查。

实现思路：

- 先按 `generation_no` 计算平均出生年。
- 再与 `members` 连接。
- 找出 `birth_year < avg_birth_year` 的成员。

### 9.6 查询 6：四代后代查询

用途：作为性能测试查询，用于索引前后对比。

实现思路：

- 使用 `WITH RECURSIVE` 从根成员向下递归查找后代。
- 限制 `depth < 4`。
- 最终返回第 4 代后代。

核心参数：

```sql
:root_member_id
```

---

## 10. 索引优化说明

索引脚本位于：

```text
交付物/sql/indexes.sql
```

### 10.1 索引设计目标

系统数据规模可达到 10 万名成员，主要性能压力来自：

- 按族谱和姓名搜索成员。
- 按族谱和代际筛选成员。
- 亲子关系中按父母查子女。
- 祖先查询中按子女查父母。
- 婚姻关系中按任一配偶查另一方。
- 模糊姓名查询。

### 10.2 已建立索引

| 索引名 | 表 | 字段 | 优化场景 |
|---|---|---|---|
| `idx_members_genealogy_name` | `members` | `(genealogy_id, name)` | 族谱内姓名查询 |
| `idx_members_generation` | `members` | `(genealogy_id, generation_no)` | 按代际统计与筛选 |
| `idx_parent_child_parent` | `parent_child_relations` | `(genealogy_id, parent_id)` | 查询某成员子女、后代递归 |
| `idx_parent_child_child` | `parent_child_relations` | `(genealogy_id, child_id)` | 查询某成员父母、祖先递归 |
| `idx_marriages_spouse1` | `marriages` | `(genealogy_id, spouse1_id)` | 按配偶 1 查婚姻 |
| `idx_marriages_spouse2` | `marriages` | `(genealogy_id, spouse2_id)` | 按配偶 2 查婚姻 |
| `idx_members_name_trgm` | `members` | `name gin_trgm_ops` | PostgreSQL 模糊姓名搜索 |

### 10.3 为什么需要组合索引

系统几乎所有成员和关系查询都限定在某个族谱内，因此索引首列使用 `genealogy_id`。这样可以先缩小到单个族谱，再查姓名、代际、父母或配偶，避免扫描全系统 10 万成员。

示例：

```sql
SELECT *
FROM members
WHERE genealogy_id = :genealogy_id
  AND name ILIKE '%' || :keyword || '%';
```

### 10.4 递归查询优化

祖先查询依赖：

```sql
parent_child_relations(genealogy_id, child_id)
```

后代查询依赖：

```sql
parent_child_relations(genealogy_id, parent_id)
```

这两个方向都需要索引，因为祖先查询和后代查询的连接方向相反。

### 10.5 模糊搜索优化

PostgreSQL 默认 B-tree 索引不适合 `%关键字%` 形式的模糊查询，因此脚本启用 `pg_trgm`：

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_members_name_trgm
    ON members USING gin (name gin_trgm_ops);
```

这样可以提升成员姓名搜索的响应速度，适合前端“输入姓名搜索成员”的下拉选择器。

### 10.6 性能测试建议

可使用以下步骤对比索引效果：

1. 导入 `generated_full` 10 万级数据。
2. 暂不执行 `indexes.sql`，运行 `queries.sql` 中第 6 个四代后代查询并记录耗时。
3. 执行 `交付物/sql/indexes.sql`。
4. 再次运行同一查询并记录耗时。
5. 使用 `EXPLAIN ANALYZE` 对比执行计划是否从顺序扫描变为索引扫描。

---

## 11. PostgreSQL 大数据导入

### 11.1 创建数据库

```powershell
createdb -U postgres genealogy_db
```

如果数据库已存在，可先删除再重建：

```powershell
dropdb -U postgres genealogy_db
createdb -U postgres genealogy_db
```

### 11.2 导入 10 万级数据

```powershell
powershell -ExecutionPolicy Bypass -File .\import_generated_full.ps1 `
  -PsqlPath "psql" `
  -Database "genealogy_db" `
  -Username "postgres"
```

脚本会自动执行：

- `交付物/sql/schema.sql`
- `交付物/sql/triggers.sql`
- CSV 批量导入
- `交付物/sql/sequence_sync.sql`
- `交付物/sql/indexes.sql`
- 导入结果校验 SQL

### 11.3 使用 PostgreSQL 启动应用

```powershell
powershell -ExecutionPolicy Bypass -File .\start_app.ps1 `
  -DatabaseUrl "postgresql+psycopg2://postgres@localhost:5432/genealogy_db"
```

---

## 12. 页面访问说明

| 页面 | 地址 |
|---|---|
| 登录页 | `http://127.0.0.1:5000/login` |
| 控制台 | `http://127.0.0.1:5000/dashboard` |
| 族谱详情 | `http://127.0.0.1:5000/genealogies/1` |
| 树状展示 | `http://127.0.0.1:5000/genealogies/1/tree` |
| 姓名查询 | `http://127.0.0.1:5000/genealogies/1/search` |
| 祖先查询 | `http://127.0.0.1:5000/genealogies/1/ancestors` |
| 亲缘路径 | `http://127.0.0.1:5000/genealogies/1/kinship` |

---

## 13. 常见问题

### 13.1 页面没有演示数据

执行：

```powershell
python seed_demo_data.py
```

然后重新启动服务。

### 13.2 端口 5000 被占用

执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\stop_app.ps1
```

或改用其他端口：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_app.ps1 -Port 5001
```

### 13.3 大数据页面卡顿

系统已经避免默认渲染完整 10 万级族谱树：

- 成员列表分页展示
- 成员选择通过搜索接口动态加载
- 树状展示限制最大展开层数
- 搜索结果分页返回

如需演示大数据能力，建议使用 PostgreSQL 数据库并通过分页、搜索、树状预览进行展示。

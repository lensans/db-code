# 寻根溯源族谱管理系统 ER 图

> 本图对应 PostgreSQL 建表脚本 `交付物/sql/schema.sql`，覆盖用户、族谱、协作者、成员、亲子关系和婚姻关系。

```mermaid
erDiagram
    users ||--o{ genealogies : creates
    users ||--o{ genealogy_collaborators : joins
    genealogies ||--o{ genealogy_collaborators : has
    genealogies ||--o{ members : contains
    genealogies ||--o{ parent_child_relations : owns
    genealogies ||--o{ marriages : owns
    members ||--o{ parent_child_relations : parent
    members ||--o{ parent_child_relations : child
    members ||--o{ marriages : spouse1
    members ||--o{ marriages : spouse2

    users {
        int user_id PK
        varchar username UK
        varchar password_hash
        timestamp created_at
    }

    genealogies {
        int genealogy_id PK
        varchar title
        varchar surname
        int revision_year
        int owner_user_id FK
        timestamp created_at
    }

    genealogy_collaborators {
        int id PK
        int genealogy_id FK
        int user_id FK
        varchar role
    }

    members {
        int member_id PK
        int genealogy_id FK
        varchar name
        char gender
        int birth_year
        int death_year
        text biography
        int generation_no
    }

    parent_child_relations {
        int relation_id PK
        int genealogy_id FK
        int parent_id FK
        int child_id FK
        varchar parent_type
    }

    marriages {
        int marriage_id PK
        int genealogy_id FK
        int spouse1_id FK
        int spouse2_id FK
        int married_year
    }
```

## 关系说明

| 关系 | 类型 | 说明 |
|---|---|---|
| `users -> genealogies` | `1:N` | 一个用户可以创建多个族谱，一个族谱只有一个创建者 |
| `users -> genealogy_collaborators <- genealogies` | `M:N` | 用户可被邀请协作多个族谱，一个族谱也可有多个协作者 |
| `genealogies -> members` | `1:N` | 一个族谱包含多个成员，每个成员只属于一个族谱 |
| `members -> parent_child_relations` | `1:N` | 一个成员可以作为多个亲子关系中的父母或子女 |
| `members -> marriages` | `1:N` | 一个成员可以出现在婚姻关系的任一配偶字段中 |

## 主要约束

| 约束 | 说明 |
|---|---|
| `users.username UNIQUE` | 用户名唯一 |
| `genealogy_collaborators(genealogy_id, user_id) UNIQUE` | 避免重复协作关系 |
| `members.gender IN ('M', 'F')` | 性别取值约束 |
| `members.death_year IS NULL OR birth_year <= death_year` | 生卒年合法性 |
| `parent_child_relations.parent_id <> child_id` | 禁止自己成为自己的父母 |
| `marriages.spouse1_id <> spouse2_id` | 禁止自己与自己建立婚姻 |
| `trg_validate_parent_child` | 校验父母性别、同族谱、出生年早于子女 |
| `trg_validate_marriage` | 校验配偶存在且同族谱 |

# PostgreSQL 备份与恢复命令

## 1. 导出整库 SQL

```powershell
pg_dump -U postgres -d genealogy_db -f 交付物/export/genealogy_db_schema.sql
```

## 2. 导出自定义格式备份

```powershell
pg_dump -U postgres -d genealogy_db -Fc -f 交付物/export/genealogy_db_full.backup
```

## 3. 从 SQL 文件恢复

```powershell
psql -U postgres -d genealogy_db -f 交付物/export/genealogy_db_schema.sql
```

## 4. 从自定义格式恢复

```powershell
pg_restore -U postgres -d genealogy_db 交付物/export/genealogy_db_full.backup
```

## 5. 说明

- 若只需要提交命令说明，本文件即可作为交付材料的一部分。
- 若需要真实备份文件，请在本目录补充实际导出产物。

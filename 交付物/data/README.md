# 数据目录说明

本目录用于存放生成后的 CSV 数据文件。

## 当前建议内容

- `generated_demo/`
  用于 GUI 演示的小规模数据集。
- `generated_full/`
  用于满足课程要求的 10 万级数据集。

## 导入顺序

1. `users.csv`
2. `genealogies.csv`
3. `members.csv`
4. `parent_child_relations.csv`
5. `marriages.csv`
6. 执行 `../sql/sequence_sync.sql`

## 注意事项

- CSV 编码为 `utf-8-sig`。
- 文件已显式包含主键列，适合 `COPY` 导入。
- 若重新生成数据，建议删除旧目录后再生成，以免混用不同批次文件。

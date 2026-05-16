-- 导出指定根成员分支下的全部成员
COPY (
    WITH RECURSIVE branch AS (
        SELECT child_id AS member_id
        FROM parent_child_relations
        WHERE parent_id = 1
        UNION ALL
        SELECT r.child_id
        FROM parent_child_relations r
        JOIN branch b ON r.parent_id = b.member_id
    )
    SELECT m.*
    FROM members m
    WHERE m.member_id IN (SELECT member_id FROM branch)
) TO '/path/to/branch_export.csv'
WITH (FORMAT csv, HEADER true);

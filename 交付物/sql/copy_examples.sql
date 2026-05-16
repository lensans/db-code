-- 导入 users
COPY users(user_id, username, password_hash, created_at)
FROM '/path/to/users.csv'
WITH (FORMAT csv, HEADER true);

-- 导入 genealogies
COPY genealogies(genealogy_id, title, surname, revision_year, owner_user_id, created_at)
FROM '/path/to/genealogies.csv'
WITH (FORMAT csv, HEADER true);

-- 导入 members
COPY members(member_id, genealogy_id, name, gender, birth_year, death_year, biography, generation_no)
FROM '/path/to/members.csv'
WITH (FORMAT csv, HEADER true);

-- 导入 parent_child_relations
COPY parent_child_relations(genealogy_id, parent_id, child_id, parent_type)
FROM '/path/to/parent_child_relations.csv'
WITH (FORMAT csv, HEADER true);

-- 导入 marriages
COPY marriages(genealogy_id, spouse1_id, spouse2_id, married_year)
FROM '/path/to/marriages.csv'
WITH (FORMAT csv, HEADER true);

-- 导出某一分支成员备份
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
) TO '/path/to/branch_backup.csv'
WITH (FORMAT csv, HEADER true);

-- 1. 给定成员 ID，查询其配偶及所有子女
WITH spouse_info AS (
    SELECT m2.member_id, m2.name, 'spouse' AS relation_type
    FROM marriages ma
    JOIN members m2 ON m2.member_id = CASE
        WHEN ma.spouse1_id = :member_id THEN ma.spouse2_id
        ELSE ma.spouse1_id
    END
    WHERE :member_id IN (ma.spouse1_id, ma.spouse2_id)
),
child_info AS (
    SELECT c.member_id, c.name, 'child' AS relation_type
    FROM parent_child_relations r
    JOIN members c ON c.member_id = r.child_id
    WHERE r.parent_id = :member_id
)
SELECT * FROM spouse_info
UNION ALL
SELECT * FROM child_info;

-- 2. 递归查询所有祖先
WITH RECURSIVE ancestor_tree AS (
    SELECT parent_id, child_id, 1 AS depth
    FROM parent_child_relations
    WHERE child_id = :member_id
    UNION ALL
    SELECT r.parent_id, r.child_id, at.depth + 1
    FROM parent_child_relations r
    JOIN ancestor_tree at ON r.child_id = at.parent_id
)
SELECT at.parent_id, m.name, at.depth
FROM ancestor_tree at
JOIN members m ON m.member_id = at.parent_id
ORDER BY at.depth, at.parent_id;

-- 3. 平均寿命最长的一代人
SELECT
    generation_no,
    AVG(death_year - birth_year) AS avg_lifespan
FROM members
WHERE death_year IS NOT NULL
GROUP BY generation_no
ORDER BY avg_lifespan DESC
LIMIT 1;

-- 4. 年龄超过 50 岁且没有配偶的男性成员
SELECT m.*
FROM members m
WHERE m.gender = 'M'
  AND EXTRACT(YEAR FROM CURRENT_DATE) - m.birth_year > 50
  AND NOT EXISTS (
      SELECT 1
      FROM marriages ma
      WHERE m.member_id IN (ma.spouse1_id, ma.spouse2_id)
  );

-- 5. 出生年份早于本代平均出生年份的成员
WITH generation_avg AS (
    SELECT generation_no, AVG(birth_year) AS avg_birth_year
    FROM members
    GROUP BY generation_no
)
SELECT m.*
FROM members m
JOIN generation_avg g ON g.generation_no = m.generation_no
WHERE m.birth_year < g.avg_birth_year
ORDER BY m.generation_no, m.birth_year;

-- 6. 查询某曾祖父的所有曾孙（四代查询），用于性能对比
WITH RECURSIVE descendants AS (
    SELECT parent_id, child_id, 1 AS depth
    FROM parent_child_relations
    WHERE parent_id = :root_member_id
    UNION ALL
    SELECT r.parent_id, r.child_id, d.depth + 1
    FROM parent_child_relations r
    JOIN descendants d ON r.parent_id = d.child_id
    WHERE d.depth < 4
)
SELECT d.depth, m.member_id, m.name
FROM descendants d
JOIN members m ON m.member_id = d.child_id
WHERE d.depth = 4;

CREATE INDEX IF NOT EXISTS idx_members_genealogy_name
    ON members (genealogy_id, name);

CREATE INDEX IF NOT EXISTS idx_members_generation
    ON members (genealogy_id, generation_no);

CREATE INDEX IF NOT EXISTS idx_parent_child_parent
    ON parent_child_relations (genealogy_id, parent_id);

CREATE INDEX IF NOT EXISTS idx_parent_child_child
    ON parent_child_relations (genealogy_id, child_id);

CREATE INDEX IF NOT EXISTS idx_marriages_spouse1
    ON marriages (genealogy_id, spouse1_id);

CREATE INDEX IF NOT EXISTS idx_marriages_spouse2
    ON marriages (genealogy_id, spouse2_id);

-- 若启用 PostgreSQL pg_trgm 扩展，可支持更好的模糊查询性能
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_members_name_trgm
    ON members USING gin (name gin_trgm_ops);

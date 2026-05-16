DROP TABLE IF EXISTS marriages CASCADE;
DROP TABLE IF EXISTS parent_child_relations CASCADE;
DROP TABLE IF EXISTS members CASCADE;
DROP TABLE IF EXISTS genealogy_collaborators CASCADE;
DROP TABLE IF EXISTS genealogies CASCADE;
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE genealogies (
    genealogy_id SERIAL PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    surname VARCHAR(50) NOT NULL,
    revision_year INTEGER,
    owner_user_id INTEGER NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE genealogy_collaborators (
    id SERIAL PRIMARY KEY,
    genealogy_id INTEGER NOT NULL REFERENCES genealogies(genealogy_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL DEFAULT 'editor',
    CONSTRAINT uq_genealogy_collaborator UNIQUE (genealogy_id, user_id)
);

CREATE TABLE members (
    member_id SERIAL PRIMARY KEY,
    genealogy_id INTEGER NOT NULL REFERENCES genealogies(genealogy_id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    gender CHAR(1) NOT NULL CHECK (gender IN ('M', 'F')),
    birth_year INTEGER NOT NULL,
    death_year INTEGER,
    biography TEXT,
    generation_no INTEGER NOT NULL CHECK (generation_no >= 1),
    CONSTRAINT chk_member_years CHECK (
        death_year IS NULL OR birth_year <= death_year
    )
);

CREATE TABLE parent_child_relations (
    relation_id SERIAL PRIMARY KEY,
    genealogy_id INTEGER NOT NULL REFERENCES genealogies(genealogy_id) ON DELETE CASCADE,
    parent_id INTEGER NOT NULL REFERENCES members(member_id) ON DELETE CASCADE,
    child_id INTEGER NOT NULL REFERENCES members(member_id) ON DELETE CASCADE,
    parent_type VARCHAR(10) NOT NULL CHECK (parent_type IN ('father', 'mother')),
    CONSTRAINT chk_not_self_parent CHECK (parent_id <> child_id),
    CONSTRAINT uq_parent_child_type UNIQUE (genealogy_id, parent_id, child_id, parent_type)
);

CREATE TABLE marriages (
    marriage_id SERIAL PRIMARY KEY,
    genealogy_id INTEGER NOT NULL REFERENCES genealogies(genealogy_id) ON DELETE CASCADE,
    spouse1_id INTEGER NOT NULL REFERENCES members(member_id) ON DELETE CASCADE,
    spouse2_id INTEGER NOT NULL REFERENCES members(member_id) ON DELETE CASCADE,
    married_year INTEGER,
    CONSTRAINT chk_not_self_marriage CHECK (spouse1_id <> spouse2_id),
    CONSTRAINT uq_spouse_pair UNIQUE (genealogy_id, spouse1_id, spouse2_id)
);

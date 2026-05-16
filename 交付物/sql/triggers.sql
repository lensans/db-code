CREATE OR REPLACE FUNCTION fn_validate_parent_child()
RETURNS TRIGGER AS $$
DECLARE
    parent_gender CHAR(1);
    parent_birth INTEGER;
    child_birth INTEGER;
    parent_genealogy INTEGER;
    child_genealogy INTEGER;
BEGIN
    SELECT gender, birth_year, genealogy_id
    INTO parent_gender, parent_birth, parent_genealogy
    FROM members
    WHERE member_id = NEW.parent_id;

    SELECT birth_year, genealogy_id
    INTO child_birth, child_genealogy
    FROM members
    WHERE member_id = NEW.child_id;

    IF parent_genealogy IS NULL OR child_genealogy IS NULL THEN
        RAISE EXCEPTION 'Parent or child does not exist';
    END IF;

    IF parent_genealogy <> child_genealogy OR parent_genealogy <> NEW.genealogy_id THEN
        RAISE EXCEPTION 'Parent and child must belong to the same genealogy';
    END IF;

    IF NEW.parent_type = 'father' AND parent_gender <> 'M' THEN
        RAISE EXCEPTION 'Father relation requires parent gender M';
    END IF;

    IF NEW.parent_type = 'mother' AND parent_gender <> 'F' THEN
        RAISE EXCEPTION 'Mother relation requires parent gender F';
    END IF;

    IF parent_birth >= child_birth THEN
        RAISE EXCEPTION 'Parent birth year must be earlier than child birth year';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validate_parent_child ON parent_child_relations;

CREATE TRIGGER trg_validate_parent_child
BEFORE INSERT OR UPDATE ON parent_child_relations
FOR EACH ROW
EXECUTE FUNCTION fn_validate_parent_child();


CREATE OR REPLACE FUNCTION fn_validate_marriage()
RETURNS TRIGGER AS $$
DECLARE
    g1 INTEGER;
    g2 INTEGER;
BEGIN
    SELECT genealogy_id INTO g1 FROM members WHERE member_id = NEW.spouse1_id;
    SELECT genealogy_id INTO g2 FROM members WHERE member_id = NEW.spouse2_id;

    IF g1 IS NULL OR g2 IS NULL THEN
        RAISE EXCEPTION 'Spouse does not exist';
    END IF;

    IF g1 <> g2 OR g1 <> NEW.genealogy_id THEN
        RAISE EXCEPTION 'Marriage members must belong to the same genealogy';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validate_marriage ON marriages;

CREATE TRIGGER trg_validate_marriage
BEFORE INSERT OR UPDATE ON marriages
FOR EACH ROW
EXECUTE FUNCTION fn_validate_marriage();

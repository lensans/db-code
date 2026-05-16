SELECT setval(pg_get_serial_sequence('users', 'user_id'), COALESCE((SELECT MAX(user_id) FROM users), 1), true);
SELECT setval(pg_get_serial_sequence('genealogies', 'genealogy_id'), COALESCE((SELECT MAX(genealogy_id) FROM genealogies), 1), true);
SELECT setval(pg_get_serial_sequence('members', 'member_id'), COALESCE((SELECT MAX(member_id) FROM members), 1), true);
SELECT setval(pg_get_serial_sequence('genealogy_collaborators', 'id'), COALESCE((SELECT MAX(id) FROM genealogy_collaborators), 1), true);
SELECT setval(pg_get_serial_sequence('parent_child_relations', 'relation_id'), COALESCE((SELECT MAX(relation_id) FROM parent_child_relations), 1), true);
SELECT setval(pg_get_serial_sequence('marriages', 'marriage_id'), COALESCE((SELECT MAX(marriage_id) FROM marriages), 1), true);

from collections import defaultdict, deque

from sqlalchemy import text

from .models import GenealogyCollaborator, Marriage, Member, ParentChildRelation, db


def user_can_access_genealogy(user_id: int, genealogy_id: int) -> bool:
    member = GenealogyCollaborator.query.filter_by(
        genealogy_id=genealogy_id,
        user_id=user_id,
    ).first()
    if member:
        return True
    count = db.session.execute(
        text(
            """
            SELECT 1
            FROM genealogies
            WHERE genealogy_id = :genealogy_id
              AND owner_user_id = :user_id
            """
        ),
        {"genealogy_id": genealogy_id, "user_id": user_id},
    ).first()
    return count is not None


def dashboard_stats(genealogy_id: int) -> dict:
    total = Member.query.filter_by(genealogy_id=genealogy_id).count()
    male = Member.query.filter_by(genealogy_id=genealogy_id, gender="M").count()
    female = Member.query.filter_by(genealogy_id=genealogy_id, gender="F").count()
    return {
        "total": total,
        "male": male,
        "female": female,
        "male_ratio": round((male / total) * 100, 2) if total else 0,
        "female_ratio": round((female / total) * 100, 2) if total else 0,
    }


def query_subtree(genealogy_id: int, root_id: int, max_depth: int):
    sql = text(
        """
        WITH RECURSIVE subtree AS (
            SELECT
                m.member_id,
                m.name,
                m.gender,
                m.birth_year,
                m.death_year,
                m.generation_no,
                0 AS depth
            FROM members m
            WHERE m.genealogy_id = :genealogy_id
              AND m.member_id = :root_id
            UNION ALL
            SELECT
                child.member_id,
                child.name,
                child.gender,
                child.birth_year,
                child.death_year,
                child.generation_no,
                subtree.depth + 1
            FROM subtree
            JOIN parent_child_relations r
              ON r.genealogy_id = :genealogy_id
             AND r.parent_id = subtree.member_id
            JOIN members child
              ON child.member_id = r.child_id
            WHERE subtree.depth < :max_depth
        )
        SELECT DISTINCT *
        FROM subtree
        ORDER BY depth, generation_no, birth_year, member_id
        """
    )
    members = db.session.execute(
        sql,
        {"genealogy_id": genealogy_id, "root_id": root_id, "max_depth": max_depth},
    ).mappings().all()

    if not members:
        return None

    member_ids = [row["member_id"] for row in members]
    relation_rows = ParentChildRelation.query.filter(
        ParentChildRelation.genealogy_id == genealogy_id,
        ParentChildRelation.parent_id.in_(member_ids),
        ParentChildRelation.child_id.in_(member_ids),
    ).all()
    marriage_rows = Marriage.query.filter(
        Marriage.genealogy_id == genealogy_id,
        Marriage.spouse1_id.in_(member_ids),
        Marriage.spouse2_id.in_(member_ids),
    ).all()

    member_map = {
        row["member_id"]: {
            "member_id": row["member_id"],
            "name": row["name"],
            "gender": row["gender"],
            "birth_year": row["birth_year"],
            "death_year": row["death_year"],
            "generation_no": row["generation_no"],
            "spouses": [],
            "children": [],
        }
        for row in members
    }

    spouse_map = defaultdict(set)
    for marriage in marriage_rows:
        spouse_map[marriage.spouse1_id].add(marriage.spouse2_id)
        spouse_map[marriage.spouse2_id].add(marriage.spouse1_id)

    child_ids = set()
    for relation in relation_rows:
        if relation.parent_id in member_map and relation.child_id in member_map:
            member_map[relation.parent_id]["children"].append(member_map[relation.child_id])
            child_ids.add(relation.child_id)

    for member_id, spouse_ids in spouse_map.items():
        member_map[member_id]["spouses"] = [
            member_map[spouse_id]
            for spouse_id in sorted(spouse_ids)
            if spouse_id in member_map
        ]

    for node in member_map.values():
        node["children"].sort(key=lambda item: (item["generation_no"], item["birth_year"], item["member_id"]))

    return member_map[root_id]


def query_ancestors(genealogy_id: int, member_id: int):
    sql = text(
        """
        WITH RECURSIVE ancestor_tree AS (
            SELECT
                r.parent_id,
                r.child_id,
                1 AS depth
            FROM parent_child_relations r
            WHERE r.genealogy_id = :genealogy_id
              AND r.child_id = :member_id
            UNION ALL
            SELECT
                r.parent_id,
                r.child_id,
                at.depth + 1
            FROM parent_child_relations r
            JOIN ancestor_tree at ON r.child_id = at.parent_id
            WHERE r.genealogy_id = :genealogy_id
        )
        SELECT
            at.parent_id,
            m.name,
            m.gender,
            m.birth_year,
            m.death_year,
            at.depth
        FROM ancestor_tree at
        JOIN members m ON m.member_id = at.parent_id
        ORDER BY at.depth, at.parent_id
        """
    )
    return db.session.execute(
        sql,
        {"genealogy_id": genealogy_id, "member_id": member_id},
    ).mappings().all()


def find_kinship_path(genealogy_id: int, start_id: int, end_id: int):
    member_rows = Member.query.with_entities(
        Member.member_id,
        Member.name,
        Member.gender,
        Member.generation_no,
    ).filter_by(genealogy_id=genealogy_id).all()
    members = {
        row.member_id: {
            "member_id": row.member_id,
            "name": row.name,
            "gender": row.gender,
            "generation_no": row.generation_no,
        }
        for row in member_rows
    }
    if start_id not in members or end_id not in members:
        return []
    if start_id == end_id:
        return [{"member": members[start_id], "relation_to_next": None}]

    graph = defaultdict(set)
    relation_labels = {}

    for relation in ParentChildRelation.query.with_entities(
        ParentChildRelation.parent_id,
        ParentChildRelation.child_id,
        ParentChildRelation.parent_type,
    ).filter_by(genealogy_id=genealogy_id):
        child = members.get(relation.child_id)
        if child is None:
            continue
        graph[relation.parent_id].add(relation.child_id)
        graph[relation.child_id].add(relation.parent_id)
        relation_labels[(relation.parent_id, relation.child_id)] = "父亲" if relation.parent_type == "father" else "母亲"
        relation_labels[(relation.child_id, relation.parent_id)] = "儿子" if child["gender"] == "M" else "女儿"

    for marriage in Marriage.query.with_entities(
        Marriage.spouse1_id,
        Marriage.spouse2_id,
    ).filter_by(genealogy_id=genealogy_id):
        graph[marriage.spouse1_id].add(marriage.spouse2_id)
        graph[marriage.spouse2_id].add(marriage.spouse1_id)
        relation_labels[(marriage.spouse1_id, marriage.spouse2_id)] = "配偶"
        relation_labels[(marriage.spouse2_id, marriage.spouse1_id)] = "配偶"

    queue = deque([start_id])
    parents = {start_id: None}

    while queue:
        current = queue.popleft()
        for neighbor in graph.get(current, set()):
            if neighbor in parents:
                continue
            parents[neighbor] = current
            if neighbor == end_id:
                path_ids = []
                cursor = end_id
                while cursor is not None:
                    path_ids.append(cursor)
                    cursor = parents[cursor]
                path_ids.reverse()
                result = []
                for index, member_id in enumerate(path_ids):
                    next_relation = None
                    if index < len(path_ids) - 1:
                        next_relation = relation_labels.get((member_id, path_ids[index + 1]), "相关")
                    result.append({"member": members[member_id], "relation_to_next": next_relation})
                return result
            queue.append(neighbor)

    return []

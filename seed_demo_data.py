import random

from werkzeug.security import generate_password_hash

from genealogy_app import create_app
from genealogy_app.models import Genealogy, Marriage, Member, ParentChildRelation, User, db


SURNAMES = ["王", "李", "张", "赵", "刘", "陈", "杨", "黄", "周", "吴"]
MALE_CHARS = ["国", "建", "志", "明", "德", "天", "成", "文", "守", "远", "安", "林"]
FEMALE_CHARS = ["兰", "梅", "凤", "静", "芳", "雪", "慧", "敏", "倩", "晴", "婉", "芝"]


def random_name(surname: str, gender: str) -> str:
    pool = MALE_CHARS if gender == "M" else FEMALE_CHARS
    return surname + "".join(random.choices(pool, k=random.choice([1, 2])))


def reset_database() -> None:
    ParentChildRelation.query.delete()
    Marriage.query.delete()
    Member.query.delete()
    Genealogy.query.delete()
    User.query.delete()
    db.session.commit()


def add_genealogy(owner_id: int, title: str, surname: str, revision_year: int) -> Genealogy:
    genealogy = Genealogy(
        title=title,
        surname=surname,
        revision_year=revision_year,
        owner_user_id=owner_id,
    )
    db.session.add(genealogy)
    db.session.flush()
    return genealogy


def build_genealogy_members(
    genealogy_id: int,
    surname: str,
    generation_count: int,
    generation_size: int,
) -> tuple[list[Member], list[ParentChildRelation], list[Marriage]]:
    members: list[Member] = []
    relations: list[ParentChildRelation] = []
    marriages: list[Marriage] = []
    generations: list[list[Member]] = []

    for generation_no in range(1, generation_count + 1):
        base_birth_year = 1680 + (generation_no - 1) * 18
        generation_members: list[Member] = []

        for index in range(generation_size):
            gender = "M" if index % 2 == 0 else "F"
            birth_year = base_birth_year + random.randint(0, 4)
            death_year = None if generation_no >= generation_count - 1 else birth_year + random.randint(45, 82)
            member = Member(
                genealogy_id=genealogy_id,
                name=random_name(surname, gender),
                gender=gender,
                birth_year=birth_year,
                death_year=death_year,
                biography=f"第 {generation_no} 代成员，属于{surname}氏演示家族。",
                generation_no=generation_no,
            )
            db.session.add(member)
            generation_members.append(member)
            members.append(member)

        db.session.flush()
        generations.append(generation_members)

    for generation_index, generation_members in enumerate(generations, start=1):
        males = [member for member in generation_members if member.gender == "M"]
        females = [member for member in generation_members if member.gender == "F"]
        for pair_index in range(min(len(males), len(females))):
            marriages.append(
                Marriage(
                    genealogy_id=genealogy_id,
                    spouse1_id=males[pair_index].member_id,
                    spouse2_id=females[pair_index].member_id,
                    married_year=1680 + generation_index * 18 + 18,
                )
            )

    for generation_index in range(1, len(generations)):
        parents = generations[generation_index - 1]
        children = generations[generation_index]
        fathers = [member for member in parents if member.gender == "M"]
        mothers = [member for member in parents if member.gender == "F"]
        pair_count = min(len(fathers), len(mothers))

        for child_index, child in enumerate(children):
            father = fathers[child_index % pair_count]
            mother = mothers[child_index % pair_count]
            relations.append(
                ParentChildRelation(
                    genealogy_id=genealogy_id,
                    parent_id=father.member_id,
                    child_id=child.member_id,
                    parent_type="father",
                )
            )
            relations.append(
                ParentChildRelation(
                    genealogy_id=genealogy_id,
                    parent_id=mother.member_id,
                    child_id=child.member_id,
                    parent_type="mother",
                )
            )

    return members, relations, marriages


def seed() -> None:
    random.seed(42)
    app = create_app()

    with app.app_context():
        reset_database()

        user = User(username="demo", password_hash=generate_password_hash("demo123"))
        db.session.add(user)
        db.session.flush()

        genealogy_specs = [
            (f"{surname}氏演示族谱", surname, 2020 + index, 30, 34)
            for index, surname in enumerate(SURNAMES, start=1)
        ]

        total_members = 0
        total_relations = 0
        total_marriages = 0

        for title, surname, revision_year, generation_count, generation_size in genealogy_specs:
            genealogy = add_genealogy(user.user_id, title, surname, revision_year)
            members, relations, marriages = build_genealogy_members(
                genealogy.genealogy_id,
                surname,
                generation_count,
                generation_size,
            )
            db.session.add_all(relations)
            db.session.add_all(marriages)
            total_members += len(members)
            total_relations += len(relations)
            total_marriages += len(marriages)

        db.session.commit()
        print("seeded demo data")
        print("username=demo password=demo123")
        print(
            f"genealogies={len(genealogy_specs)} "
            f"members={total_members} "
            f"parent_child_relations={total_relations} "
            f"marriages={total_marriages}"
        )


if __name__ == "__main__":
    seed()

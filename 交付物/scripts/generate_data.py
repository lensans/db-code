import argparse
import csv
import os
import random
from datetime import datetime


SURNAMES = ["王", "李", "张", "赵", "刘", "陈", "杨", "黄", "周", "吴"]
MALE_CHARS = ["国", "建", "志", "明", "德", "天", "成", "中", "承", "远", "宏", "林"]
FEMALE_CHARS = ["华", "梅", "兰", "静", "芳", "雪", "怡", "敏", "倩", "晨", "婷", "芸"]


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_csv(path: str, headers, rows) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)


def random_name(surname: str, gender: str) -> str:
    pool = MALE_CHARS if gender == "M" else FEMALE_CHARS
    return surname + "".join(random.choices(pool, k=random.choice([1, 2])))


def split_evenly(total: int, parts: int) -> list[int]:
    base, remainder = divmod(total, parts)
    return [base + (1 if index < remainder else 0) for index in range(parts)]


def make_generation_sizes(member_count: int, generations: int) -> list[int]:
    if member_count < generations * 2:
        raise ValueError("member_count 必须至少是 generations 的 2 倍，才能稳定构造每代亲缘关系。")

    sizes = [2] * generations
    remaining = member_count - generations * 2
    for index in range(remaining):
        sizes[index % generations] += 1
    return sizes


def build_genealogy(genealogy_id: int, member_count: int, generations: int, start_member_id: int):
    surname = SURNAMES[(genealogy_id - 1) % len(SURNAMES)]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    genealogy_row = [
        genealogy_id,
        f"{surname}氏族谱{genealogy_id}",
        surname,
        2026,
        ((genealogy_id - 1) % 10) + 1,
        now,
    ]

    generation_sizes = make_generation_sizes(member_count, generations)
    members = []
    relations = []
    marriages = []

    generation_member_ids: list[list[int]] = []
    member_gender_map: dict[int, str] = {}
    next_member_id = start_member_id

    for generation_no, generation_size in enumerate(generation_sizes, start=1):
        ids = []
        base_birth_year = 1500 + (generation_no - 1) * 18

        for index in range(generation_size):
            if index % 2 == 0:
                gender = "M"
            else:
                gender = "F"
            birth_year = base_birth_year + random.randint(0, 5)
            death_year = None if generation_no >= generations - 2 else birth_year + random.randint(45, 88)
            biography = f"第{generation_no}代成员，属于{surname}氏家族。"

            members.append(
                [
                    next_member_id,
                    genealogy_id,
                    random_name(surname, gender),
                    gender,
                    birth_year,
                    death_year,
                    biography,
                    generation_no,
                ]
            )
            ids.append(next_member_id)
            member_gender_map[next_member_id] = gender
            next_member_id += 1

        generation_member_ids.append(ids)

    for generation_index, parent_ids in enumerate(generation_member_ids, start=1):
        male_parents = [member_id for member_id in parent_ids if member_gender_map[member_id] == "M"]
        female_parents = [member_id for member_id in parent_ids if member_gender_map[member_id] == "F"]

        pair_count = min(len(male_parents), len(female_parents))
        for pair_index in range(pair_count):
            marriages.append(
                [
                    genealogy_id,
                    male_parents[pair_index],
                    female_parents[pair_index],
                    1500 + generation_index * 18 + 20,
                ]
            )

    for generation_index in range(1, len(generation_member_ids)):
        parents = generation_member_ids[generation_index - 1]
        children = generation_member_ids[generation_index]
        father_candidates = [member_id for member_id in parents if member_gender_map[member_id] == "M"]
        mother_candidates = [member_id for member_id in parents if member_gender_map[member_id] == "F"]

        if not father_candidates or not mother_candidates:
            raise ValueError("上一代必须同时存在男性和女性成员。")

        father_pairs = list(zip(father_candidates, mother_candidates))
        if not father_pairs:
            raise ValueError("无法构造父母配对。")

        for child_index, child_id in enumerate(children):
            father_id, mother_id = father_pairs[child_index % len(father_pairs)]
            relations.append([genealogy_id, father_id, child_id, "father"])
            relations.append([genealogy_id, mother_id, child_id, "mother"])

    return genealogy_row, members, relations, marriages, next_member_id


def generate_dataset(output_dir: str, genealogy_count: int, total_members: int, large_genealogy_members: int, generations: int):
    if genealogy_count < 10:
        raise ValueError("根据作业要求，genealogy_count 不能小于 10。")
    if total_members < 100000:
        raise ValueError("根据作业要求，total_members 不能小于 100000。")
    if large_genealogy_members < 50000:
        raise ValueError("根据作业要求，large_genealogy_members 不能小于 50000。")
    if generations < 30:
        raise ValueError("根据作业要求，generations 不能小于 30。")
    if total_members <= large_genealogy_members:
        raise ValueError("total_members 必须大于 large_genealogy_members。")

    ensure_dir(output_dir)

    users = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for user_id in range(1, 11):
        users.append([user_id, f"user{user_id}", "pbkdf2:sha256:demo-password-hash", now])

    genealogies = []
    members = []
    relations = []
    marriages = []

    genealogy_sizes = [large_genealogy_members]
    remaining = total_members - large_genealogy_members
    genealogy_sizes.extend(split_evenly(remaining, genealogy_count - 1))

    next_member_id = 1
    for genealogy_id, member_count in enumerate(genealogy_sizes, start=1):
        genealogy_row, local_members, local_relations, local_marriages, next_member_id = build_genealogy(
            genealogy_id=genealogy_id,
            member_count=member_count,
            generations=generations,
            start_member_id=next_member_id,
        )
        genealogies.append(genealogy_row)
        members.extend(local_members)
        relations.extend(local_relations)
        marriages.extend(local_marriages)

    write_csv(os.path.join(output_dir, "users.csv"), ["user_id", "username", "password_hash", "created_at"], users)
    write_csv(
        os.path.join(output_dir, "genealogies.csv"),
        ["genealogy_id", "title", "surname", "revision_year", "owner_user_id", "created_at"],
        genealogies,
    )
    write_csv(
        os.path.join(output_dir, "members.csv"),
        ["member_id", "genealogy_id", "name", "gender", "birth_year", "death_year", "biography", "generation_no"],
        members,
    )
    write_csv(
        os.path.join(output_dir, "parent_child_relations.csv"),
        ["genealogy_id", "parent_id", "child_id", "parent_type"],
        relations,
    )
    write_csv(
        os.path.join(output_dir, "marriages.csv"),
        ["genealogy_id", "spouse1_id", "spouse2_id", "married_year"],
        marriages,
    )

    print(f"输出目录: {output_dir}")
    print(f"族谱数: {len(genealogies)}")
    print(f"总成员数: {len(members)}")
    print(f"最大族谱成员数: {max(genealogy_sizes)}")
    print(f"代数: {generations}")
    print(f"亲子关系数: {len(relations)}")
    print(f"婚姻关系数: {len(marriages)}")


def main():
    parser = argparse.ArgumentParser(description="生成满足数据库大作业要求的族谱模拟数据")
    parser.add_argument("--output-dir", default="交付物/data/generated_full", help="输出目录")
    parser.add_argument("--genealogy-count", type=int, default=10, help="族谱数量，不能小于 10")
    parser.add_argument("--total-members", type=int, default=100000, help="总成员数，不能小于 100000")
    parser.add_argument("--large-genealogy-members", type=int, default=50000, help="最大族谱成员数，不能小于 50000")
    parser.add_argument("--generations", type=int, default=30, help="每个族谱代数，不能小于 30")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    args = parser.parse_args()

    random.seed(args.seed)
    generate_dataset(
        output_dir=args.output_dir,
        genealogy_count=args.genealogy_count,
        total_members=args.total_members,
        large_genealogy_members=args.large_genealogy_members,
        generations=args.generations,
    )


if __name__ == "__main__":
    main()

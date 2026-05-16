from functools import wraps

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from .models import Genealogy, GenealogyCollaborator, Marriage, Member, ParentChildRelation, User, db
from .services import dashboard_stats, find_kinship_path, query_ancestors, query_subtree, user_can_access_genealogy


bp = Blueprint("main", __name__)
PAGE_SIZE = 50


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("main.login"))
        return view(*args, **kwargs)

    return wrapped


def ensure_access(genealogy_id: int):
    user = current_user()
    return user and user_can_access_genealogy(user.user_id, genealogy_id)


def ensure_owner(genealogy: Genealogy) -> bool:
    user = current_user()
    return bool(user and genealogy.owner_user_id == user.user_id)


def get_genealogy_member_or_none(genealogy_id: int, member_id: int):
    return Member.query.filter_by(genealogy_id=genealogy_id, member_id=member_id).first()


def member_display_name(genealogy_id: int, member_id: int | None) -> str:
    if not member_id:
        return ""
    member = get_genealogy_member_or_none(genealogy_id, member_id)
    return member.name if member else ""


def create_new_member_relations(genealogy_id: int, member: Member) -> None:
    father_id = request.form.get("father_id", type=int)
    mother_id = request.form.get("mother_id", type=int)
    spouse_id = request.form.get("spouse_id", type=int)
    married_year = request.form.get("married_year", type=int)

    if father_id:
        father = get_genealogy_member_or_none(genealogy_id, father_id)
        if not father:
            raise ValueError("所选父亲不属于当前族谱。")
        if father.member_id == member.member_id:
            raise ValueError("父亲不能选择新成员本人。")
        db.session.add(
            ParentChildRelation(
                genealogy_id=genealogy_id,
                parent_id=father.member_id,
                child_id=member.member_id,
                parent_type="father",
            )
        )

    if mother_id:
        mother = get_genealogy_member_or_none(genealogy_id, mother_id)
        if not mother:
            raise ValueError("所选母亲不属于当前族谱。")
        if mother.member_id == member.member_id:
            raise ValueError("母亲不能选择新成员本人。")
        db.session.add(
            ParentChildRelation(
                genealogy_id=genealogy_id,
                parent_id=mother.member_id,
                child_id=member.member_id,
                parent_type="mother",
            )
        )

    if spouse_id:
        spouse = get_genealogy_member_or_none(genealogy_id, spouse_id)
        if not spouse:
            raise ValueError("所选配偶不属于当前族谱。")
        if spouse.member_id == member.member_id:
            raise ValueError("配偶不能选择新成员本人。")
        db.session.add(
            Marriage(
                genealogy_id=genealogy_id,
                spouse1_id=member.member_id,
                spouse2_id=spouse.member_id,
                married_year=married_year,
            )
        )


@bp.route("/")
def index():
    if current_user():
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("main.login"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        if not username or not password:
            flash("用户名和密码不能为空。")
            return redirect(url_for("main.register"))
        if User.query.filter_by(username=username).first():
            flash("用户名已存在。")
            return redirect(url_for("main.register"))
        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash("注册成功，请登录。")
        return redirect(url_for("main.login"))
    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash("用户名或密码错误。")
            return redirect(url_for("main.login"))
        session["user_id"] = user.user_id
        return redirect(url_for("main.dashboard"))
    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login"))


@bp.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    owned = Genealogy.query.filter_by(owner_user_id=user.user_id).order_by(Genealogy.genealogy_id).all()
    joined_ids = [item.genealogy_id for item in user.collaborations]
    joined = (
        Genealogy.query.filter(Genealogy.genealogy_id.in_(joined_ids)).order_by(Genealogy.genealogy_id).all()
        if joined_ids
        else []
    )
    genealogy_ids = [item.genealogy_id for item in owned + joined]
    member_counts = {}
    if genealogy_ids:
        member_counts = dict(
            db.session.query(Member.genealogy_id, func.count(Member.member_id))
            .filter(Member.genealogy_id.in_(genealogy_ids))
            .group_by(Member.genealogy_id)
            .all()
        )
    return render_template(
        "dashboard.html",
        user=user,
        owned=owned,
        joined=joined,
        member_counts=member_counts,
        total_genealogies=len(owned) + len(joined),
        total_members=sum(member_counts.values()),
    )


@bp.route("/genealogies/new", methods=["GET", "POST"])
@login_required
def create_genealogy():
    if request.method == "POST":
        title = request.form["title"].strip()
        surname = request.form["surname"].strip()
        revision_year_text = request.form["revision_year"].strip()
        if not title or not surname:
            flash("谱名和姓氏不能为空。")
            return redirect(url_for("main.create_genealogy"))

        genealogy = Genealogy(
            title=title,
            surname=surname,
            revision_year=int(revision_year_text) if revision_year_text else None,
            owner_user_id=current_user().user_id,
        )
        db.session.add(genealogy)
        db.session.commit()
        flash("族谱创建成功。")
        return redirect(url_for("main.genealogy_detail", genealogy_id=genealogy.genealogy_id))
    return render_template("genealogy_form.html")


@bp.route("/genealogies/<int:genealogy_id>")
@login_required
def genealogy_detail(genealogy_id):
    if not ensure_access(genealogy_id):
        flash("无权访问该族谱。")
        return redirect(url_for("main.dashboard"))

    genealogy = Genealogy.query.get_or_404(genealogy_id)
    stats = dashboard_stats(genealogy_id)
    page = max(request.args.get("page", default=1, type=int), 1)
    pagination = (
        Member.query.filter_by(genealogy_id=genealogy_id)
        .order_by(Member.member_id)
        .paginate(page=page, per_page=PAGE_SIZE, error_out=False)
    )
    return render_template(
        "genealogy_detail.html",
        genealogy=genealogy,
        stats=stats,
        members=pagination.items,
        pagination=pagination,
        can_manage=ensure_owner(genealogy),
    )


@bp.route("/genealogies/<int:genealogy_id>/invite", methods=["POST"])
@login_required
def invite_collaborator(genealogy_id):
    genealogy = Genealogy.query.get_or_404(genealogy_id)
    user = current_user()
    if genealogy.owner_user_id != user.user_id:
        flash("只有创建者可以邀请协作者。")
        return redirect(url_for("main.genealogy_detail", genealogy_id=genealogy_id))

    username = request.form["username"].strip()
    invited = User.query.filter_by(username=username).first()
    if not invited:
        flash("目标用户不存在。")
        return redirect(url_for("main.genealogy_detail", genealogy_id=genealogy_id))
    if invited.user_id == user.user_id:
        flash("创建者无需重复邀请自己。")
        return redirect(url_for("main.genealogy_detail", genealogy_id=genealogy_id))

    exists = GenealogyCollaborator.query.filter_by(genealogy_id=genealogy_id, user_id=invited.user_id).first()
    if exists:
        flash("该用户已经是协作者。")
        return redirect(url_for("main.genealogy_detail", genealogy_id=genealogy_id))

    db.session.add(GenealogyCollaborator(genealogy_id=genealogy_id, user_id=invited.user_id, role="editor"))
    db.session.commit()
    flash("邀请成功。")
    return redirect(url_for("main.genealogy_detail", genealogy_id=genealogy_id))


@bp.route("/genealogies/<int:genealogy_id>/delete", methods=["POST"])
@login_required
def delete_genealogy(genealogy_id):
    genealogy = Genealogy.query.get_or_404(genealogy_id)
    if not ensure_owner(genealogy):
        flash("只有创建者可以删除族谱。")
        return redirect(url_for("main.genealogy_detail", genealogy_id=genealogy_id))

    ParentChildRelation.query.filter_by(genealogy_id=genealogy_id).delete(synchronize_session=False)
    Marriage.query.filter_by(genealogy_id=genealogy_id).delete(synchronize_session=False)
    Member.query.filter_by(genealogy_id=genealogy_id).delete(synchronize_session=False)
    GenealogyCollaborator.query.filter_by(genealogy_id=genealogy_id).delete(synchronize_session=False)
    db.session.delete(genealogy)
    db.session.commit()
    flash("族谱已删除。")
    return redirect(url_for("main.dashboard"))


@bp.route("/genealogies/<int:genealogy_id>/members/new", methods=["GET", "POST"])
@login_required
def create_member(genealogy_id):
    if not ensure_access(genealogy_id):
        flash("无权访问该族谱。")
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        try:
            birth_year = int(request.form["birth_year"])
            death_year_text = request.form["death_year"].strip()
            death_year = int(death_year_text) if death_year_text else None
            if death_year is not None and death_year < birth_year:
                raise ValueError("逝世年份不能早于出生年份。")

            member = Member(
                genealogy_id=genealogy_id,
                name=request.form["name"].strip(),
                gender=request.form["gender"],
                birth_year=birth_year,
                death_year=death_year,
                biography=request.form["biography"].strip(),
                generation_no=int(request.form["generation_no"]),
            )
            db.session.add(member)
            db.session.flush()
            create_new_member_relations(genealogy_id, member)
            db.session.commit()
            flash("成员创建成功。")
            return redirect(url_for("main.genealogy_detail", genealogy_id=genealogy_id))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc))
        except Exception as exc:
            db.session.rollback()
            flash(f"成员创建失败：{exc}")

    return render_template("member_form.html", genealogy_id=genealogy_id, member=None)


@bp.route("/members/<int:member_id>/edit", methods=["GET", "POST"])
@login_required
def edit_member(member_id):
    member = Member.query.get_or_404(member_id)
    if not ensure_access(member.genealogy_id):
        flash("无权访问该族谱。")
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        birth_year = int(request.form["birth_year"])
        death_year_text = request.form["death_year"].strip()
        death_year = int(death_year_text) if death_year_text else None
        if death_year is not None and death_year < birth_year:
            flash("逝世年份不能早于出生年份。")
            return redirect(url_for("main.edit_member", member_id=member_id))

        member.name = request.form["name"].strip()
        member.gender = request.form["gender"]
        member.birth_year = birth_year
        member.death_year = death_year
        member.biography = request.form["biography"].strip()
        member.generation_no = int(request.form["generation_no"])
        db.session.commit()
        flash("成员更新成功。")
        return redirect(url_for("main.genealogy_detail", genealogy_id=member.genealogy_id))

    return render_template("member_form.html", genealogy_id=member.genealogy_id, member=member)


@bp.route("/members/<int:member_id>/delete", methods=["POST"])
@login_required
def delete_member(member_id):
    member = Member.query.get_or_404(member_id)
    genealogy_id = member.genealogy_id
    if not ensure_access(genealogy_id):
        flash("无权访问该族谱。")
        return redirect(url_for("main.dashboard"))

    ParentChildRelation.query.filter(
        ParentChildRelation.genealogy_id == genealogy_id,
        (ParentChildRelation.parent_id == member_id) | (ParentChildRelation.child_id == member_id),
    ).delete(synchronize_session=False)
    Marriage.query.filter(
        Marriage.genealogy_id == genealogy_id,
        (Marriage.spouse1_id == member_id) | (Marriage.spouse2_id == member_id),
    ).delete(synchronize_session=False)
    db.session.delete(member)
    db.session.commit()
    flash("成员已删除。")
    return redirect(url_for("main.genealogy_detail", genealogy_id=genealogy_id))


@bp.route("/genealogies/<int:genealogy_id>/relations/new", methods=["GET", "POST"])
@login_required
def create_relation(genealogy_id):
    if not ensure_access(genealogy_id):
        flash("无权访问该族谱。")
        return redirect(url_for("main.dashboard"))

    genealogy = Genealogy.query.get_or_404(genealogy_id)

    if request.method == "POST":
        relation_kind = request.form["relation_kind"]
        try:
            if relation_kind == "parent_child":
                parent_id = int(request.form["parent_id"])
                child_id = int(request.form["child_id"])
                if parent_id == child_id:
                    raise ValueError("父母成员和子女成员不能是同一人。")
                if not get_genealogy_member_or_none(genealogy_id, parent_id) or not get_genealogy_member_or_none(genealogy_id, child_id):
                    raise ValueError("成员必须属于当前族谱。")
                db.session.add(
                    ParentChildRelation(
                        genealogy_id=genealogy_id,
                        parent_id=parent_id,
                        child_id=child_id,
                        parent_type=request.form["parent_type"],
                    )
                )
            elif relation_kind == "marriage":
                spouse1_id = int(request.form["spouse1_id"])
                spouse2_id = int(request.form["spouse2_id"])
                if spouse1_id == spouse2_id:
                    raise ValueError("婚姻关系的双方不能是同一人。")
                if not get_genealogy_member_or_none(genealogy_id, spouse1_id) or not get_genealogy_member_or_none(genealogy_id, spouse2_id):
                    raise ValueError("成员必须属于当前族谱。")
                db.session.add(
                    Marriage(
                        genealogy_id=genealogy_id,
                        spouse1_id=spouse1_id,
                        spouse2_id=spouse2_id,
                        married_year=int(request.form["married_year"]) if request.form["married_year"] else None,
                    )
                )
            else:
                flash("未知关系类型。")
                return redirect(url_for("main.create_relation", genealogy_id=genealogy_id))

            db.session.commit()
            flash("关系创建成功。")
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc))
        except Exception as exc:
            db.session.rollback()
            flash(f"关系创建失败：{exc}")

        return redirect(url_for("main.create_relation", genealogy_id=genealogy_id))

    existing_parent_relations = (
        ParentChildRelation.query.filter_by(genealogy_id=genealogy_id)
        .order_by(ParentChildRelation.relation_id.desc())
        .limit(20)
        .all()
    )
    existing_marriages = (
        Marriage.query.filter_by(genealogy_id=genealogy_id)
        .order_by(Marriage.marriage_id.desc())
        .limit(20)
        .all()
    )
    recent_member_ids = {
        *(row.parent_id for row in existing_parent_relations),
        *(row.child_id for row in existing_parent_relations),
        *(row.spouse1_id for row in existing_marriages),
        *(row.spouse2_id for row in existing_marriages),
    }
    member_map = {
        member.member_id: member
        for member in Member.query.filter(Member.member_id.in_(recent_member_ids)).all()
    } if recent_member_ids else {}

    return render_template(
        "relation_form.html",
        genealogy=genealogy,
        member_map=member_map,
        existing_parent_relations=existing_parent_relations,
        existing_marriages=existing_marriages,
    )


@bp.route("/genealogies/<int:genealogy_id>/members/options")
@login_required
def member_options(genealogy_id):
    if not ensure_access(genealogy_id):
        return jsonify([]), 403

    keyword = request.args.get("q", "").strip()
    limit = min(max(request.args.get("limit", default=30, type=int), 1), 50)
    query = Member.query.filter(Member.genealogy_id == genealogy_id)
    if keyword:
        query = query.filter(Member.name.ilike(f"%{keyword}%"))

    members = query.order_by(Member.member_id).limit(limit).all()
    return jsonify(
        [
            {
                "id": member.member_id,
                "name": member.name,
                "gender": "男" if member.gender == "M" else "女",
                "birth_year": member.birth_year,
                "generation_no": member.generation_no,
            }
            for member in members
        ]
    )


@bp.route("/genealogies/<int:genealogy_id>/search")
@login_required
def search_members(genealogy_id):
    if not ensure_access(genealogy_id):
        flash("无权访问该族谱。")
        return redirect(url_for("main.dashboard"))

    genealogy = Genealogy.query.get_or_404(genealogy_id)
    keyword = request.args.get("keyword", "").strip()
    page = max(request.args.get("page", default=1, type=int), 1)
    members = []
    pagination = None

    if keyword:
        pagination = (
            Member.query.filter(
                Member.genealogy_id == genealogy_id,
                Member.name.ilike(f"%{keyword}%"),
            )
            .order_by(Member.member_id)
            .paginate(page=page, per_page=PAGE_SIZE, error_out=False)
        )
        members = pagination.items

    return render_template("search.html", genealogy=genealogy, keyword=keyword, members=members, pagination=pagination)


@bp.route("/genealogies/<int:genealogy_id>/tree")
@login_required
def tree_preview(genealogy_id):
    if not ensure_access(genealogy_id):
        flash("无权访问该族谱。")
        return redirect(url_for("main.dashboard"))

    genealogy = Genealogy.query.get_or_404(genealogy_id)
    root_id = request.args.get("root_id", type=int)
    max_depth = request.args.get("max_depth", default=3, type=int)
    max_depth = min(max(max_depth, 1), 5)
    tree = query_subtree(genealogy_id, root_id, max_depth) if root_id else None
    return render_template(
        "tree.html",
        genealogy=genealogy,
        tree=tree,
        root_id=root_id,
        root_name=member_display_name(genealogy_id, root_id),
        max_depth=max_depth,
    )


@bp.route("/genealogies/<int:genealogy_id>/ancestors")
@login_required
def ancestor_query(genealogy_id):
    if not ensure_access(genealogy_id):
        flash("无权访问该族谱。")
        return redirect(url_for("main.dashboard"))
    member_id = request.args.get("member_id", type=int)
    results = query_ancestors(genealogy_id, member_id) if member_id else []
    genealogy = Genealogy.query.get_or_404(genealogy_id)
    return render_template(
        "ancestors.html",
        genealogy=genealogy,
        results=results,
        member_id=member_id,
        member_name=member_display_name(genealogy_id, member_id),
    )


@bp.route("/genealogies/<int:genealogy_id>/kinship")
@login_required
def kinship_query(genealogy_id):
    if not ensure_access(genealogy_id):
        flash("无权访问该族谱。")
        return redirect(url_for("main.dashboard"))
    start_id = request.args.get("start_id", type=int)
    end_id = request.args.get("end_id", type=int)
    path = find_kinship_path(genealogy_id, start_id, end_id) if start_id and end_id else []
    genealogy = Genealogy.query.get_or_404(genealogy_id)
    return render_template(
        "kinship.html",
        genealogy=genealogy,
        path=path,
        start_id=start_id,
        start_name=member_display_name(genealogy_id, start_id),
        end_id=end_id,
        end_name=member_display_name(genealogy_id, end_id),
    )

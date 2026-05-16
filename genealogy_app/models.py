from datetime import datetime

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Genealogy(db.Model):
    __tablename__ = "genealogies"

    genealogy_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(50), nullable=False)
    revision_year = db.Column(db.Integer)
    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    owner = db.relationship("User", backref="owned_genealogies")


class GenealogyCollaborator(db.Model):
    __tablename__ = "genealogy_collaborators"

    id = db.Column(db.Integer, primary_key=True)
    genealogy_id = db.Column(db.Integer, db.ForeignKey("genealogies.genealogy_id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="editor")

    __table_args__ = (
        db.UniqueConstraint("genealogy_id", "user_id", name="uq_genealogy_collaborator"),
    )

    genealogy = db.relationship("Genealogy", backref="collaborators")
    user = db.relationship("User", backref="collaborations")


class Member(db.Model):
    __tablename__ = "members"

    member_id = db.Column(db.Integer, primary_key=True)
    genealogy_id = db.Column(db.Integer, db.ForeignKey("genealogies.genealogy_id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(1), nullable=False)
    birth_year = db.Column(db.Integer, nullable=False)
    death_year = db.Column(db.Integer)
    biography = db.Column(db.Text)
    generation_no = db.Column(db.Integer, nullable=False, default=1)

    genealogy = db.relationship("Genealogy", backref="members")


class ParentChildRelation(db.Model):
    __tablename__ = "parent_child_relations"

    relation_id = db.Column(db.Integer, primary_key=True)
    genealogy_id = db.Column(db.Integer, db.ForeignKey("genealogies.genealogy_id"), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("members.member_id"), nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey("members.member_id"), nullable=False)
    parent_type = db.Column(db.String(10), nullable=False)


class Marriage(db.Model):
    __tablename__ = "marriages"

    marriage_id = db.Column(db.Integer, primary_key=True)
    genealogy_id = db.Column(db.Integer, db.ForeignKey("genealogies.genealogy_id"), nullable=False)
    spouse1_id = db.Column(db.Integer, db.ForeignKey("members.member_id"), nullable=False)
    spouse2_id = db.Column(db.Integer, db.ForeignKey("members.member_id"), nullable=False)
    married_year = db.Column(db.Integer)

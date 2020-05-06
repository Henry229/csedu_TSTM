import random
import re
import string
from datetime import datetime, timedelta
from time import time

import jwt
import pytz
from flask import current_app
from flask_login import UserMixin, AnonymousUserMixin, current_user
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import load_only
from sqlalchemy.sql import func
from werkzeug.security import generate_password_hash, check_password_hash

from app import login_manager, db
from config import Config


# permission 변경시 Role class에 영향
class Permission:
    ITEM_EXEC = 0x0001  # 1
    ITEM_MANAGE = 0x0002  # 2
    TESTLET_MANAGE = 0x0004  # 4
    TESTSET_READ = 0x0008  # 8
    TESTSET_MANAGE = 0x0010  # 16
    ASSESSMENT_READ = 0x0020  # 32
    ASSESSMENT_MANAGE = 0x0040  # 64
    WRITING_READ = 0x0080  # 128
    WRITING_MANAGE = 0x0100  # 256
    ADMIN = 0x8000  # 32768


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    confirmed = db.Column(db.Boolean, default=False)
    created_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    modified_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    last_seen = db.Column(db.DateTime(), default=datetime.now(pytz.utc))
    active = db.Column(db.BOOLEAN)
    delete = db.Column(db.BOOLEAN)

    # name = db.Column(db.String(64))     # Student 조회시, 이름 조회 가능하도록
    # location = db.Column(db.String(64)) # Student 조회시, 사는 지역 확인하도록
    # about_me = db.Column(db.Text())
    # member_since = db.Column(db.DateTime(), default=datetime.now(pytz.utc))
    #
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        # Role이 할당되지 않은 유저일 경우, Email이 관리자 이메일이면 Administrator Role을 부여
        #                              그외는 모두 Default role을 부여.
        if self.role is None:
            if self.email == current_app.config['CSEDU_ADMIN']:
                self.role = Role.query.filter_by(name='Administrator').first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id}).decode('utf-8')

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.commit()
        return True

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)

    def is_student(self):
        if self.role.name == 'Test_taker':
            return True
        else:
            return False

    def is_writing_marker(self):
        if self.role.name == 'Writing_marker':
            return True
        else:
            return False

    def get_branch_id(self):
        if self.role.name == 'Test_center':
            # Naming convention: 'Castlehill' or 'Castlehill Branch'
            branch_name = self.username.rsplit(' ', 1)[0]
            row = Codebook.query.filter_by(code_type='test_center').filter_by(code_name=branch_name).first()
            return row.id
        else:
            return None

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id}).decode('utf-8')

    @staticmethod
    def reset_password(token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        user = User.query.get(data.get('reset'))
        if user is None:
            return False
        user.password = new_password
        db.session.commit()
        return True

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            Config.SECRET_KEY, algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, Config.SECRET_KEY,
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    @staticmethod
    def create_default_admin(email, password):
        if not User.query.filter_by(username='admin').first():
            admin_role = Role.query.filter_by(name='Administrator').first()
            admin_user = User(username='admin', email=email, role=admin_role, confirmed=True)
            # if you want to set Random Password, please use as following:
            # password = ''.join(random.SystemRandom().choice(string.ascii_uppercase+string.digits) for _ in rnage(16)
            admin_user.password = password
            db.session.add(admin_user)
            db.session.commit()
        else:
            print("Cannot create default admin user: user already existing.")

    @staticmethod
    def create_default_users():
        roles = Role.query.all()
        created_users = []
        for role in roles:
            password = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(16))
            if role.name == 'Administrator':
                continue
            if not User.query.filter_by(username=role.name).first():
                t_email = role.name + '@csedu.com'
                user = User(username=role.name, email=t_email, confirmed=True, active=True, role=role)
                user.password = password
                db.session.add(user)
                created_users.append((user.email, password))
                print("{} User created: with {} role ".format(user.username, user.role.name))
            else:
                print("Cannot create default admin user: user already existing.")
        db.session.commit()
        return created_users

    @staticmethod
    def getUserName(id):
        user = User.query.filter_by(id=id).first()
        if user:
            return user.username
        else:
            return 'Anonymous'

    def ping(self):
        self.last_seen = datetime.now(pytz.utc)
        db.session.commit()

    def __json__(self):
        return ['username', 'email']

    def __repr__(self):
        return '<User %r>' % self.username


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')
    created_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    modified_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    @staticmethod
    def insert_roles():
        roles = {
            'Test_taker': [Permission.ITEM_EXEC],
            'Item_generator': [Permission.ITEM_EXEC, Permission.ITEM_MANAGE],
            'Assessment_creator': [Permission.ASSESSMENT_MANAGE],
            'Itembank_manager': [Permission.ITEM_EXEC, Permission.ITEM_MANAGE, Permission.TESTLET_MANAGE,
                                 Permission.TESTSET_MANAGE],
            'Moderator': [Permission.ITEM_EXEC, Permission.ASSESSMENT_MANAGE,
                          Permission.WRITING_MANAGE,
                          Permission.ITEM_MANAGE, Permission.TESTSET_MANAGE],
            'Administrator': [Permission.ITEM_EXEC, Permission.ASSESSMENT_MANAGE,
                              Permission.ITEM_MANAGE, Permission.TESTLET_MANAGE, Permission.TESTSET_READ,
                              Permission.TESTSET_MANAGE, Permission.ASSESSMENT_READ,
                              Permission.WRITING_READ, Permission.WRITING_MANAGE,
                              Permission.ADMIN],
            'Test_center': [Permission.ASSESSMENT_READ, Permission.ASSESSMENT_MANAGE, Permission.WRITING_READ,
                            Permission.WRITING_MANAGE],
            'Writing_marker': [Permission.WRITING_READ]
        }
        default_role = 'Test_taker'

        for r, p in roles.items():
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
                db.session.add(role)
            role.reset_permissions()
            for perm in p:
                role.add_permission(perm)
            role.default = (role.name == default_role)
        db.session.commit()

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm

    def __repr__(self):
        return '<Role %r>' % self.name


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False


login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Item(db.Model):
    """Item Model: basic unit for question in Testlet.
           Data is exported from QTI qti.xml or Excel file"""
    __tablename__ = 'item'

    id = db.Column(db.Integer, primary_key=True)
    GUID = db.Column(db.String(45))
    version = db.Column(db.Integer, default=1)
    TAO_GUID = db.Column(db.String(45))
    name = db.Column(db.String(50))
    grade = db.Column(db.Integer, index=True)
    subject = db.Column(db.Integer, index=True)
    category = db.Column(db.Integer, index=True)
    subcategory = db.Column(db.Integer)
    level = db.Column(db.Integer)
    interaction_type = db.Column(db.String(30))
    cardinality = db.Column(db.String(30))  # responseDeclaration-cardinality
    baseType = db.Column(db.String(30))  # responseDeclaration-baseType
    caseSensitive = db.Column(db.String(30))  # mapping-> mapEntry-caseSensitive
    correct_answer = db.Column(db.String(256))  # JSON type
    file_link = db.Column(db.String(256))
    correct_r_value = db.Column(JSONB)  # correct response value
    outcome_score = db.Column(db.Float)  # SetOutcome Score
    extended_property = db.Column(JSONB)  # JSON type
    active = db.Column(db.Boolean)
    delete = db.Column(db.Boolean)
    created_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    imported_by = db.Column(db.Integer)
    imported_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    modified_by = db.Column(db.Integer)
    modified_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))

    marking = db.relationship('Marking', back_populates="item")
    explanation = db.relationship('ItemExplanation', back_populates="item")

    def set_value_from_qti(self, qti_item):
        try:  # TODO - Temporary patch to import excel file
            self.TAO_GUID = qti_item.get_identifier()
        except:
            pass
        self.name = qti_item.get_attribute_value('title')
        self.interaction_type = qti_item.get_interaction_type()
        self.cardinality = qti_item.get_cardinality()
        self.baseType = qti_item.get_base_type()
        self.correct_answer = qti_item.get_correct_response()
        self.file_link = qti_item.get_resource_id()

    def get_contents(self):
        """
        This function returns the actual contents of the item. The contents consists of DB and File contents
        :return: A dictionary containing item contents
        """
        # TODO - Get item contents from file
        file_contents = {}  # get_file_contents(self.TAO_GUID)

        contents = {
            "id": self.id,
            "GUID": self.GUID,
            "version": self.version,
            "TAO_GUID": self.TAO_GUID,
            "name": self.name,
            "grade": self.grade,
            "subject": self.subject,
            "category": self.category,
            "subcategory": self.subcategory,
            "level": self.level,
            "interaction": self.interaction_type,
            "cardinality": self.cardinality,
            "baseType": self.baseType,
            "caseSensitive": self.caseSensitive,
            "correct_answer": self.correct_answer,
            "multiple_answer": self.multiple_answers,
            "extended_property": self.extended_property,
            "active": self.active,
            "imported_by": self.imported_by,
            "imported_time": self.imported_time,
            "modified_by": self.modified_by,
            "modified_time": self.modified_time
        }

        return contents.update(file_contents)

    def __repr__(self):
        return '<Item {}:{}>'.format(self.id, self.interaction_type)


class ItemExplanation(db.Model):
    """ItemExplanation Model: basic unit for question explanation """
    __tablename__ = 'item_explanation'

    id = db.Column(db.Integer, primary_key=True)
    GUID = db.Column(db.String(45))
    version = db.Column(db.Integer, default=1)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    explanation = db.Column(db.String(2048))
    images = db.Column(JSONB)
    links = db.Column(JSONB)
    active = db.Column(db.Boolean, default=True)
    modified_by = db.Column(db.Integer)
    modified_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))

    item = db.relationship('Item', back_populates="explanation")

    def versioning(self):
        new_ie = ItemExplanation()
        version = db.session.query(func.max(ItemExplanation.version)).filter_by(GUID=self.GUID).scalar()

        for key in self.__dict__:
            if key != '_sa_instance_state' and key != 'modified_time' and key != 'modified_by' and key != 'id':
                new_ie.__dict__[key] = self.__dict__[key]

        new_ie.modified_by = current_user.id
        new_ie.version = version + 1
        return new_ie

    def is_versioning(self, item_id, explanation, images, links):
        if images:
            if self.images["images"] == images:
                return False
            else:
                return True
        return False

    def __repr__(self):
        return '<Item Explanation {}>'.format(self.id)


class Testlet(db.Model):
    '''Testlet Model: basic unit for question set in Testset. '''
    __tablename__ = 'testlet'
    __table_args__ = (UniqueConstraint('GUID', 'version', name='testlet_versioning_unique'),)

    id = db.Column(db.Integer, primary_key=True)
    GUID = db.Column(db.String(45))
    version = db.Column(db.Integer, default=1)
    name = db.Column(db.String(50))
    grade = db.Column(db.Integer, index=True)
    subject = db.Column(db.Integer, index=True)
    test_type = db.Column(db.Integer, index=True, default='Naplan')
    no_of_items = db.Column(db.Integer)
    full_mark = db.Column(db.Float)  # sum of each item's mark * weight'
    # isChanged = db.Column(db.Boolean, default=False)  # true when weights or items changed
    completed = db.Column(db.Boolean, default=False)
    extended_property = db.Column(JSONB)  # JSON type
    active = db.Column(db.Boolean)
    delete = db.Column(db.Boolean)
    created_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    modified_by = db.Column(db.Integer)
    modified_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))

    weights = db.relationship('TestletWeight', backref='testlet', lazy='dynamic', order_by='TestletWeight.level.asc()')
    items = db.relationship('Item', secondary='testlet_items', order_by='TestletHasItem.order.asc()')

    def versioning(self):
        new_tl = Testlet()
        version = db.session.query(func.max(Testlet.version)).filter_by(GUID=self.GUID).scalar()

        for key in self.__dict__:
            if key != '_sa_instance_state' and key != 'created_time' and key != 'modified_time' and key != 'modified_by' and key != 'id':
                new_tl.__dict__[key] = self.__dict__[key]

        new_tl.modified_by = current_user.id
        new_tl.version = version + 1
        return new_tl

    def is_versioning(self, id, name, grade, subject, test_type, no_of_items, weights):
        if self.subject != subject:
            return True
        if self.test_type != test_type:
            return True
        if self.no_of_items != int(no_of_items):
            return True
        for entry in weights.entries:
            l = Codebook.get_code_id(entry.form.level.data)
            weight = TestletWeight.query.filter_by(testlet_id=id).filter_by(
                level=l).first()
            if weight.weight != float(entry.form.weight.data):
                return True
        return False

    def __repr__(self):
        return '<Testlet {}>'.format(self.name)


class TestletWeight(db.Model):
    '''Testlet_Weight Model:  describe weight for each level in testlet table '''
    __tablename__ = 'testlet_weight'

    id = db.Column(db.Integer, primary_key=True)
    testlet_id = db.Column(db.Integer, db.ForeignKey('testlet.id'))
    level = db.Column(db.Integer, index=True)
    weight = db.Column(db.Float)
    modified_by = db.Column(db.Integer)
    modified_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))

    def clone(self):
        new_tl = TestletWeight()
        for key in self.__dict__:
            if key != '_sa_instance_state' and key != 'modified_time' and key != 'modified_by' and key != 'id' and key != 'testlet_id':
                new_tl.__dict__[key] = self.__dict__[key]

        new_tl.modified_by = current_user.id
        return new_tl

    def __repr__(self):
        return '<Testlet has Weights: {}>'.format(self.id)


class TestletHasItem(db.Model):
    '''Testlet_has_item Model: associate table '''
    __tablename__ = 'testlet_items'

    id = db.Column(db.Integer, primary_key=True)
    testlet_id = db.Column(db.Integer, db.ForeignKey('testlet.id'))
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    order = db.Column(db.Integer, index=True)  # order of items in the testlet
    weight = db.Column(db.Float)
    created_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    modified_by = db.Column(db.Integer)
    modified_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))

    testlet = db.relationship('Testlet', backref=db.backref('item_asso', lazy='dynamic'))
    item = db.relationship('Item', backref=db.backref('testlet_asso', lazy='dynamic'))

    def clone(self):
        new_ti = TestletHasItem()
        for key in self.__dict__:
            if key != '_sa_instance_state' and key != 'created_time' and key != 'modified_time' and key != 'testlet_id' and key != 'id':
                new_ti.__dict__[key] = self.__dict__[key]
        new_ti.modified_by = current_user.id
        return new_ti

    @staticmethod
    def on_changed_weight(target, value, oldvalue, initiator):
        # ToDo: get _total_score with weights and items
        # ToDo: set Testlet.full_mark with _total_score
        _total_score = 100
        testlet = Testlet.query.filter_by(id=target.testlet_id).first()
        testlet.full_mark = _total_score

    @staticmethod
    def on_changed_item(target, value, oldvalue, initiator):
        # ToDo: get _total_score with weights and items
        # ToDo: set Testlet.full_mark with _total_score
        _total_score = 100
        testlet = Testlet.query.filter_by(id=target.testlet_id).first()
        testlet.full_mark = _total_score

    def __repr__(self):
        return '<Testlet has Items: {}>'.format(self.id)


db.event.listen(TestletHasItem.weight, 'set', TestletHasItem.on_changed_weight)
db.event.listen(TestletHasItem.item_id, 'set', TestletHasItem.on_changed_item)


class Testset(db.Model):
    """Testset Model: basic unit for testlet set in assessment test. """
    __tablename__ = 'testset'
    __table_args__ = (UniqueConstraint('GUID', 'version', name='testset_versioning_unique'),)

    id = db.Column(db.Integer, primary_key=True)
    GUID = db.Column(db.String(45))
    version = db.Column(db.Integer, default=1)
    name = db.Column(db.String(50))
    grade = db.Column(db.Integer, index=True)
    subject = db.Column(db.Integer, index=True)
    test_type = db.Column(db.Integer, index=True, default='Naplan')
    no_of_stages = db.Column(db.Integer)
    completed = db.Column(db.Boolean, default=False)
    extended_property = db.Column(JSONB)  # JSON type
    total_score = db.Column(db.Float)
    test_duration = db.Column(db.Integer, default=50)  # Number of minutes the testset runs
    active = db.Column(db.Boolean)
    delete = db.Column(db.Boolean)
    created_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    modified_by = db.Column(db.Integer)
    modified_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    branching = db.Column(JSONB)

    assessments = db.relationship('Assessment', secondary='assessment_testsets',
                                  order_by='AssessmentHasTestset.assessment_id.asc()')

    def versioning(self):
        new_ts = Testset()
        version = db.session.query(func.max(Testset.version)).filter_by(GUID=self.GUID).scalar()

        for key in self.__dict__:
            if key != '_sa_instance_state' and key != 'created_time' and key != 'modified_time' and key != 'modified_by' and key != 'id':
                new_ts.__dict__[key] = self.__dict__[key]

        new_ts.modified_by = current_user.id
        new_ts.version = version + 1
        return new_ts

    def is_versioning(self, id, name, grade, subject, test_type, no_of_stages, test_duration, total_score,
                      testset_data):
        if not self.completed:
            return False
        if self.no_of_stages != int(no_of_stages):
            return True
        if self.branching != testset_data:
            return True
        return False

    def parsingStageData(self):
        item_no = 0
        jsonData = self.branching.get("data")
        parsedNodes = []
        parsedEdges = []
        item_no = Testset.intoNext(item_no, jsonData, parsedNodes, parsedEdges)
        parsedData = {"nodes": parsedNodes, "edges": parsedEdges}
        return parsedData

    def intoNext(item_no, jsonData, parsedNodes, parsedEdges):
        _parent_no = item_no
        # parsedData = []
        for data in jsonData:
            item_no = item_no + 1
            _current_name = data.get("name")
            _current_label = "{0}%".format(data.get("condition"))
            node = dict(id=item_no, label=_current_name)
            parsedNodes.append(node)
            if (item_no != 0):
                edge = dict(to=item_no, arrows='to', label=_current_label)
                x = edge.setdefault("from", _parent_no)
                parsedEdges.append(edge)
            if (data.get("next")):
                item_no = Testset.intoNext(item_no, data.get("next"), parsedNodes, parsedEdges)
        return item_no

    def getFirstStageTestletID(self):
        branching = self.branching.get("data")
        return branching[0].get("id")

    def __repr__(self):
        return '<Testset {}>'.format(self.name)


class Assessment(db.Model):
    """Assessment Model: basic unit for test. """
    __tablename__ = 'assessment'
    __table_args__ = (UniqueConstraint('GUID', 'version', name='assessment_versioning_unique'),)

    id = db.Column(db.Integer, primary_key=True)
    GUID = db.Column(db.String(45))
    version = db.Column(db.Integer, default=1)
    name = db.Column(db.String(50), index=True)
    branch_id = db.Column(db.Integer)  # from CodeTable
    test_type = db.Column(db.Integer)  # from CodeTable
    year = db.Column(db.String(4), default=datetime.today().year)
    review_period = db.Column(db.Integer, default=7)
    session_date = db.Column(db.DateTime)
    session_start_time = db.Column(db.Time)
    session_end_time = db.Column(db.Time)
    avg_score = db.Column(db.Float)
    highest_score = db.Column(db.Float)
    lowest_score = db.Column(db.Float)
    created_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    modified_by = db.Column(db.Integer)
    modified_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    active = db.Column(db.Boolean, default=True)
    delete = db.Column(db.Boolean)

    testsets = db.relationship('Testset', secondary='assessment_testsets',
                               order_by='AssessmentHasTestset.testset_id.asc()')
    enroll = db.relationship('AssessmentEnroll', back_populates="assessment")

    @property
    def branch_state(self):
        branch_info = Codebook.get_additional_info(self.branch_id)
        if branch_info:
            if 'branch_state' in branch_info.keys():
                return branch_info['branch_state']
        return list(Config.CS_BRANCH_STATES.keys())[0]  # Use the first one as default

    def versioning(self):
        new_assessment = Assessment()
        version = db.session.query(func.max(Assessment.version)).filter_by(GUID=self.GUID).scalar()
        for key in self.__dict__:
            if key != '_sa_instance_state' and key != 'created_time' and key != 'modified_time' and key != 'modified_by' and key != 'id':
                new_assessment.__dict__[key] = self.__dict__[key]
        new_assessment.modified_by = current_user.id
        new_assessment.version = version + 1
        return new_assessment

    def is_versioning(self, id, name, test_type, test_center, year, review_period):
        if self.test_type != test_type:
            return True
        if self.branch_id != test_center:
            return True
        return False

    def __json__(self):
        return ['GUID', 'name', 'branch_id', 'test_type', 'year']

    def __repr__(self):
        return '<Assessment {}>'.format(self.name)


class AssessmentHasTestset(db.Model):
    """Assessment_has_testset Model: associate table """
    __tablename__ = 'assessment_testsets'

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessment.id'))
    testset_id = db.Column(db.Integer, db.ForeignKey('testset.id'))
    created_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    modified_by = db.Column(db.Integer)
    modified_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))

    assessment = db.relationship('Assessment', backref=db.backref('testset_asso', lazy='dynamic'))
    testset = db.relationship('Testset', backref=db.backref('assessment_asso', lazy='dynamic'))

    def clone(self):
        new_at = AssessmentHasTestset()
        for key in self.__dict__:
            if key != '_sa_instance_state' and key != 'created_time' and key != 'modified_time' and key != 'assessment_id' and key != 'id':
                new_at.__dict__[key] = self.__dict__[key]
        new_at.modified_by = current_user.id
        return new_at

    def __repr__(self):
        return '<Assessment has Testsets: {}>'.format(self.id)


class AssessmentEnroll(db.Model):
    """assessment enrollment Model: information which test taker enroll which assessment tet."""
    __tablename__ = 'assessment_enroll'

    id = db.Column(db.Integer, primary_key=True)
    # An assessment can have multiple versions but has only one GUID
    assessment_guid = db.Column(db.String(45))
    # Each assessment version has its own id.
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessment.id'))
    testset_id = db.Column(db.Integer, db.ForeignKey('testset.id'))
    student_user_id = db.Column(db.Integer, db.ForeignKey('student.user_id'))  # user table - id
    attempt_count = db.Column(db.Integer)
    grade = db.Column(db.String(10))
    test_center = db.Column(db.Integer)
    # Test runner session key
    session_key = db.Column(db.String(120))
    # Testlet stage change data
    stage_data = db.Column(JSONB)
    # Number of minutes the testset runs. 0 means no limit
    test_duration = db.Column(db.Integer, default=50)
    created_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    start_time = db.Column(db.DateTime)
    finish_time = db.Column(db.DateTime)
    start_time_client = db.Column(db.DateTime)
    finish_time_client = db.Column(db.DateTime)
    start_ip = db.Column(db.String(32))
    synced = db.Column(db.Boolean, default=False)
    synced_time = db.Column(db.DateTime)

    assessment = db.relationship('Assessment', back_populates="enroll")
    testset = db.relationship('Testset')
    student = db.relationship('Student', back_populates="enroll")
    marking = db.relationship('Marking', back_populates="enroll")

    def end_time(self, margin=11):
        if self.start_time:
            testset = Testset.query.filter_by(id=self.testset_id).first()
            return self.start_time + timedelta(minutes=testset.test_duration + margin)

    @property
    def is_finished(self):
        finished = self.finish_time is not None
        if not finished:
            elapsed = datetime.utcnow() - self.start_time
            if elapsed.total_seconds() > self.test_duration * 60 + 5:
                finished = True
        return finished

    @hybrid_property
    def markings(self):
        markings = Marking.query.filter_by(assessment_enroll_id=self.id).all()
        return markings

    def __json__(self):
        return ['id', 'assessment_guid', 'testset_id', 'attempt_count', 'start_time_client', "markings"]

    def __repr__(self):
        return '<Assessment Enrol {}>'.format(self.id)


class EducationPlan(db.Model):
    '''education_plan Model '''
    __tablename__ = 'education_plan'
    __table_args__ = (UniqueConstraint('GUID', 'version', name='education_plan_versioning_unique'),)

    id = db.Column(db.Integer, primary_key=True)
    GUID = db.Column(db.String(45))
    version = db.Column(db.Integer, default=1)
    name = db.Column(db.String(64))
    year = db.Column(db.String(4))
    grade = db.Column(db.Integer)
    test_type = db.Column(db.Integer)
    active = db.Column(db.Boolean, default=True)
    delete = db.Column(db.Boolean)
    modified_by = db.Column(db.Integer)
    modified_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    detail = db.relationship('EducationPlanDetail', backref='master_plan', lazy='dynamic')

    def versioning(self):
        new_ep = EducationPlan()
        version = db.session.query(func.max(EducationPlan.version)).filter_by(GUID=self.GUID).scalar()
        for key in self.__dict__:
            if key != '_sa_instance_state' and key != 'modified_time' and key != 'modified_by' and key != 'id':
                new_ep.__dict__[key] = self.__dict__[key]

        new_ep.modified_by = current_user.id
        new_ep.version = version + 1
        return new_ep

    def is_versioning(self, id, name, year, grade, test_type):
        if self.year != year:
            return True
        if self.grade != grade:
            return True
        if self.test_type != test_type:
            return True
        return False

    def __repr__(self):
        return '<Education Plan {}>'.format(self.id)


class EducationPlanDetail(db.Model):
    '''education_plan_details Model '''
    __tablename__ = 'education_plan_details'

    id = db.Column(db.Integer, primary_key=True)
    order = db.Column(db.Integer, index=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessment.id'))
    plan_id = db.Column(db.Integer, db.ForeignKey('education_plan.id'))
    modified_by = db.Column(db.Integer)
    modified_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))

    def clone(self):
        new_ep_detail = EducationPlanDetail()
        for key in self.__dict__:
            if key != '_sa_instance_state' and key != 'modified_time' and key != 'plan_id' and key != 'id':
                new_ep_detail.__dict__[key] = self.__dict__[key]
        new_ep_detail.modified_by = current_user.id
        return new_ep_detail

    @staticmethod
    def get_grade(assessment_id):
        epd = EducationPlanDetail.query. \
            filter(EducationPlanDetail.assessment_id == assessment_id). \
            order_by(EducationPlanDetail.modified_time.desc()).first()
        if epd:
            return Codebook.get_code_name(epd.master_plan.grade)
        else:
            return '-'

    def __repr__(self):
        return '<Assessment has Testsets: {}>'.format(self.id)


class Marking(db.Model):
    """marking Model: information of student marking status during the test"""
    __tablename__ = 'marking'

    id = db.Column(db.Integer, primary_key=True)
    question_no = db.Column(db.Integer)
    testset_id = db.Column(db.Integer)
    testlet_id = db.Column(db.Integer)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    weight = db.Column(db.Float)
    correct_r_value = db.Column(JSONB)  # Correct Response Value. Copy when row inserted
    candidate_r_value = db.Column(JSONB)  # Candidate Response Value
    is_correct = db.Column(db.Boolean)
    outcome_score = db.Column(db.Float, default=1)  # SetOutcome Score
    candidate_mark = db.Column(db.Float, default=0)  # Student's score
    duration = db.Column(db.Interval)  # time - time:duration, DB column type:Interval,Python Type: datetime.timedelta?
    # flag = db.Column(db.Boolean)
    is_read = db.Column(db.Boolean, default=False)
    is_flagged = db.Column(db.Boolean, default=False)
    assessment_enroll_id = db.Column(db.Integer, db.ForeignKey('assessment_enroll.id'))

    enroll = db.relationship('AssessmentEnroll', back_populates="marking")
    item = db.relationship('Item', back_populates="marking")
    created_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    modified_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    # Time read the related question
    read_time = db.Column(db.DateTime)

    @hybrid_property
    def scaled_outcome_score(self):
        return self.outcome_score * self.weight

    def getScore(self):
        score = self.candidate_mark * self.weight
        return score

    @staticmethod
    def getTotalOutcomeScore(assessment_enroll_id, testset_id, testlet_id):
        if assessment_enroll_id:
            total_score = Marking.query.with_entities(func.sum(Marking.scaled_outcome_score).label('score')). \
                filter_by(assessment_enroll_id=assessment_enroll_id, testset_id=testset_id,
                          testlet_id=testlet_id).first()
        else:
            # ToDo: Remove these lines when assessment_enroll_id fixed
            total_score = Marking.query.with_entities(func.sum(Marking.scaled_outcome_score).label('score')). \
                filter(Marking.testset_id == testset_id). \
                filter(Marking.testlet_id == testlet_id).first()

        return total_score.score

    def __json__(self):
        return ['question_no', 'testset_id', 'testlet_id', 'item_id', 'weight', \
                'is_correct', 'correct_r_value', 'candidate_r_value', 'scaled_outcome_score', 'candidate_mark']

    def __repr__(self):
        return '<Marking {}>'.format(self.id)


class MarkingBySimulater(db.Model):
    """marking by simulator Model: information of simulator marking status """
    __tablename__ = 'marking_bs'

    id = db.Column(db.Integer, primary_key=True)
    question_no = db.Column(db.Integer)
    testset_id = db.Column(db.Integer)
    testlet_id = db.Column(db.Integer)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    weight = db.Column(db.Float)
    correct_r_value = db.Column(JSONB)  # Correct Response Value. Copy when row inserted
    candidate_r_value = db.Column(JSONB)  # Candidate Response Value
    is_correct = db.Column(db.Boolean)
    outcome_score = db.Column(db.Float)  # SetOutcome Score
    candidate_mark = db.Column(db.Float)  # Student's score
    assessment_enroll_id = db.Column(db.Integer, db.ForeignKey('assessment_enroll.id'))

    created_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    modified_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))

    @hybrid_property
    def scaled_outcome_score(self):
        return self.outcome_score * self.weight

    def getScore(self):
        score = self.candidate_mark * self.weight
        return score

    @staticmethod
    def getTotalOutcomeScore(assessment_enroll_id, testset_id, testlet_id, attempt_count=1):
        if assessment_enroll_id:
            total_score = MarkingBySimulater.query.with_entities(
                func.sum(MarkingBySimulater.scaled_outcome_score).label('score')). \
                filter_by(assessment_enroll_id=assessment_enroll_id, testset_id=testset_id,
                          testlet_id=testlet_id, attempt_count=attempt_count).first()
        else:
            # ToDo: Remove these lines when assessment_enroll_id fixed
            total_score = MarkingBySimulater.query.with_entities(
                func.sum(MarkingBySimulater.scaled_outcome_score).label('score')). \
                filter(MarkingBySimulater.testset_id == testset_id). \
                filter(MarkingBySimulater.testlet_id == testlet_id).first()

        return total_score.score

    def __repr__(self):
        return '<Marking By Simulator {}>'.format(self.id)


class MarkingForWriting(db.Model):
    """marking for writing item Model: """
    __tablename__ = 'marking_writing'

    id = db.Column(db.Integer, primary_key=True)
    candidate_file_link = db.Column(
        JSONB)  # {"file1" :"file1_path", ... "filen" : "filen_path" } candidate response writing image file
    marked_file_link = db.Column(
        JSONB)  # {"file1" :"file1_path", ... "filen" : "filen_path" } marker's response image file
    candidate_mark_detail = db.Column(JSONB)  # {Codebook.id_for_c1 :1, Codebook.id_for_c2:1, Codebook.id_for_c3:1 ...}
    marking_id = db.Column(db.Integer, db.ForeignKey('marking.id'))
    markers_comment = db.Column(db.String(2048))
    marker_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    additional_info = db.Column(JSONB)  # JSON type
    created_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    modified_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))

    def is_mark_done(self):
        # Check markers_comment existing
        if self.markers_comment:
            if len(self.markers_comment) < 1:
                return False
        else:
            return False
        # Check candidate marking score existing
        if self.candidate_mark_detail:
            if len(self.candidate_mark_detail) < 1:
                return False
        else:
            return False

        return True

    def __repr__(self):
        return '<Marking Detail For Writing {}>'.format(self.id)


class MarkerAssigned(db.Model):
    """Marker assigned for writing Model: """
    __tablename__ = 'marker_assigned'
    __table_args__ = (UniqueConstraint('marker_id', 'assessment_id', name='marker_assessment_unique'),)

    id = db.Column(db.Integer, primary_key=True)
    marker_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessment.id'))
    delete = db.Column(db.Boolean)
    created_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    modified_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))

    def __repr__(self):
        return '<Marker Assigned For Writing Assessment {}>'.format(self.assessment_id)


class MarkerBranch(db.Model):
    """Marker linked to branch Model: """
    __tablename__ = 'marker_branch'
    __table_args__ = (UniqueConstraint('marker_id', 'branch_id', name='marker_branch_unique'),)

    id = db.Column(db.Integer, primary_key=True)
    marker_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    branch_id = db.Column(db.Integer, db.ForeignKey('codebook.id'))
    delete = db.Column(db.Boolean)
    created_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    modified_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))

    def __repr__(self):
        return '<Marker linked To Branch {}>'.format(self.branch_id)


class ScoreSummary(db.Model):
    '''score summary Model: information of score summary on each item. it is for the statistics  '''
    __tablename__ = 'score_summary'

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer)
    no_of_candidates = db.Column(db.Integer)
    no_of_correct = db.Column(db.Integer)
    no_of_incorrect = db.Column(db.Integer)
    session_date = db.Column(db.DateTime)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    created_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    modified_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))

    def __repr__(self):
        return '<Marking {}>'.format(self.id)


class Student(db.Model):
    '''student Model: test taker. '''
    __tablename__ = 'student'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    user = db.relationship('User', lazy='joined')
    student_id = db.Column(db.String(64), index=True)
    branch = db.Column(db.String(5), index=True)
    state = db.Column(db.String(5), index=True)
    created_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    modified_by = db.Column(db.Integer)
    modified_time = db.Column(db.DateTime, default=datetime.now(pytz.utc))
    last_access = db.Column(db.DateTime, default=datetime.now(pytz.utc))

    enroll = db.relationship('AssessmentEnroll', back_populates="student")

    @staticmethod
    def getCSStudentId(user_id):
        return (Student.query.filter_by(user_id=user_id).first()).student_id

    @staticmethod
    def getStudentUserId(cs_student_id):
        row = Student.query.filter_by(student_id=cs_student_id).first()
        if row:
            return (Student.query.filter_by(student_id=cs_student_id).first()).user_id
        else:
            return None

    @staticmethod
    def getCSStudentName(user_id):
        user = User.query.filter_by(id=user_id).first()
        if user:
            return user.username
        else:
            return 'Unknown User'

    @staticmethod
    def getCSCampusName(user_id):
        if user_id:
            branch_id = Student.query.filter_by(user_id=user_id).first().branch
            branch = Codebook.query.filter(Codebook.code_type == 'test_center',
                                           Codebook.additional_info.contains({"campus_prefix": branch_id})).first()
            if branch:
                return branch.code_name

    @hybrid_property
    def branch_name(self):
        return Codebook.query.filter(Codebook.code_type == 'test_center',
                                     Codebook.additional_info.contains({"campus_prefix": self.branch})).first()

    def __json__(self):
        return ['user_id', 'student_id', 'branch_name', 'last_access', 'user']

    def __repr__(self):
        return '<Student {}>'.format(self.user_id)


class Codebook(db.Model):
    '''Codebook: to be used in various cases mainly in templates '''

    __tablename__ = 'codebook'

    id = db.Column(db.Integer, primary_key=True)
    code_type = db.Column(db.String(255), index=True)
    code_name = db.Column(db.String(255))
    parent_code = db.Column(db.Integer, db.ForeignKey('codebook.id'))
    additional_info = db.Column(
        JSONB)  # {"state":"", "suburb":"", "address":"", "country":"", "hq_flag":"", "postcode": "",

    # "centre_type": "", "contact_fax": "", "contact_tel": "", "campus_title": "",
    # "activate_flag": "", "campus_prefix": "", "email_address": ""}

    def get_parent_name(self):
        v_parent = Codebook.query.filter_by(id=self.parent_code).first()
        return v_parent.code_name

    @staticmethod
    def get_code_name(code_id):
        code = Codebook.query.filter_by(id=code_id).first()
        if code is None:
            return '-'
        return code.code_name

    @staticmethod
    def get_subject_name(testset_id):
        ts = db.session.query(Testset.subject).filter_by(id=testset_id).first()
        if ts is None:
            return '-'
        return Codebook.get_code_name(ts[0])

    @staticmethod
    def get_code_id(code_name):
        code = Codebook.query.options(load_only("id")).filter_by(code_name=code_name).first()
        if code:
            return code.id
        else:
            return 0

    @staticmethod
    def get_testcenter_by_ip(ip):
        return Codebook.query.filter(Codebook.code_type == 'test_center',
                                     Codebook.additional_info.contains({"ip": [ip]})).first()

    @staticmethod
    def get_testcenter_of_current_user():
        student = Student.query.filter_by(user_id=current_user.id).first()
        if student:
            return Codebook.query.filter(Codebook.code_type == 'test_center',
                                         Codebook.additional_info.contains({"campus_prefix": student.branch})).first()

    @staticmethod
    def get_additional_info(code_id):
        code = Codebook.query.filter_by(id=code_id).first()
        if code:
            return code.additional_info

    @staticmethod
    def get_childlist(parent_id):
        childlist = [(row.id, row.code_name) for row in Codebook.query.filter_by(parent_code=parent_id).all()]
        return childlist

    @staticmethod
    # Category/Subcategory update
    def create_default_category(subject, *argv):
        # new subject creation
        m_subject = Codebook.query.filter_by(code_name=subject).first()
        if not m_subject:
            m_subject = Codebook(code_type='subject', code_name=subject)
            db.session.add(m_subject)
            db.session.commit()
            print("Codebook: parent '{}' created.".format(subject))

        # new category creation
        for arg in argv:
            category = Codebook.query.filter(Codebook.parent_code == m_subject.id).filter(
                Codebook.code_name == arg).first()
            if not category:
                if m_subject.code_type == 'subject':
                    category = Codebook(code_type='category', code_name=arg, parent_code=m_subject.id)
                else:  # subcategory
                    category = Codebook(code_type='subcategory', code_name=arg, parent_code=m_subject.id)
                db.session.add(category)
                db.session.commit()
            else:
                print("Already created child '{}' under parent '{}'.".format(arg, subject))
            print("Codebook: child '{}'  created under parent '{}'.".format(arg, subject))

    @staticmethod
    # code_type/code_name creation
    def create_default_codeset(parent_type, type, *argv):
        v_code_type = type
        if parent_type is not None:
            parent_row = Codebook.query.filter_by(code_name=parent_type).first()
        else:
            parent_row = None
        print("Codebook: ".format(v_code_type))
        if parent_row:
            for arg in argv:
                v_code = Codebook.query.filter(Codebook.code_type == v_code_type).filter(
                    Codebook.parent_code == parent_row.id).filter(Codebook.code_name == arg).first()
                if not v_code:
                    v_code = Codebook(code_type=v_code_type, code_name=arg, parent_code=parent_row.id)
                    db.session.add(v_code)
                    db.session.commit()
                    print("- {}-{} code".format(v_code_type, arg))
                else:
                    print("Already created code {}-{}.".format(v_code_type, arg))
        else:
            for arg in argv:
                v_code = Codebook.query.filter(Codebook.code_type == v_code_type).filter(
                    Codebook.code_name == arg).first()
                if not v_code:
                    v_code = Codebook(code_type=v_code_type, code_name=arg)
                    db.session.add(v_code)
                    db.session.commit()
                    print("- {}-{} code".format(v_code_type, arg))
                else:
                    print("Already created code {}-{}.".format(v_code_type, arg))
        print("Created.")

    def __repr__(self):
        return '<Codebook {}: {}>'.format(self.code_type, self.code_name)


class Choices:
    grade_choices = []
    subject_choices = []
    level_choices = []
    category_choices = []
    subcategory_choices = []

    def __init__(self):
        self.grade_choices = self.get_codes('grade')
        self.subject_choices = self.get_codes('subject')
        self.level_choices = self.get_codes('level')
        self.category_choices = self.get_codes('category')
        self.subcategory_choices = self.get_codes('subcategory')

    @staticmethod
    def get_codes(type):
        codesets = Codebook.query.filter_by(code_type=type).all()
        my_codesets = [(0, '')]
        if codesets:
            for codeset in codesets:
                code = (codeset.id, codeset.code_name)
                my_codesets.append(code)
        return sort_codes(my_codesets)

    @staticmethod
    def get_codes_child(parent_id):
        codesets = Codebook.query.filter_by(parent_code=parent_id).all()
        my_codesests = [(0, '')]
        if codesets:
            for codeset in codesets:
                code = (codeset.id, codeset.code_name)
                my_codesests.append(code)
            return sort_codes(my_codesests)
        else:
            return my_codesests

    @staticmethod
    def get_ty_choices():
        from datetime import datetime
        current_year = datetime.now().year

        my_codesets = [('', '')]
        for i in range(0, 2):
            current_year = i + current_year
            my_codesets.append((str(current_year), str(current_year)))
        return my_codesets

    @staticmethod
    def get_branch_state_choices():
        b_state = current_app.config['CS_BRANCH_STATES']
        return [(state, state) for state in b_state.keys()]


class Weights:
    def get_weight(testlet_id, level):
        row = TestletWeight.query.filter_by(level=level).filter_by(testlet_id=testlet_id).first()
        if row:
            return row.weight
        else:
            return 1


def atoi(text):
    return int(text) if text.isdigit() else text


def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    return [atoi(c) for c in re.split(r'(\d+)', text)]


def sort_codes(codesets):
    if len(codesets) > 1:
        codesets.sort(key=lambda x: natural_keys(x[1]))
    return codesets


# Refresh materialized views
def refresh_mviews():
    for v in ['refresh materialized view marking_summary_360_degree_mview;',
              'refresh materialized view marking_summary_by_category_360_degree_mview;',
              'refresh materialized view test_summary_mview;']:
        db.engine.execute(v)

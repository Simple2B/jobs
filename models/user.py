import json
import flask
from sqlalchemy import Column, Integer, String, Boolean, Enum  # , ForeignKey
from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import relationship
from session import db_engine
from secrets import token_hex
from flask_mail import Mail, Message
from config import config
from .user_role import UserRole
from .auth_type import AuthType
from logger import log

ModelBase = declarative_base(bind=db_engine)


class User(ModelBase):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    password = Column(String)
    role = Column(Enum(UserRole))  # , ForeignKey('user_role.name'))
    auth_type = Column(String)
    oauth_id = Column(String)
    oauth_access_token = Column(String)
    # user_role = relationship("UserRole")
    is_active = Column(Boolean)
    is_email_confirmed = Column(Boolean)
    email_confirmation_token = Column(String)
    is_test_completed = Column(Boolean)
    test_results = Column(String)

    def __init__(self, name, email, passwd, role: UserRole, auth_type: AuthType = AuthType.login_pwd,
                 oauth_id=None, oauth_access_token=None):
        self.name = name
        self.email = email
        self.password = passwd
        self.role = role.value
        self.auth_type = auth_type
        self.oauth_id = oauth_id
        self.oauth_access_token = oauth_access_token
        self.is_active = True
        self.is_email_confirmed = False
        self.is_test_completed = False
        self.test_results = None

    def generate_email_confirmation_token(self):
        self.email_confirmation_token = token_hex(32)
        log(log.DEBUG, 'debug: email_confirmation_token = %s', self.email_confirmation_token)

    def send_confirmation_email(self, mail: Mail):
        email_settings = config["confirmation_email"]
        subject = email_settings["SUBJECT"]
        recipients = [self.email]
        sender = email_settings["SENDER"]
        msg_template = email_settings["MSG_TEMPLATE"]
        html = msg_template.format(host=flask.request.host, token=self.email_confirmation_token)
        confirm_msg = Message(subject=subject, recipients=recipients, sender=sender, html=html)
        test_username = config["selenium"]["TEST_USERNAME"]
        if self.name != test_username:
            mail.send(confirm_msg)

    def to_dict(self) -> dict:
        """ convert to dict """
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "password": self.password,
            "role": self.role,
            "auth_type": self.auth_type,
            "oauth_id": self.oauth_id,
            "oauth_access_token": self.oauth_access_token,
            "is_active": self.is_active,
            "email_conf": self.is_email_confirmed,
            "test_results": self.test_results
            # TODO для нормального отображения вопросов в админской консоли
            # https://stackoverflow.com/questions/18337407/saving-utf-8-texts-in-json-dumps-as-utf8-not-as-u-escape-sequence
        }

    def values(self) -> list:
        return [
            self.id,
            self.name,
            self.email,
            self.password,
            self.role,
            self.auth_type,
            self.oauth_id,
            self.oauth_access_token,
            self.is_active,
            self.is_email_confirmed,
            self.rating
        ]

    @property
    def rating(self) -> str:
        if self.test_results is None:
            return 'Unknown'
        res = json.loads(self.test_results)
        total = len(res)
        correct_list = [i for i in res if int(i['correct_index']) == int(i['user_answer'])]
        correct = len(correct_list)
        return '({correct}/{total})'.format(correct=correct, total=total)

    def __repr__(self):
        if self.is_test_completed:
            results = json.loads(self.test_results)
        else:
            results = ""
        print_template = """id: {}\tname: {}\tpassword: {}\temail: {}\trole: {}\tauth_type: {}\toauth_id: {}\toauth_access_token: {}\tis_active: {}
            is_email_confirmed: {}\temail_confirmation_token: {}\tis_test_completed: {}\ttest_results:\n\t{}
            ------------------------"""
        return print_template.format(
            self.id, self.name, self.password, self.email, self.role,
            self.auth_type, self.oauth_id, self.oauth_access_token, self.is_active, self.is_email_confirmed,
            self.email_confirmation_token, self.is_test_completed, results)

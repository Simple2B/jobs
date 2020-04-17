import enum
from sqlalchemy import Column, Integer, String, Boolean, Enum  # , ForeignKey
from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import relationship
from session import db_engine
from secrets import token_hex
from flask_mail import Mail, Message
import json

ModelBase = declarative_base(bind=db_engine)


class UserRole(enum.Enum):
    admin = 'admin'
    user = 'user'
    guest = 'guest'


class User(ModelBase):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    password = Column(String)
    role = Column(Enum(UserRole))  # , ForeignKey('user_role.name'))
    # user_role = relationship("UserRole")
    is_active = Column(Boolean)
    is_email_confirmed = Column(Boolean)
    email_confirmation_token = Column(String)
    is_test_completed = Column(Boolean)
    test_results = Column(String)

    def __init__(self, name, email, passwd, role: UserRole):
        self.name = name
        self.email = email
        self.password = passwd
        self.role = role.value
        self.is_active = True
        self.is_email_confirmed = False
        self.is_test_completed = False
        self.test_results = None

    def generate_email_confirmation_token(self):
        self.email_confirmation_token = token_hex(32)
        print("debug: email_confirmation_token = ", self.email_confirmation_token)

    def send_confirmation_email(self, mail: Mail):
        # TODO if not flask.configuration['TESTING']:
        email_settings = json.load(open("config.json"))["confirmation_email"]
        host = email_settings["HOST"]
        subject = email_settings["SUBJECT"]
        recipients = [self.email]
        sender = email_settings["SENDER"]
        msg_template = email_settings["MSG_TEMPLATE"]
        html = msg_template.format(host=host, token=self.email_confirmation_token)
        confirm_msg = Message(subject=subject, recipients=recipients, sender=sender, html=html)
        mail.send(confirm_msg)

    def to_dict(self) -> dict:
        """ convert to dict """
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "password": self.password,
            "role": self.role,
            "is_active": self.is_active,
            "email_conf": self.is_email_confirmed,
            "test_results": self.test_results
            # TODO для нормального отображения вопросов в админской консоли
            # https://stackoverflow.com/questions/18337407/saving-utf-8-texts-in-json-dumps-as-utf8-not-as-u-escape-sequence
        }

    def __repr__(self):
        if self.is_test_completed:
            results = json.loads(self.test_results)
        else:
            results = ""
        print_template = """id: {}\tname: {}\tpassword: {}\temail: {}\trole: {}\tis_active: {}
            is_email_confirmed: {}\temail_confirmation_token: {}\tis_test_completed: {}\ttest_results:\n\t{}
            ------------------------"""
        return print_template.format(self.id, self.name, self.password, self.email, self.role,
                                     self.is_active, self.is_email_confirmed,
                                     self.email_confirmation_token, self.is_test_completed, results)

# в sqlite по умолчанию отключены foreign keys (https://www.sqlite.org/foreignkeys.html пункт 2)
# включать их - много мороки, а пользы мало: только возможность прои создании пользователя убедиться, что такая роль существует
# class UserRole(ModelBase):

#     __tablename__: str = 'user_role'

#     name = Column(String, primary_key=True)
#     # users = relationship('User', backref='users', lazy='dynamic')

#     def __init__(self, name):
#         self.name = name

#     def __repr__(self):
#         return "name {}".format(self.name)

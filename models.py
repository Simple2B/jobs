from sqlalchemy import Column, Integer, String, Boolean  # , ForeignKey
from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import relationship
from session import db_engine
from enum import Enum
from secrets import token_hex
from flask_mail import Mail, Message
import json

ModelBase = declarative_base(bind=db_engine)


class UserRoleEnum(Enum):
    ADMIN = 'admin'
    USER = 'user'
    GUEST = 'guest'


class User(ModelBase):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    password = Column(String)
    role = Column(String)  # , ForeignKey('user_role.name'))
    # user_role = relationship("UserRole")
    is_active = Column(Boolean)
    is_email_confirmed = Column(Boolean)
    email_confirmation_token = Column(String)
    test_results = Column(String)

    def __init__(self, name, email, passwd, role: UserRoleEnum):
        self.name = name
        self.email = email
        self.password = passwd
        self.role = role.value
        self.is_active = True
        self.is_email_confirmed = False
        self.test_results = None

    def generate_email_confirmation_token(self):
        self.email_confirmation_token = token_hex(32)
        print("debug: email_confirmation_token = ", self.email_confirmation_token)

    def send_confirmation_email(self, mail: Mail):
        host = "localhost:5000"  # TODO: global variable
        subject = 'Confirm registration on simple2b.com'
        recipients = [self.email]
        sender = 'info@simple2b.com'
        msg_template = "<p>confirmation link: http://{host}/confirm_email?token={token}</p>"
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
            "is_email_confirmed": self.is_email_confirmed,
            "email_confirmation_token": self.email_confirmation_token
        }

    def __repr__(self):
        results = ""
        try:
            results = json.loads(self.test_results)
        except:
            pass
        print_template = """id: {}\tname: {}\temail: {}\trole: {}\tis_active: {}
\tis_email_confirmed: {}\temail_confirmation_token: {}\ttest_results: {}"""
        return print_template.format(self.id, self.name, self.email, self.role,
                                     self.is_active, self.is_email_confirmed, self.email_confirmation_token, results)

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

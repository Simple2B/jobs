from sqlalchemy import Column, Integer, String  # , ForeignKey
from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import relationship
from session import db_engine
from enum import Enum

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

    def __init__(self, name, email, passwd, role: UserRoleEnum):
        self.name = name
        self.email = email
        self.password = passwd
        self.role = role.value

    def __repr__(self):
        return "id: {}\tname: {}\temail: {}\trole: {}".format(self.id, self.name, self.email, self.role)

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

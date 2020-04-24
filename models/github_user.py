from models import User
from sqlalchemy import Column, String, Integer, ForeignKey


class GithubUser(User):
    __tablename__ = 'github_users'

    id = Column(None, ForeignKey('users.id'), primary_key=True)
    github_access_token = Column(String(255))
    github_id = Column(Integer)
    github_login = Column(String(255))

    def __init__(self, name, email, passwd, role, github_access_token, github_id, github_login):
        User.__init__(self, name, email, passwd, role)
        self.github_access_token = github_access_token
        self.github_id = github_id
        self.github_login = github_login

    def __repr__(self):
        return User.__repr__(self) + "\ngithub_id: {}\t, github_login: {}".format(self.github_id, self.github_login)

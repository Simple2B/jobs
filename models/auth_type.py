import enum


class AuthType(enum.Enum):
    login_pwd = 'login_pwd'
    github = 'github'
    facebook = 'facebook'
    google = 'google'

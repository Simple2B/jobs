# -*- coding: utf-8 -*-
import os
from invoke import task  # noqa
from models import ModelBase, User, UserRole  # , UserRole
from session import db_session_ctx


@task
def renew_db(_):
    """
    Пересоздание БД
    """
    from secret_settings import admin_email, admin_name, admin_password
    ModelBase.metadata.drop_all()
    ModelBase.metadata.create_all()
    with db_session_ctx(read_only=False) as dsession:
        # role_admin = UserRole('admin')
        admin = User(name=admin_name, email=admin_email, passwd=admin_password, role=UserRole.admin)
        admin.is_email_confirmed = True
        test_user = User(name='ton_user', email='an.malyshko@gmail.com', passwd='123', role=UserRole.user)
        test_user.is_email_confirmed = True
        # session.add(role_admin)
        dsession.add(admin)
        dsession.add(test_user)


@task
def print_db(_):
    with db_session_ctx(read_only=True) as session:
        all = session.query(User).all()
        print("database users:")
        for user in all:
            print(user)


@task
def renew_config(_, passwd):
    """Using: renew_config <passwd>
    """
    os.system('echo A | unzip -P {} config.zip'.format(passwd))


@task
def zip_config(_, passwd):
    """Using: zip_config <passwd>
    """
    os.system('zip -P {} config.zip config.json secret_settings.py'.format(passwd))

from invoke import task  # noqa
from models import ModelBase, User, UserRoleEnum  # , UserRole
from session import DbSession, db_session_ctx


@task
def renew_db(_):
    ModelBase.metadata.drop_all()
    ModelBase.metadata.create_all()
    session = DbSession()
    # role_admin = UserRole('admin')
    ton = User(name='ton', email='ton@gmail.com', passwd='123', role=UserRoleEnum.ADMIN.value)
    # session.add(role_admin)
    session.add(ton)
    session.commit()


@task
def print_db(_):
    with db_session_ctx(read_only=True) as session:
        all = session.query(User).all()
        print("database users:")
        for user in all:
            print(user)
        # all = session.query(UserRole).all()
        # print("user roles:")
        # for role in all:
        #     print(role)

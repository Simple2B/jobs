from flask import Flask, render_template, session, request, redirect
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired
from session import db_session_ctx
from models import User, UserRoleEnum
from flask_mail import Mail
import secret_settings

app = Flask(__name__)
app.secret_key = secret_settings.app_secret_key

app.config.update(dict(
    DEBUG=False,
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USE_SSL=False,
    MAIL_USERNAME='info.simple2b@gmail.com',
    MAIL_PASSWORD=secret_settings.gmail_account_application_password
))

mail = Mail(app)


class LoginForm(FlaskForm):
    username = StringField('username', validators=[DataRequired()])
    password = StringField('password', validators=[DataRequired()])

    @property
    def name(self):
        return self.username.data

    @property
    def passwd(self):
        return self.password.data


class SignupForm(LoginForm):
    email = StringField('email', validators=[DataRequired()])

    @property
    def e_mail(self):
        return self.email.data


def is_user_logged_in():
    return 'user_id' in session


def fetch_user_by_id():
    with db_session_ctx(read_only=True) as dbses:
        user: User = dbses.query(User).filter(User.id == session['user_id']).first()
        return user


@app.route("/")
def home():
    if not is_user_logged_in():
        return render_template("landing.html", form=LoginForm())
    user = fetch_user_by_id()
    if not user.is_active:
        return "User is inactive"
    if not user.is_email_confirmed:
        return render_template("confirm_email.html", user=user)
    if user.role == UserRoleEnum.ADMIN.value:
        return redirect("/admin", 302)
    # TODO if user.is_test_passed: redirect("/thankyou")
    return "TODO would you like to pass a test?"


@app.route("/login", methods=['POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        with db_session_ctx(read_only=True) as dsession:
            user: User = dsession.query(User).filter(User.name == form.name).first()
            if user and user.password == form.passwd:
                session['user_id'] = user.id
                return redirect("/", 200)
            else:
                return "no such user"
    else:
        return "error in form"


@app.route("/signup", methods=['POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        with db_session_ctx(read_only=False) as dsession:
            user = dsession.query(User).filter(User.name == form.name).first()
            if user:
                return "user {} already exists".format(form.name)
            else:
                new_user = User(form.name, form.e_mail, form.passwd, UserRoleEnum.USER)
                new_user.send_confirmation_email(mail)
                dsession.add(new_user)
                return "user {} created".format(new_user.name)
    else:
        return render_template("landing.html", form=form, role=session['role'])


@app.route("/confirm_email", methods=['GET'])
def confirm():
    token = request.args.get('token')
    if token is None:
        if not is_user_logged_in():
            return redirect("/", 403)
        else:
            return render_template("confirm_email.html", user=fetch_user_by_id())
    with db_session_ctx(read_only=False) as dsession:
        user = dsession.query(User).filter(User.email_confirmation_token == token).first()
        if user is None:
            return "token expired or does not exist"
        else:
            if user.is_email_confirmed:
                return "email already confirmed"
            user.is_email_confirmed = True
            return "email successfully confirmed"


@app.route("/confirm_email/resend", methods=['POST'])
def resend():
    if 'user_id' not in session:
        return redirect("/", 302)
    else:
        user_id = session['user_id']
        with db_session_ctx() as dsession:
            user: User = dsession.query(User).filter(User.id == user_id).first()
            user.send_confirmation_email(mail)
            return "check your mail"


@app.route("/admin", methods=['GET'])
def admin_console():
    if 'user_id' not in session:
        return redirect("/", 403)
    user_id = session['user_id']
    with db_session_ctx(read_only=True) as dbses:
        user = dbses.query(User).filter(User.id == user_id).first()
        if user.role != UserRoleEnum.ADMIN.value:
            return redirect("/", 403)
        else:
            return render_template("admin_console.html", users=dbses.query(User).all())


@app.route('/logout', methods=['POST'])
def logout():
    if 'user_id' in session:
        session.pop('user_id')
    return render_template("landing.html", form=LoginForm())

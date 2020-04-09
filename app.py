from flask import Flask, render_template, session
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


@app.route("/")
def home():
    if 'role' not in session:
        session['role'] = UserRoleEnum.GUEST.value
    return render_template("landing.html", form=LoginForm(), role=session['role'])


@app.route("/login", methods=['POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        with db_session_ctx(read_only=True) as dsession:
            user: User = dsession.query(User).filter(User.name == form.name).first()
            if user and user.password == form.passwd:
                session['role'] = user.role
                if not user.is_active:
                    return "User is inactive"
                if not user.is_email_confirmed:
                    return render_template("confirm_email.html", user=user)
            else:
                return "no such user"
    else:
        return "error in form"


@app.route("/signup", methods=['POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        with db_session_ctx(read_only=True) as dsession:
            user = dsession.query(User).filter(User.name == form.name).first()
            if user:
                return "user {} already exists".format(form.name)
            else:
                new_user = User(form.name, form.e_mail, form.passwd, UserRoleEnum.USER)
                new_user.send_confirmation_email(mail)
                dsession.add(new_user)
                dsession.commit()
                return "user {} created".format(new_user.name)
    else:
        return render_template("landing.html", form=form, role=session['role'])

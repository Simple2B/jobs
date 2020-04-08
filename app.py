from flask import Flask, render_template, session
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired
from session import db_session_ctx
from models import User, UserRoleEnum

app = Flask(__name__)
app.secret_key = "adlfkhLSDHFlkshfsdbfnBSMDNFBSkjweKDFJhsldkjhf"


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
            user = dsession.query(User).filter(User.name == form.name).first()
            if user and user.password == form.passwd:
                session['role'] = user.role
                return "hello, {}".format(form.name)
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
                dsession.add(new_user)
                dsession.commit()
                return "user {} created".format(new_user.name)
    else:
        return render_template("landing.html", form=form, role=session['role'])

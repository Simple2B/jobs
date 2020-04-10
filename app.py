from flask import Flask, render_template, session, request, redirect
from flask_mail import Mail
from forms.login_form import LoginForm
from forms.signup_form import SignupForm
from forms.exam_form import ExamForm
from models import User, UserRoleEnum
from exam.skilltest import SkillTest
from session import db_session_ctx
import secret_settings
import json


app = Flask(__name__)
app.secret_key = secret_settings.app_secret_key

config = json.load(open("config.json"))
app.config.update(config['mailer'])

mail = Mail(app)


def is_user_logged_in():
    return 'user_id' in session


def fetch_user_by_id():
    with db_session_ctx(read_only=True) as db:
        user: User = db.query(User).filter(User.id == session['user_id']).first()
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
    return render_template("test_invitation.html", username=user.name)


@app.route("/login", methods=['POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        with db_session_ctx(read_only=True) as db:
            user: User = db.query(User).filter(User.name == form.name).first()
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
        user = None  # for return
        with db_session_ctx() as db:
            user = db.query(User).filter(User.name == form.name).first()
            if user:
                return "user {} already exists".format(form.name)
            else:
                new_user = User(form.name, form.e_mail, form.passwd, UserRoleEnum.USER)
                db.add(new_user)
        with db_session_ctx() as db:
            user = db.query(User).filter(User.name == form.name).first()
            user.generate_email_confirmation_token()
            user.send_confirmation_email(mail)
            return "user {} created".format(user.name)

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
            user.generate_email_confirmation_token()
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


@app.route('/skill_test', methods=['GET'])
def skill_test_get():
    if not is_user_logged_in():
        return redirect("/", 403)
    skt = SkillTest()
    return render_template("skill_test.html", skill_test=skt)


@app.route('/skill_test', methods=['POST'])
def skill_test_post():
    if not is_user_logged_in():
        return redirect("/", 403)
    exam_form = ExamForm()
    user_answers = exam_form.user_answers.data
    print(json.loads(user_answers))
    return "thank you!"

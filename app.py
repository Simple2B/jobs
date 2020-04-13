from flask import Flask, render_template, session, request, redirect
import json
from flask_mail import Mail
from forms.login_form import LoginForm
from forms.signup_form import SignupForm
from forms.exam_form import ExamForm
from models import User, UserRoleEnum
from exam.skilltest import SkillTest
from session import db_session_ctx
import secret_settings
import messages


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


def simple_message(message):
    return render_template("simple_message.html", message=message)


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
        return admin_console()
    if not user.is_test_completed:
        return render_template("test_invitation.html", username=user.name)
    return simple_message(messages.TEST_COMPLETED)


@app.route("/login", methods=['POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        with db_session_ctx(read_only=True) as db:
            user: User = db.query(User).filter(User.name == form.name).first()
            if user and user.password == form.passwd:
                session['user_id'] = user.id
                return redirect("/")
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
            return render_template("confirm_email.html", user=user)

    else:
        return render_template("landing.html", form=form)


@app.route("/confirm_email", methods=['GET'])
def confirm():
    token = request.args.get('token')
    if token is None:
        if not is_user_logged_in():
            return redirect("/")
        else:
            user = fetch_user_by_id()
            if not user.is_email_confirmed:
                return render_template("confirm_email.html", user=user)
            else:
                return simple_message(messages.EMAIL_ALREADY_CONFIRMED)
    with db_session_ctx(read_only=False) as dsession:
        user = dsession.query(User).filter(User.email_confirmation_token == token).first()
        if user is None:
            return simple_message(messages.NO_SUCH_EMAIL_CONFIRMATION_TOKEN)
        else:
            if user.is_email_confirmed:
                return simple_message(messages.EMAIL_ALREADY_CONFIRMED)
            user.is_email_confirmed = True
            return simple_message(messages.EMAIL_CONFIRMED)


@app.route("/confirm_email/resend", methods=['POST'])
def resend():
    if 'user_id' not in session:
        return redirect("/")
    else:
        user_id = session['user_id']
        with db_session_ctx() as dsession:
            user: User = dsession.query(User).filter(User.id == user_id).first()
            if user.is_email_confirmed:
                return simple_message(messages.EMAIL_ALREADY_CONFIRMED)
            user.generate_email_confirmation_token()
            user.send_confirmation_email(mail)
        return simple_message(messages.NEW_EMAIL_CONFIRMATION_TOKEN_SENT)


@app.route("/admin", methods=['GET', 'POST'])
def admin_console():
    if 'user_id' not in session:
        return redirect("/")
    admin_id = session['user_id']
    with db_session_ctx() as db:
        admin = db.query(User).filter(User.id == admin_id).first()
        if admin.role != UserRoleEnum.ADMIN.value:
            return redirect("/")
        else:
            if request.method == 'GET':
                return render_template("admin_console.html", users=db.query(User).all())
            if request.method == 'POST':
                print(request.form['admin_action'])
                print(request.form['selected_users'])
                for user_id in json.loads(request.form['selected_users']):
                    user = db.query(User).filter(User.id == user_id).first()
                    if user is None:
                        # TODO proper error display
                        return "error: no user with id {}".format(user_id)
                    if request.form['admin_action'] == "ban":
                        user.is_active = False
                    if request.form['admin_action'] == "unban":
                        user.is_active = True
                    if request.form['admin_action'] == "make_admin":
                        user.role = UserRoleEnum.ADMIN.value
                    if request.form['admin_action'] == "make_user":
                        user.role = UserRoleEnum.USER.value
                return redirect("/", 302)
                # admin console ban and make admin actions


@app.route('/logout', methods=['POST'])
def logout():
    if 'user_id' in session:
        session.pop('user_id')
    return render_template("landing.html", form=LoginForm())


@app.route('/skill_test', methods=['GET'])
def skill_test_get():
    if not is_user_logged_in():
        return redirect("/")
    skt = SkillTest()
    return render_template("skill_test.html", skill_test=skt)


@app.route('/skill_test', methods=['POST'])
def skill_test_post():
    if not is_user_logged_in():
        return redirect("/")
    if fetch_user_by_id().is_test_completed:
        return simple_message(messages.REPEAT_TEST_SUBMIT)
    exam_form = ExamForm()
    user_answers = exam_form.user_answers.data
    print(user_answers)
    user_answers_json = json.loads(user_answers)
    user_answers_array = []
    for a_dict in user_answers_json:
        user_answers_array.append(user_answers_json[a_dict])
    print("user answers: ", user_answers_array)

    with db_session_ctx() as db:
        user = db.query(User).filter(User.id == session['user_id']).first()
        user.test_results = json.dumps(SkillTest().as_list_with_answers(user_answers_array))
        user.is_test_completed = True
    return simple_message(messages.TEST_COMPLETED)

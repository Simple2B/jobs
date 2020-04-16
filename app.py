import flask
import json
from flask_mail import Mail
from forms.login_form import LoginForm
from forms.signup_form import SignupForm
from forms.exam_form import ExamForm
from models import User, UserRole
from exam.skilltest import SkillTest
from session import db_session_ctx
import secret_settings
import messages
from logger import log


app = flask.Flask(__name__)
app.secret_key = secret_settings.app_secret_key

config = json.load(open("config.json"))
app.config.update(config['mailer'])

mail = Mail(app)


def is_user_logged_in():
    return 'user_id' in flask.session


def fetch_user_by_id():
    with db_session_ctx(read_only=True) as db:
        user: User = db.query(User).filter(User.id == flask.session['user_id']).first()
        return user


def simple_message(message):
    return flask.render_template("simple_message.html", message=message)


@app.route("/")
def home():
    if not is_user_logged_in():
        # TODO flask.request.remote_addr returns 10.0.0.121, not actual adress
        log(log.INFO, "Guest connected from addr %s", flask.request.remote_addr)
        return flask.redirect("/login")
    user = fetch_user_by_id()
    if not user.is_active:
        return "User is banned"
    if not user.is_email_confirmed:
        return flask.render_template("confirm_email.html", user=user)
    if user.role == UserRole.admin:
        return admin_console()
    if not user.is_test_completed:
        return flask.render_template("test_invitation.html", username=user.name)
    return simple_message(messages.TEST_COMPLETED)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if flask.request.method == 'GET':
        return flask.render_template("login.html", form=LoginForm())
    form = LoginForm()
    if form.validate_on_submit():
        with db_session_ctx(read_only=True) as db:
            user: User = db.query(User).filter(User.name == form.name).first()
            if user and user.password == form.passwd:
                flask.session['user_id'] = user.id
                log(log.INFO, "User {username} (id: {id}) logged in".format(username=user.name, id=user.id))
                return flask.redirect("/")
            else:
                log(log.ERROR, "Failed login attempt for user {} (id: {}) from addr {}"
                    .format(form.name, user.id if user else None, flask.request.remote_addr))
                return flask.render_template("simple_message.html", message=messages.NO_SUCH_USER)
    else:
        log(log.INFO, "Invalid login form submit from addr {}".format(flask.request.remote_addr))
        return "error in form"


@app.route("/join", methods=['GET'])
def signup_get():
    return flask.render_template('join.html', form=SignupForm())


@app.route("/signup", methods=['POST'])
#  TODO HASH
def signup_post():
    form = SignupForm()
    if form.validate_on_submit():
        user = None  # for return
        with db_session_ctx() as db:
            user = db.query(User).filter(User.name == form.name).first()
            if user:
                log(log.INFO, "Attempt to create already existing user {} (id: {}) from addr {}"
                    .format(user.name, user.id, flask.request.remote_addr))
                return "user {} already exists".format(form.name)
            else:
                new_user = User(form.name, form.e_mail, form.passwd, UserRole.user)
                db.add(new_user)
                log(log.INFO, "User created: {}".format(new_user))
        with db_session_ctx() as db:
            user = db.query(User).filter(User.name == form.name).first()
            user.generate_email_confirmation_token()
            user.send_confirmation_email(mail)
            return flask.render_template("confirm_email.html", user=user)
    else:
        return flask.render_template("join.html", form=form)


@app.route("/confirm_email", methods=['GET'])
def confirm():
    token = flask.request.args.get('token')
    if token is None:
        if not is_user_logged_in():
            return flask.redirect("/")
        else:
            user = fetch_user_by_id()
            if not user.is_email_confirmed:
                return flask.render_template("confirm_email.html", user=user)
            else:
                return simple_message(messages.EMAIL_ALREADY_CONFIRMED)
    with db_session_ctx(read_only=False) as dsession:
        user = dsession.query(User).filter(User.email_confirmation_token == token).first()
        if user is None:
            log(log.INFO, "User {} (id: {}) tried to confirm his email {} with invalid token {}"
                .format(user.name, user.id, user.email, token))
            return simple_message(messages.NO_SUCH_EMAIL_CONFIRMATION_TOKEN)
        else:
            if user.is_email_confirmed:
                return simple_message(messages.EMAIL_ALREADY_CONFIRMED)
            user.is_email_confirmed = True
            log(log.INFO, "User {} (id: {}) confirmed his email {}".format(user.name, user.id, user.email))
            return simple_message(messages.EMAIL_CONFIRMED)


@app.route("/confirm_email/resend", methods=['POST'])
def resend():
    if not is_user_logged_in():
        log(log.WARNING, "severe: Guest tried to post confirmation email resend request")
        return flask.redirect("/")
    else:
        user_id = flask.session['user_id']
        with db_session_ctx() as dsession:
            user: User = dsession.query(User).filter(User.id == user_id).first()
            if user.is_email_confirmed:
                log(log.WARNING, "User {} (id: {}) with already confirmed email requested token re-generation"
                    .format(user.name, user.id))
                return simple_message(messages.EMAIL_ALREADY_CONFIRMED)
            log(log.INFO, "User {} (id: {}) requested email confirmation token re-generation".format(user.name, user.id))
            user.generate_email_confirmation_token()
            user.send_confirmation_email(mail)
        return simple_message(messages.NEW_EMAIL_CONFIRMATION_TOKEN_SENT)


@app.route("/admin", methods=['GET', 'POST'])
def admin_console():
    if not is_user_logged_in():
        return flask.redirect("/")
    admin_id = flask.session['user_id']
    with db_session_ctx() as db:
        admin: User = db.query(User).filter(User.id == admin_id).first()
        if admin.role != UserRole.admin:
            log(log.WARNING, "User {} (id: {}) illegally tried to access admin console", admin.name, admin.id)
            return flask.redirect("/")
        else:
            if flask.request.method == 'GET':
                return flask.render_template("admin_console.html", users=db.query(User).all())
            if flask.request.method == 'POST':
                log(log.INFO, "Admin {} (id: {}) requested action '{}' for user(s) {}"
                    .format(admin.name, admin.id, flask.request.form['admin_action'], flask.request.form['selected_users']))
                for user_id in json.loads(flask.request.form['selected_users']):
                    user = db.query(User).filter(User.id == user_id).first()
                    if user is None:
                        # TODO proper error display
                        return "error: no user with id {}".format(user_id)
                    if flask.request.form['admin_action'] == "ban":
                        user.is_active = False
                    if flask.request.form['admin_action'] == "unban":
                        user.is_active = True
                    if flask.request.form['admin_action'] == "make_admin":
                        user.role = UserRole.ADMIN.value
                    if flask.request.form['admin_action'] == "make_user":
                        user.role = UserRole.USER.value
                return flask.redirect("/", 302)
                # admin console ban and make admin actions


@app.route('/logout', methods=['POST'])
def logout():
    if 'user_id' in flask.session:
        id = flask.session['user_id']
        log(log.INFO, "User {username} (id: {id}) logged out".format(username=fetch_user_by_id().name, id=id))
        if 'user_id' in flask.session:
            del flask.session['user_id']
        if 'need_back' in flask.session:
            del flask.session['need_back']
    return flask.redirect("/")


@app.route('/skill_test', methods=['GET'])
def skill_test_get():
    if not is_user_logged_in():
        log(log.WARNING, "Guest tried to access skill_test")
        return flask.redirect("/")
    skt = SkillTest()
    log(log.INFO, "User {} (id: {}) started skill test".format(fetch_user_by_id().name, flask.session['user_id']))
    return flask.render_template("skill_test.html", skill_test=skt)


@app.route('/skill_test', methods=['POST'])
def skill_test_post():
    if not is_user_logged_in():
        return flask.redirect("/")
    if fetch_user_by_id().is_test_completed:
        log(log.WARNING, "User (id: {}) tried to submit test results again".format(flask.session['user_id']))
        return simple_message(messages.REPEAT_TEST_SUBMIT)
    exam_form = ExamForm()
    user_answers = exam_form.user_answers.data
    user_answers_json = json.loads(user_answers)
    user_answers_array = []
    for a_dict in user_answers_json:
        # user_answers_array.append(user_answers_json[a_dict])
        user_answers_array += [user_answers_json[a_dict]]

    with db_session_ctx() as db:
        user = db.query(User).filter(User.id == flask.session['user_id']).first()
        user.test_results = json.dumps(SkillTest().as_list_with_answers(user_answers_array))
        user.is_test_completed = True
    log(log.INFO, "User (id: {}) submited test results: {}".format(flask.session['user_id'], user_answers))
    return simple_message(messages.TEST_COMPLETED)

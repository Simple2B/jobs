import json

import flask
import requests
from flask_github import GitHub
from flask_mail import Mail
from oauthlib.oauth2 import WebApplicationClient

import messages
import secret_settings
from config import config
from exam.skilltest import SkillTest
from forms.exam_form import ExamForm
from forms.join_form import JoinForm
from forms.login_form import LoginForm
from logger import log
from models import AuthType, User, UserRole
from session import db_session_ctx

app = flask.Flask(__name__)
app.secret_key = secret_settings.app_secret_key

app.config['GITHUB_CLIENT_ID'] = secret_settings.github_client_id
app.config['GITHUB_CLIENT_SECRET'] = secret_settings.github_client_secret

app.config.update(config['mailer'])

mail = Mail(app)

github = GitHub(app)

GOOGLE_CLIENT_ID = secret_settings.google_client_id
GOOGLE_CLIENT_SECRET = secret_settings.google_client_secret
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

# OAuth 2 client setup for google
client = WebApplicationClient(GOOGLE_CLIENT_ID)


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
    if 'need_back' in flask.session:
        del flask.session['need_back']
    if not is_user_logged_in():
        # FIXME flask.request.remote_addr returns 10.0.0.121, not actual address
        log(log.INFO, "Guest connected from addr %s", flask.request.remote_addr)
        return flask.redirect("/login")
    user = fetch_user_by_id()
    if user is None:
        flask.session['user_id'] = None
        return flask.redirect("/login")
    if not user.is_active:
        return "User is banned"
    if not user.is_email_confirmed:
        return flask.render_template("confirm_email.html", user=user)
    if user.role == UserRole.admin:
        return admin_console()
    if not user.is_test_completed:
        return flask.render_template("test_invitation.html", username=user.name)
    return simple_message(messages.TEST_COMPLETED)


# login/password authentication
@app.route("/login", methods=['GET', 'POST'])
def login():
    if flask.request.method == 'GET':
        return flask.render_template("login.html", form=LoginForm())
    form = LoginForm()
    if form.validate_on_submit():
        with db_session_ctx(read_only=True) as db:
            user: User = db.query(User).filter(User.name == form.name and User.auth_type == AuthType.login_pwd).first()
            if user and user.password == form.passwd:
                flask.session['user_id'] = user.id
                log(log.INFO, "User {username} (id: {id}) logged in".format(username=user.name, id=user.id))
                return flask.redirect("/")
            else:
                flask.session['need_back'] = True
                log(log.ERROR, "Failed login attempt for user {} (id: {}) from addr {}"
                    .format(form.name, user.id if user else None, flask.request.remote_addr))
                return flask.render_template("simple_message.html", message=messages.NO_SUCH_USER)
                # TODO form error, warning
    else:
        log(log.INFO, "Invalid login form submit from addr {}".format(flask.request.remote_addr))
        return "error in form"


@app.route("/join", methods=['GET', 'POST'])
def join():
    if flask.request.method == 'GET':
        return flask.render_template('join.html', form=JoinForm())
    else:
        form = JoinForm()
        if form.validate_on_submit():
            with db_session_ctx() as db:
                user = db.query(User).filter(User.name == form.name).first()
                if user:
                    log(log.INFO, "Attempt to create already existing user {} (id: {}) from addr {}"
                        .format(user.name, user.id, flask.request.remote_addr))
                    # TODO form error
                    return "user {} already exists".format(form.name)

                user = User(form.name, form.e_mail, form.passwd, UserRole.user)
                db.add(user)
                log(log.INFO, "User created: {}".format(user))
            # Send confirmation email
            with db_session_ctx() as db:
                user = db.query(User).filter(User.name == form.name).first()
                user.generate_email_confirmation_token()
                user.send_confirmation_email(mail)
                flask.session['need_back'] = True
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
    with db_session_ctx(read_only=False) as db:
        user = db.query(User).filter(User.email_confirmation_token == token).first()
        if user is None:
            log(log.INFO, "Someone tried to confirm his email with invalid token {}".format(token))
            return simple_message(messages.NO_SUCH_EMAIL_CONFIRMATION_TOKEN)
        else:
            if user.is_email_confirmed:
                return simple_message(messages.EMAIL_ALREADY_CONFIRMED)
            user.is_email_confirmed = True
            log(log.INFO, "User {} (id: {}) confirmed his email {}".format(user.name, user.id, user.email))
            flask.session['need_back'] = True
            return simple_message(messages.EMAIL_CONFIRMED)


@app.route("/confirm_email/resend", methods=['POST'])
def resend():
    if not is_user_logged_in():  # FIXME after user signs in, there is a button to resend, but user is not logged in
        log(log.WARNING, "severe: Guest tried to post confirmation email resend request")
        return flask.redirect("/")
    else:
        user_id = flask.session['user_id']
        with db_session_ctx() as db:
            user: User = db.query(User).filter(User.id == user_id).first()
            if user.is_email_confirmed:
                log(log.WARNING, "User {} (id: {}) with already confirmed email requested token re-generation"
                    .format(user.name, user.id))
                return simple_message(messages.EMAIL_ALREADY_CONFIRMED)
            log(log.INFO, "User {} (id: {}) requested email confirmation token re-generation".format(user.name, user.id))
            user.generate_email_confirmation_token()
            user.send_confirmation_email(mail)
        flask.session['need_back'] = True
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
                        user.role = UserRole.admin
                    if flask.request.form['admin_action'] == "make_user":
                        user.role = UserRole.user
                    if flask.request.form['admin_action'] == "delete_user":
                        db.delete(user)
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
    log(log.INFO, "User (id: {}) submitted test results: {}".format(flask.session['user_id'], user_answers))
    return simple_message(messages.TEST_COMPLETED)


@github.access_token_getter
def token_getter():
    user = flask.g.user
    if user is not None:
        return user.oauth_access_token


@app.route("/github_login", methods=['POST'])
def github_login():
    log(log.INFO, "github login")
    # если пользователь разрешил сайту вход через гитхаб, и после этого база данных была пересоздана,
    # при логине не пересоздаётся пользователь. по идее так и надо, никто в здравом уме не будет удалять базу данных.
    return github.authorize()


# эта функция вызывается только первый раз, когда пользователь позволяет сайту получить  доступ к своему аккаунту.
# переключаться между localhost:5000 и задеплоеным сайтом нужно на https://github.com/settings/developers
@app.route("/github_auth_callback")
@github.authorized_handler
def authorized_github_callback(access_token):
    log(log.INFO, "authorized_github_callback")
    next_url = "/"
    if access_token is None:
        return flask.redirect(next_url)

    flask.g.user = User("github_username_placeholder", "email", None, UserRole.user,
                        AuthType.github, "github_id_placeholder", access_token)
    flask.g.user.is_email_confirmed = True
    github_user = github.get('/user')
    flask.g.user.oauth_id = github_user['id']
    flask.g.user.name = github_user['login']

    with db_session_ctx() as db:
        user = db.query(User).filter(User.oauth_id == github_user['id'] and User.auth_type == AuthType.github).first()
        if user is None:
            db.add(flask.g.user)
        else:
            user.access_token = access_token
            flask.g.user = user

    # второй запрос - чтобы получить сгенерированный базой данных идентификатор
    with db_session_ctx() as db:
        user = db.query(User).filter(User.oauth_id == github_user['id'] and User.auth_type == AuthType.github).first()
        flask.session['user_id'] = user.id
        return flask.redirect(next_url)


# TODO actual email
def oauth_login_or_signup(oauth_type: AuthType, user_id, access_token):
    if oauth_type == AuthType.login_pwd:
        raise ValueError("AuthType.login_pwd is not supported in this function")
    with db_session_ctx() as db:
        user = db.query(User).filter(User.oauth_id == user_id and User.auth_type == oauth_type).first()
        if user is None:
            user = User("{}_username_placeholder".format(oauth_type), "email", None, UserRole.user,
                        oauth_type, user_id, access_token)
            user.is_email_confirmed = True
            db.add(user)
    with db_session_ctx() as db:
        user = db.query(User).filter(User.oauth_id == user_id and User.auth_type == oauth_type).first()
        return user.id


def get_facebook_username_and_email(user_id):
    url = f'https://graph.facebook.com/{user_id}\
?fields=id,name\
&access_token={secret_settings.app_id}|{secret_settings.app_secret_key}'
    # print(url)
    json_resp = requests.get(url).json()
    print(json_resp)


# вызывается каждый раз, когда пользователь входит через login.html
# https://developers.facebook.com/docs/facebook-login/manually-build-a-login-flow?locale=ru_RU#checktoken
@app.route("/facebook_auth", methods=["GET"])
def facebook_auth():
    access_token = flask.request.args.get('access_token')
    log(log.INFO, "Facebook: Attempt to log in with token %s", access_token)
    access_token_validity_check_url = f"https://graph.facebook.com/debug_token?input_token={access_token} \
        &access_token={secret_settings.app_id}|{secret_settings.app_secret_key}"
    json_resp = requests.get(access_token_validity_check_url).json()["data"]
    if(json_resp["is_valid"]):
        # create account or log in
        log(log.INFO, "login success for user %s", json_resp["user_id"])
        log(log.INFO, "user info: %s", json.dumps(json_resp))
        # get_facebook_username_and_email(json_resp["user_id"])  # чтобы добыть имя пользователя. не работает на
        #                                                        # http, поэтому надо тестить на pythonanywhere (TODO).
        user_id = oauth_login_or_signup(AuthType.facebook, json_resp["user_id"], access_token)
        flask.session['user_id'] = user_id
        return flask.redirect("/")
    else:
        # login/signup failed
        log(log.INFO, "login fail for user, provided access token: %s", access_token)
        return simple_message("Provided access token is not valid.")


def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()


# https://realpython.com/flask-google-login/
@app.route("/google_login", methods=["GET"])
def google_login():
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri="/google_auth_callback",
        scope=["openid", "email", "profile"],
    )
    return flask.redirect(request_uri)


@app.route("/google_auth_callback")
def google_auth_callback():
    # Get authorization code Google sent back to you
    code = request.args.get("code")
    # Find out what URL to hit to get tokens that allow you to ask for things on behalf of a user
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]
    
    # TODO OpenID google

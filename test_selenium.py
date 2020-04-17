import pytest
import json
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from time import sleep
from session import db_session_ctx
from models import User, UserRole
from exam.skilltest import SkillTest
from secret_settings import admin_name, admin_password
import messages
# скачать geckodriver, положить в /user/bin
# если ругается на permission, "chmod +x geckodriver"
# если ругается на DISPLAY, "export DISPLAY=:0.0"
# scrapping (selenium)

# ! export DISPLAY=:0.0 !!

# join, guest, login, test, test done, admin login

# TODO after each function clean, separate tests, tearup/down

with open('config.json', 'r') as file:
    conf = json.load(file)["selenium"]
    HOST = conf["HOST"]
    TEST_USERNAME = conf["TEST_USERNAME"]
    TEST_PASSWORD = conf["TEST_PASSWORD"]
    TEST_EMAIL = conf["TEST_EMAIL"]
    SITE_TITLE = conf["SITE_TITLE"]


@pytest.fixture(scope="class")
def driver_init(request):
    options = Options()
    # If you are running Firefox on a system with no display, make sure you use headless mode.
    # https://stackoverflow.com/questions/52534658/webdriverexception-message-invalid-argument-cant-kill-an-exited-process-with
    options.headless = False  # TODO visualisation selenium option
    ff_driver = webdriver.Firefox(options=options)
    ff_driver.implicitly_wait(5)  # ждет 5 секунд, если элемент ещё не загружен
    request.cls.driver = ff_driver
    yield
    ff_driver.close()


@pytest.fixture(scope="function")
def clean():
    create_test_user()
    yield
    delete_test_user()


def create_test_user(email_confirmed=False):
    with db_session_ctx() as db:
        if not db.query(User).filter(User.name == TEST_USERNAME).first():
            user = User(TEST_USERNAME, TEST_EMAIL, TEST_PASSWORD, UserRole.user)
            user.is_email_confirmed = email_confirmed
            db.add(user)


def delete_test_user():
    with db_session_ctx() as db:
        user: User = db.query(User).filter(User.name == TEST_USERNAME).first()
        if user is not None:
            db.delete(user)


def confirm_email():
    with db_session_ctx() as db:
        user: User = db.query(User).filter(User.name == TEST_USERNAME).first()
        user.is_email_confirmed = True


@pytest.mark.usefixtures("driver_init")
@pytest.mark.usefixtures("clean")
class BasicTest:
    pass


class Test_URL(BasicTest):

    def log_in(self, username=TEST_USERNAME, password=TEST_PASSWORD):
        dr = self.driver
        dr.get("http://localhost:5000/login")
        s_uname = dr.find_element_by_name("username")
        s_uname.send_keys(username)
        s_pwd = dr.find_element_by_name("password")
        s_pwd.send_keys(password)
        s_pwd.send_keys(Keys.RETURN)

    def test_home_page(self):
        dr = self.driver
        dr.get(HOST)
        assert SITE_TITLE in self.driver.title

    def test_join(self):
        """заполняем форму регистрации и проверяем, есть ли теперь пользователя в БД"""
        delete_test_user()
        dr = self.driver
        dr.get(HOST + "/join")

        s_email = dr.find_element_by_name("email")
        s_email.send_keys(TEST_EMAIL)
        s_uname = dr.find_element_by_name("username")
        s_uname.send_keys(TEST_USERNAME)
        s_pwd = dr.find_element_by_name("password")
        s_pwd.send_keys(TEST_PASSWORD)
        s_pwd.send_keys(Keys.RETURN)
        # sleep(3)
        WebDriverWait(dr, 5).until(EC.presence_of_element_located((By.ID, 'conf_msg')))
        assert "please confirm your e-mail address" in dr.page_source

        with db_session_ctx() as db:
            user: User = db.query(User).filter(User.name == TEST_USERNAME).first()
            assert user is not None
            assert user.password == TEST_PASSWORD
            assert user.email == TEST_EMAIL
            assert user.is_active
            assert not user.is_email_confirmed
            assert not user.is_test_completed
            assert user.test_results is None

    def test_login(self):
        """заходим под тестовым пользователем и проверяем, что ему нужно подтвердить почту"""
        self.log_in()
        sleep(1)  # После логина может быть много разных страниц, чего ждать - не понятно
        assert "The debugger caught an exception in your WSGI application." not in self.driver.page_source
        assert SITE_TITLE in self.driver.title

    def test_email_confirmation_required(self):
        self.log_in()
        sleep(1)
        assert "please confirm your e-mail address" in self.driver.page_source

    def test_exam(self):
        confirm_email()

        dr = self.driver

        self.log_in()
        WebDriverWait(dr, 5).until(EC.presence_of_element_located((By.ID, "test_start")))
        assert "would you like to pass a basic skill test?" in dr.page_source
        s_test_start = dr.find_element_by_id("test_start")

        s_test_start.click()
        WebDriverWait(dr, 5).until(EC.presence_of_element_located((By.ID, "submit_btn")))
        skt = SkillTest()
        for question in skt.questions:
            radio_0 = dr.find_element_by_id(str(question.id) + '.0')  # 0.0, 1.0, 2.0 ...
            radio_0.click()
        s_submit = dr.find_element_by_id("submit_btn")
        # ActionChains(dr).move_to_element(s_submit).click().perform()
        s_submit.click()
        assert messages.TEST_COMPLETED in dr.page_source

        # FIXME dr.get("localhost:5000/confirm_email?token=123123123)

    def test_admin(self):
        dr = self.driver
        dr.get(HOST + "/login")
        self.log_in(username=admin_name, password=admin_password)
        WebDriverWait(dr, 5).until(EC.presence_of_element_located((By.ID, "admin_action_form")))
        assert admin_name in dr.page_source
        assert "Ban" in dr.page_source
        assert "Set admin role" in dr.page_source

    def test_exam_done(self):
        confirm_email()
        with db_session_ctx() as db:
            user = db.query(User).filter(User.name == TEST_USERNAME).first()
            user.is_test_completed = True

        self.log_in()
        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, "simple_message")))
        assert messages.TEST_COMPLETED in self.driver.page_source

    def test_logout(self):
        self.log_in()
        # StaleElementReferenceException on next line
        # WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, "logout_btn")))
        sleep(1)
        self.driver.find_element_by_id("logout_btn").click()
        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, "login_btn")))

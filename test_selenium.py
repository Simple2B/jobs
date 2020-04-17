import pytest
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from time import sleep
from session import db_session_ctx
from models import User, UserRoleEnum
from exam.skilltest import SkillTest
import messages
# скачать geckodriver, положить в /user/bin
# если ругается на permission, "chmod +x geckodriver"
# если ругается на DISPLAY, "export DISPLAY=:0.0"
# scrapping (selenium)

# ! export DISPLAY=:0.0 !!

# TODO join, guest, login, test, test done, admin login

# TODO after each function clean, separate tests, tearup/down
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


@pytest.mark.usefixtures("driver_init")
class BasicTest:
    pass


class Test_URL(BasicTest):
    TEST_USERNAME = "ton_test_sign_in"
    TEST_PASSWORD = "test"
    TEST_EMAIL = "info.simple2b@gmail.com"

    def create_test_user(self):
        with db_session_ctx() as db:
            if not db.query(User).filter(User.name == self.TEST_USERNAME).first():
                user = User(self.TEST_USERNAME, self.TEST_EMAIL, self.TEST_PASSWORD, UserRoleEnum.USER)
                db.add(user)

    def delete_test_user(self):
        with db_session_ctx() as db:
            user: User = db.query(User).filter(User.name == self.TEST_USERNAME).first()
            if user is not None:
                db.delete(user)

    def confirm_email(self):
        with db_session_ctx() as db:
            user: User = db.query(User).filter(User.name == self.TEST_USERNAME).first()
            user.is_email_confirmed = True

    def log_in(self):
        dr = self.driver
        dr.get("http://localhost:5000/login")
        s_uname = dr.find_element_by_name("username")
        s_uname.send_keys(self.TEST_USERNAME)
        s_pwd = dr.find_element_by_name("password")
        s_pwd.send_keys(self.TEST_PASSWORD)
        s_pwd.send_keys(Keys.RETURN)

    def test_home_page(self):
        dr = self.driver
        dr.get("http://localhost:5000")
        assert "Simple2b" in self.driver.title

    def test_join(self):
        """заполняем форму регистрации и проверяем, есть ли теперь пользователя в БД"""
        self.delete_test_user()
        dr = self.driver
        dr.get("http://localhost:5000/join")
        s_email = dr.find_element_by_name("email")
        s_email.send_keys(self.TEST_EMAIL)
        s_uname = dr.find_element_by_name("username")
        s_uname.send_keys(self.TEST_USERNAME)
        s_pwd = dr.find_element_by_name("password")
        s_pwd.send_keys(self.TEST_PASSWORD)
        s_pwd.send_keys(Keys.RETURN)
        # sleep(3)
        WebDriverWait(dr, 5).until(EC.presence_of_element_located((By.ID, 'conf_msg')))
        assert "please confirm your e-mail address" in dr.page_source

        with db_session_ctx() as db:
            user: User = db.query(User).filter(User.name == self.TEST_USERNAME).first()
            assert user is not None

    def test_login(self):
        """заходим под тестовым пользователем и проверяем, что ему нужно подтвердить почту"""
        self.create_test_user()
        self.log_in()
        sleep(1)
        assert "The debugger caught an exception in your WSGI application." not in self.driver.page_source
        assert "Simple2b" in self.driver.title

    def test_email_confirmation_required(self):
        self.delete_test_user()
        self.create_test_user()
        self.log_in()
        sleep(1)
        assert "please confirm your e-mail address" in self.driver.page_source
        s_logout = self.driver.find_element_by_id("logout_btn")
        ActionChains(self.driver).move_to_element(s_logout).click().perform()

    def test_exam(self):
        # искусственно подтверждаем почту через БД
        dr = self.driver
        with db_session_ctx() as db:
            user: User = db.query(User).filter(User.name == self.TEST_USERNAME).first()
            user.is_email_confirmed = True

        self.log_in()
        WebDriverWait(dr, 5).until(EC.presence_of_element_located((By.ID, "test_start")))
        assert "would you like to pass a basic skill test?" in dr.page_source
        s_test_start = dr.find_element_by_id("test_start")

        ActionChains(dr).move_to_element(s_test_start).click().perform()
        WebDriverWait(dr, 5).until(EC.presence_of_element_located((By.ID, "submit_btn")))
        skt = SkillTest()
        for question in skt.questions:
            radio_0 = dr.find_element_by_id(str(question.id) + '.0')  # 0.0, 1.0, 2.0 ...
            ActionChains(dr).move_to_element(radio_0).click().perform()
        s_submit = dr.find_element_by_id("submit_btn")
        ActionChains(dr).move_to_element(s_submit).click().perform()
        sleep(1)
        assert messages.TEST_COMPLETED in dr.page_source

        # FIXME dr.get("localhost:5000/confirm_email?token=123123123)

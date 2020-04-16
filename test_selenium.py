import pytest
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from time import sleep
from session import db_session_ctx
from models import User
from exam.skilltest import SkillTest
import messages
# скачать geckodriver, положить в /user/bin
# если ругается на permission, "chmod +x geckodriver"
# если ругается на DISPLAY, "export DISPLAY=:0.0"
# scrapping (selenium)

# ! export DISPLAY=:0.0 !!

# TODO after each function clean, separate tests, tearup/down
@pytest.fixture(scope="class")
def driver_init(request):
    options = Options()
    # If you are running Firefox on a system with no display, make sure you use headless mode.
    # https://stackoverflow.com/questions/52534658/webdriverexception-message-invalid-argument-cant-kill-an-exited-process-with
    options.headless = False  # TODO visualisation selenium option
    ff_driver = webdriver.Firefox(options=options)
    request.cls.driver = ff_driver
    yield
    ff_driver.close()


@pytest.mark.usefixtures("driver_init")
class BasicTest:
    pass


class Test_URL(BasicTest):
    # TODO caps
    test_username = "ton_test_sign_in"
    test_password = "test"
    test_email = "info.simple2b@gmail.com"

    @pytest.mark.skip(reason="test for selenium itself")
    def test_open_url(self):
        dr: webdriver.WebDriver = self.driver
        dr.get("http://localhost:5000")
        sleep(1)
        elem = dr.find_element_by_name("username")
        elem.send_keys("ton_user")
        sleep(1)
        elem.send_keys(Keys.RETURN)
        sleep(1)
        assert "error in form" in self.driver.page_source
        sleep(1)

    @pytest.mark.skip(reason="test for selenium itself")
    def test_python_website(self):
        self.driver.get("http://www.python.org")
        assert "Python" in self.driver.title
        elem = self.driver.find_element_by_name("q")
        elem.send_keys("pycon")
        elem.send_keys(Keys.RETURN)
        assert "No results found." not in self.driver.page_source

    def test_join(self):
        # удалить тестового пользователя, если он уже существует
        with db_session_ctx() as db:
            user: User = db.query(User).filter(User.name == self.test_username).first()
            if user is not None:
                db.delete(user)

        # заполняем форму регистрации и проверяем, есть ли теперь пользователя в БД
        dr = self.driver
        dr.get("http://localhost:5000/join")

        s_email = dr.find_element_by_name("email")
        s_email.send_keys(self.test_email)
        s_uname = dr.find_element_by_name("username")
        s_uname.send_keys(self.test_username)
        s_pwd = dr.find_element_by_name("password")
        s_pwd.send_keys(self.test_password)
        sleep(1)
        s_pwd.send_keys(Keys.RETURN)
        sleep(2)
        assert "please confirm your e-mail address" in self.driver.page_source

        with db_session_ctx() as db:
            user: User = db.query(User).filter(User.name == self.test_username).first()
            assert user is not None
            print(user.email_confirmation_token)
            # user.is_email_confirmed = True

        # заходим под тестовым пользователем и проверяем, что ему нужно подтвердить почту
        dr.get("http://localhost:5000/login")
        s_uname = dr.find_element_by_name("username")
        s_uname.send_keys(self.test_username)
        s_pwd = dr.find_element_by_name("password")
        s_pwd.send_keys(self.test_password)
        sleep(1)
        s_pwd.send_keys(Keys.RETURN)
        sleep(2)
        assert "please confirm your e-mail address" in dr.page_source
        # TODO logout, in db set is_email_confirmed = True, then test exam
        s_logout = dr.find_element_by_id("logout_btn")
        ActionChains(dr).move_to_element(s_logout).click().perform()
        sleep(1)

        # искусственно подтверждаем почту через БД
        with db_session_ctx() as db:
            user: User = db.query(User).filter(User.name == self.test_username).first()
            user.is_email_confirmed = True

        sleep(1)

        dr.get("http://localhost:5000/login")
        s_uname = dr.find_element_by_name("username")
        s_uname.send_keys(self.test_username)
        s_pwd = dr.find_element_by_name("password")
        s_pwd.send_keys(self.test_password)
        sleep(1)
        s_pwd.send_keys(Keys.RETURN)
        sleep(2)

        assert "would you like to pass a basic skill test?" in dr.page_source

        s_test_start = dr.find_element_by_id("test_start")
        ActionChains(dr).move_to_element(s_test_start).click().perform()
        sleep(2)
        skt = SkillTest()
        for question in skt.questions:
            radio_0 = dr.find_element_by_id(str(question.id) + '.0')  # 0.0, 1.0, 2.0 ...
            ActionChains(dr).move_to_element(radio_0).click().perform()
            sleep(0.3)
        sleep(2)
        s_submit = dr.find_element_by_id("submit_btn")
        ActionChains(dr).move_to_element(s_submit).click().perform()
        sleep(3)
        assert messages.TEST_COMPLETED in dr.page_source

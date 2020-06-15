# import pytest
# from time import sleep
from secrets import token_hex

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import messages
from config import config
from secret_settings import admin_name, admin_password
from test_selenium import BasicTest, driver_init  # noqa


class TestExternal(BasicTest):
    s_conf = config["selenium"]
    HOST = "http://localhost:5000"  # "https://flav1us.pythonanywhere.com"  # TODO export to config
    TEST_CREATED_USERNAME = s_conf["TEST_USERNAME"]
    TEST_NEW_USERNAME = s_conf["TEST_USERNAME"] + token_hex(8)  # during join test new user will be created each time
    TEST_PASSWORD = s_conf["TEST_PASSWORD"]
    TEST_EMAIL = s_conf["TEST_EMAIL"]
    SITE_TITLE = s_conf["SITE_TITLE"]

    def log_in(self, username=TEST_CREATED_USERNAME, password=TEST_PASSWORD):
        dr = self.driver
        dr.get(self.HOST + "/login")
        s_uname = dr.find_element_by_name("username")
        s_uname.send_keys(username)
        s_pwd = dr.find_element_by_name("password")
        s_pwd.send_keys(password)
        s_pwd.send_keys(Keys.RETURN)

    def test_home_page(self):
        self.driver.get(self.HOST)
        assert self.s_conf["SITE_TITLE"] in self.driver.title

    def test_oauth2_button_presence(self):
        self.driver.get(self.HOST)
        assert '<form action="/github_login"' in self.driver.page_source
        assert '<fb:login-button' in self.driver.page_source

    def test_login(s):
        s.log_in(username=s.TEST_CREATED_USERNAME, password=s.TEST_PASSWORD)
        # assert "The debugger caught an exception in your WSGI application." not in self.driver.page_source
        assert "exception" not in s.driver.page_source
        assert s.SITE_TITLE in s.driver.title
        assert messages.NO_SUCH_USER in s.driver.page_source  # user deleted

    def test_admin(self):
        dr = self.driver
        dr.get(self.HOST + "/login")
        self.log_in(username=admin_name, password=admin_password)
        WebDriverWait(dr, 5).until(EC.presence_of_element_located((By.ID, "admin_action_form")))
        assert admin_name in dr.page_source
        assert "Ban" in dr.page_source
        assert "Set admin role" in dr.page_source
        dr.find_element_by_id("logout_btn").click()

    # @pytest.mark.skip(reason="creates new user each time")
    def test_join(self):
        dr = self.driver
        dr.get(self.HOST + "/join")

        s_email = dr.find_element_by_name("email")
        s_email.send_keys(self.TEST_EMAIL)
        s_uname = dr.find_element_by_name("username")
        s_uname.send_keys(self.TEST_NEW_USERNAME)
        s_pwd = dr.find_element_by_name("password")
        s_pwd.send_keys(self.TEST_PASSWORD)
        s_pwd.send_keys(Keys.RETURN)
        # sleep(3)
        WebDriverWait(dr, 5).until(EC.presence_of_element_located((By.ID, 'conf_msg')))
        assert "please confirm your e-mail address" in dr.page_source  # FIXME not working if several pages

        s_logout = dr.find_element_by_id("back_btn")
        s_logout.click()
        self.log_in(admin_name, admin_password)
        assert self.TEST_NEW_USERNAME in dr.page_source

        # перебираем строки таблицы
        for tr in dr.find_elements(By.XPATH, "//*[@id=\"admin_console_users\"]/tbody/tr"):
            # в кажом стобце строки ищем имя пользователя
            for subelem in tr.find_elements_by_tag_name("td"):
                # если такое имя пользователя есть в строке, нажимаем чекбокс из этой строки
                if self.TEST_NEW_USERNAME in subelem.text:
                    checkbox = tr.find_element(By.TAG_NAME, "input")
                    checkbox.click()
                    break
        dr.find_element_by_id("delete_user_btn").click()
        assert self.TEST_NEW_USERNAME not in dr.page_source

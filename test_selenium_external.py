import pytest
from test_selenium import BasicTest, driver_init
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from time import sleep
from secrets import token_hex
from config import config
from secret_settings import admin_name, admin_password


class TestExternal(BasicTest):
    s_conf = config["selenium"]
    HOST = "https://flav1us.pythonanywhere.com"  # TODO export to config
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

    def test_login(s):
        s.log_in()
        # assert "The debugger caught an exception in your WSGI application." not in self.driver.page_source
        assert "exception" not in s.driver.page_source
        assert s.SITE_TITLE in s.driver.title

    def test_admin(self):
        dr = self.driver
        dr.get(self.HOST + "/login")
        self.log_in(username=admin_name, password=admin_password)
        WebDriverWait(dr, 5).until(EC.presence_of_element_located((By.ID, "admin_action_form")))
        assert admin_name in dr.page_source
        assert "Ban" in dr.page_source
        assert "Set admin role" in dr.page_source

    @pytest.mark.skip(reason="creates new user each time")
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
        assert "please confirm your e-mail address" in dr.page_source
        sleep(2)

        s_logout = dr.find_element_by_id("logout_btn")
        s_logout.click()
        self.log_in(admin_name, admin_password)
        assert self.TEST_USERNAME in dr.page_source
        sleep(2)

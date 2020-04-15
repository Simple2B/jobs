from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from time import sleep
import pytest
# скачать geckodriver, положить в /user/bin
# если ругается на permission, "chmod +x geckodriver"
# если ругается на DISPLAY, "export DISPLAY=:0.0"

# ! export DISPLAY=:0.0 !!


@pytest.fixture(scope="class")
def driver_init(request):
    options = Options()
    # If you are running Firefox on a system with no display, make sure you use headless mode.
    # https://stackoverflow.com/questions/52534658/webdriverexception-message-invalid-argument-cant-kill-an-exited-process-with
    options.headless = False
    ff_driver = webdriver.Firefox(options=options)
    request.cls.driver = ff_driver
    yield
    ff_driver.close()


@pytest.mark.usefixtures("driver_init")
class BasicTest:
    pass


class Test_URL(BasicTest):
    def test_open_url(self):
        dr = self.driver
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

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import pytest
from time import sleep
# скачать geckodriver, положить в /user/bin
# если ругается на permission, "chmod +x geckodriver"
# если ругается на DISPLAY, "export DISPLAY=:0.0"


@pytest.fixture(scope="class")
def driver_init(request):
    options = Options()
    # If you are running Firefox on a system with no display, make sure you use headless mode.
    # https://stackoverflow.com/questions/52534658/webdriverexception-message-invalid-argument-cant-kill-an-exited-process-with
    options.headless = True
    ff_driver = webdriver.Firefox(options=options)
    request.cls.driver = ff_driver
    yield
    ff_driver.close()


@pytest.mark.usefixtures("driver_init")
class BasicTest:
    pass


class Test_URL(BasicTest):
    def test_open_url(self):
        self.driver.get("http://localhost:5000")
        print(self.driver.title)

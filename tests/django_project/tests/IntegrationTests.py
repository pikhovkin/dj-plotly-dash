import os
import time
import warnings

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup

from django.test import LiveServerTestCase

from .utils import invincible, wait_for


TIMEOUT = 20


class SeleniumDriverTimeout(Exception):
    pass


class IntegrationTests(LiveServerTestCase):
    last_timestamp = 0
    _last_ts = 0

    def wait_for_element_by_id(self, id, timeout=TIMEOUT):
        wait_for(lambda: None is not invincible(
            lambda: self.driver.find_element_by_id(id)
        ), timeout=timeout)
        return self.driver.find_element_by_id(id)

    def wait_for_element_by_css_selector(self, selector, timeout=TIMEOUT):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector)),
            'Could not find element with selector "{}"'.format(selector)
        )

    def wait_for_text_to_equal(self, selector, assertion_text, timeout=TIMEOUT):
        el = self.wait_for_element_by_css_selector(selector)
        WebDriverWait(self.driver, timeout).until(
            lambda *args: (
                    (str(el.text) == assertion_text) or
                    (str(el.get_attribute('value')) == assertion_text)
            ),
            "Element '{}' text was supposed to equal '{}' but it didn't".format(
                selector,
                assertion_text
            )
        )

    @classmethod
    def setUpClass(cls):
        super(IntegrationTests, cls).setUpClass()

        options = Options()
        options.add_argument('--no-sandbox')

        capabilities = DesiredCapabilities.CHROME
        capabilities['loggingPrefs'] = {'browser': 'SEVERE'}

        if 'DASH_TEST_CHROMEPATH' in os.environ:
            options.binary_location = os.environ['DASH_TEST_CHROMEPATH']

        cls.driver = webdriver.Chrome(
            chrome_options=options, desired_capabilities=capabilities,
            service_args=["--verbose", "--log-path=chrome.log"]
            )

    @classmethod
    def tearDownClass(cls):
        super(IntegrationTests, cls).tearDownClass()

        cls.driver.quit()

    def tearDown(self):
        self.clear_log()
        time.sleep(1)

    def open(self, dash):
        # Visit the dash page
        self.driver.implicitly_wait(2)
        self.driver.get('{}/{}'.format(self.live_server_url, dash))
        time.sleep(1)

    def clear_log(self):
        entries = self.driver.get_log("browser")
        if entries:
            self.last_timestamp = entries[-1]["timestamp"]

    def get_log(self):
        entries = self.driver.get_log("browser")
        return [
            entry
            for entry in entries
            if entry["timestamp"] > self.last_timestamp
        ]

    def get_logs(self):
        """return a list of `SEVERE` level logs after last reset time stamps
        (default to 0, resettable by `reset_log_timestamp`. Chrome only
        """
        if self.driver.name.lower() == "chrome":
            return [
                entry
                for entry in self.driver.get_log("browser")
                if entry["timestamp"] > self._last_ts
            ]
        warnings.warn(
            "get_logs always return None with webdrivers other than Chrome"
        )
        return None

    def wait_until_get_log(self, timeout=10):
        logs = None
        cnt, poll = 0, 0.1
        while not logs:
            logs = self.get_log()
            time.sleep(poll)
            cnt += 1
            if cnt * poll >= timeout * 1000:
                raise SeleniumDriverTimeout(
                    'cannot get log in {}'.format(timeout))

        return logs

    def is_console_clean(self):
        return not self.get_log()

    def find_element(self, selector):
        """find_element returns the first found element by the css `selector`
        shortcut to `driver.find_element_by_css_selector`
        """
        return self.driver.find_element_by_css_selector(selector)

    def multiple_click(self, selector, clicks):
        """multiple_click click the element with number of `clicks`
        """
        for _ in range(clicks):
            self.find_element(selector).click()

    def clear_input(self, elem):
        """simulate key press to clear the input"""
        (
            ActionChains(self.driver)
                .click(elem)
                .send_keys(Keys.HOME)
                .key_down(Keys.SHIFT)
                .send_keys(Keys.END)
                .key_up(Keys.SHIFT)
                .send_keys(Keys.DELETE)
        ).perform()

    @property
    def redux_state_rqs(self):
        return self.driver.execute_script(
            "return window.store.getState().requestQueue"
        )

    @property
    def redux_state_paths(self):
        return self.driver.execute_script(
            "return window.store.getState().paths"
        )

    @property
    def dash_entry_locator(self):
        return "#react-entry-point"

    def _get_dash_dom_by_attribute(self, attr):
        return BeautifulSoup(
            self.find_element(self.dash_entry_locator).get_attribute(attr),
            "html",
        )

    @property
    def dash_innerhtml_dom(self):
        return self._get_dash_dom_by_attribute("innerHTML")

    def find_elements(self, selector):
        """find_elements returns a list of all elements matching the css
        `selector`. shortcut to `driver.find_elements_by_css_selector`
        """
        return self.driver.find_elements_by_css_selector(selector)

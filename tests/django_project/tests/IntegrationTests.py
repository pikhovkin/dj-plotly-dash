import time

from django.test import LiveServerTestCase

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .utils import invincible, wait_for


TIMEOUT = 20


class IntegrationTests(LiveServerTestCase):
    def wait_for_element_by_id(self, id):
        wait_for(lambda: None is not invincible(
            lambda: self.driver.find_element_by_id(id)
        ), timeout=TIMEOUT)
        return self.driver.find_element_by_id(id)

    def wait_for_element_by_css_selector(self, selector):
        return WebDriverWait(self.driver, TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )

    def wait_for_text_to_equal(self, selector, assertion_text):
        return WebDriverWait(self.driver, TIMEOUT).until(
            EC.text_to_be_present_in_element((By.CSS_SELECTOR, selector),
                                             assertion_text)
        )

    @classmethod
    def setUpClass(cls):
        super(IntegrationTests, cls).setUpClass()

        cls.driver = webdriver.Chrome()

    @classmethod
    def tearDownClass(cls):
        super(IntegrationTests, cls).tearDownClass()

        cls.driver.quit()

    def tearDown(self):
        time.sleep(2)

    def open(self, dash):
        # Visit the dash page
        self.driver.get('{}/{}'.format(self.live_server_url, dash))
        time.sleep(1)

        # Inject an error and warning logger
        logger = '''
        window.tests = {};
        window.tests.console = {error: [], warn: [], log: []};

        var _log = console.log;
        var _warn = console.warn;
        var _error = console.error;

        console.log = function() {
            window.tests.console.log.push({method: 'log', arguments: arguments});
            return _log.apply(console, arguments);
        };

        console.warn = function() {
            window.tests.console.warn.push({method: 'warn', arguments: arguments});
            return _warn.apply(console, arguments);
        };

        console.error = function() {
            window.tests.console.error.push({method: 'error', arguments: arguments});
            return _error.apply(console, arguments);
        };
        '''
        self.driver.execute_script(logger)

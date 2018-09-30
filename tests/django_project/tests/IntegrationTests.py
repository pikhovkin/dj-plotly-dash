import sys
import time

from selenium import webdriver
from django.test import LiveServerTestCase

from .utils import invincible, wait_for


class IntegrationTests(LiveServerTestCase):
    def wait_for_element_by_id(self, id):
        wait_for(lambda: None is not invincible(
            lambda: self.driver.find_element_by_id(id)
        ), timeout=5)
        return self.driver.find_element_by_id(id)

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

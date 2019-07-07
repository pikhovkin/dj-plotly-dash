import itertools
import re
import json
import time

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from dash import exceptions
from dash.dependencies import Input, Output, State

from .IntegrationTests import IntegrationTests
from .utils import assert_clean_console, wait_for

from ..dynamic_dash import views as dynamic_views
from ..static_dash import views as static_views


class Tests(IntegrationTests):
    def _simple_callback(self, view_class):
        self.open('dash/{}/'.format(view_class.dash_name))

        # output1 = self.wait_for_element_by_id('output-1')
        # wait_for(lambda: output1.text == 'initial value', timeout=20)

        self.wait_for_text_to_equal('#output-1', 'initial value')

        input1 = self.wait_for_element_by_id('input')
        chain = (
            ActionChains(self.driver)
                .click(input1)
                .send_keys(Keys.HOME)
                .key_down(Keys.SHIFT)
                .send_keys(Keys.END)
                .key_up(Keys.SHIFT)
                .send_keys(Keys.DELETE))
        chain.perform()

        input1.send_keys('hello world')

        self.wait_for_text_to_equal('#output-1', 'hello world')

        self.assertEqual(
            view_class.call_count.value,
            # an initial call to retrieve the first value
            # and one for clearing the input
            2 +
            # one for each hello world character
            len('hello world')
        )

        # assert_clean_console(self)
        self.assertTrue(self.is_console_clean())

    def _wildcard_callback(self, view_class):
        self.open('dash/{}/'.format(view_class.dash_name))

        self.wait_for_text_to_equal('#output-1', 'initial value')

        input1 = self.wait_for_element_by_css_selector('#input')
        chain = (ActionChains(self.driver)
                 .click(input1)
                 .send_keys(Keys.HOME)
                 .key_down(Keys.SHIFT)
                 .send_keys(Keys.END)
                 .key_up(Keys.SHIFT)
                 .send_keys(Keys.DELETE))
        chain.perform()

        input1.send_keys('hello world')

        self.wait_for_text_to_equal('#output-1', 'hello world')

        self.assertEqual(
            view_class.call_count.value,
            # an initial call
            # and a call for clearing the input
            2 +
            # one for each hello world character
            len('hello world')
        )

        self.assertTrue(self.is_console_clean())

    def _aborted_callback(self, view_class):
        """
        Raising PreventUpdate OR returning no_update
        prevents update and triggering dependencies
        """
        self.open('dash/{}/'.format(view_class.dash_name))

        input_ = self.wait_for_element_by_id('input')
        input_.send_keys('xyz')
        self.wait_for_text_to_equal('#input', 'initial inputxyz')
        output1 = self.wait_for_element_by_id('output1')
        output2 = self.wait_for_element_by_id('output2')

        # callback1 runs 4x (initial page load and 3x through send_keys)
        wait_for(lambda: view_class.callback1_count.value == 4)

        # callback2 is never triggered, even on initial load
        self.assertEqual(view_class.callback2_count.value, 0)

        # double check that output1 and output2 children were not updated
        self.assertEqual(output1.text, view_class.initial_output)
        self.assertEqual(output2.text, view_class.initial_output)

        self.assertTrue(self.is_console_clean())

    def _wildcard_data_attributes(self, view_class):
        self.open('dash/{}/'.format(view_class.dash_name))

        div = self.wait_for_element_by_id('data-element')

        # React wraps text and numbers with e.g. <!-- react-text: 20 -->
        # Remove those
        comment_regex = r'<!--[^\[](.*?)-->'  # noqa: W605

        # Somehow the html attributes are unordered.
        # Try different combinations (they're all valid html)
        permutations = itertools.permutations([
            'id="inner-element"',
            'data-string="multiple words"',
            'data-number="512"',
            'data-date="%s"' % (view_class.test_date),
            'aria-progress="5"'
        ], 5)
        passed = False
        for permutation in permutations:
            actual_cleaned = re.sub(comment_regex, '',
                                    div.get_attribute('innerHTML'))
            expected_cleaned = re.sub(
                comment_regex,
                '',
                "<div PERMUTE></div>"
                .replace('PERMUTE', ' '.join(list(permutation)))
            )
            passed = passed or (actual_cleaned == expected_cleaned)
            if passed:
                break

        if not passed:
            raise Exception(
                'HTML does not match\nActual:\n{}\n\nExpected:\n{}'.format(
                    actual_cleaned,
                    expected_cleaned
                )
            )

        self.assertTrue(self.is_console_clean())

    def _flow_component(self, view_class):
        self.open('dash/{}/'.format(view_class.dash_name))

        self.wait_for_element_by_id('waitfor')

    def _no_props_component(self, view_class):
        self.open('dash/{}/'.format(view_class.dash_name))

        self.assertTrue(self.is_console_clean())

    def _meta_tags(self, view_class):
        self.open('dash/{}/'.format(view_class.dash_name))

        metas = view_class.metas
        meta = self.driver.find_elements_by_tag_name('meta')

        # -2 for the meta charset and http-equiv.
        self.assertEqual(len(metas), len(meta) - 2, 'Not enough meta tags')

        for i in range(2, len(meta)):
            meta_tag = meta[i]
            meta_info = metas[i - 2]
            name = meta_tag.get_attribute('name')
            content = meta_tag.get_attribute('content')
            self.assertEqual(name, meta_info['name'])
            self.assertEqual(content, meta_info['content'])

    def _index_customization(self, view_class):
        self.open('dash/{}/'.format(view_class.dash_name))

        header = self.wait_for_element_by_id('custom-header')
        footer = self.wait_for_element_by_id('custom-footer')

        self.assertEqual('My custom header', header.text)
        self.assertEqual('My custom footer', footer.text)

        add = self.wait_for_element_by_id('add')

        self.assertEqual('Got added', add.text)

    def _assets(self, view_class):
        self.open('dash/{}/'.format(view_class.dash_name))

        body = self.driver.find_element_by_tag_name('body')

        body_margin = body.value_of_css_property('margin')
        self.assertEqual('0px', body_margin)

        content = self.wait_for_element_by_id('content')
        content_padding = content.value_of_css_property('padding')
        self.assertEqual('8px', content_padding)

        tested = self.wait_for_element_by_id('tested')
        tested = json.loads(tested.text)

        order = ('load_first', 'load_after', 'load_after1',
                 'load_after10', 'load_after11', 'load_after2',
                 'load_after3', 'load_after4', )

        self.assertEqual(len(order), len(tested))

        for i in range(len(tested)):
            self.assertEqual(order[i], tested[i])

    def _external_files_init(self, view_class):
        self.open('dash/{}/'.format(view_class.dash_name))

        js_urls = [x['src'] if isinstance(x, dict) else x for x in view_class.js_files]
        css_urls = [x['href'] if isinstance(x, dict) else x for x in view_class.css_files]

        for fmt, url in itertools.chain((("//script[@src='{}']", x) for x in js_urls),
                                        (("//link[@href='{}']", x) for x in css_urls)):
            self.driver.find_element_by_xpath(fmt.format(url))

        # Ensure the button style was overloaded by reset (set to 38px in codepen)
        btn = self.driver.find_element_by_id('btn')
        btn_height = btn.value_of_css_property('height')

        self.assertEqual('38px', btn_height)

        # ensure ramda was loaded before the assets so they can use it.
        lo_test = self.driver.find_element_by_id('ramda-test')
        self.assertEqual('Hello World', lo_test.text)

    def _func_layout_accepted(self, view_class):
        self.open('dash/{}/'.format(view_class.dash_name))

    def _late_component_register(self, view_class):
        self.open('dash/{}/'.format(view_class.dash_name))

        btn = self.wait_for_element_by_css_selector('#btn-insert')
        btn.click()
        time.sleep(1)

        self.wait_for_element_by_css_selector('#inserted-input')

    def _multi_output(self, view_class):
        view = view_class if getattr(view_class, 'dash', None) else view_class()

        with self.assertRaises(exceptions.DuplicateCallbackOutput) as err:
            view.dash.callback(Output('output1', 'children'),
                               [Input('output-btn', 'n_clicks')])(view.on_click_duplicate)

        self.assertIn('output1', err.exception.args[0])

        with self.assertRaises(
                exceptions.DuplicateCallbackOutput,
                msg='multi output cannot contain a used single output'
        ) as err:
            view.dash.callback(Output('output1', 'children'),
                               [Input('output-btn', 'n_clicks')])(view.on_click_duplicate)

        self.assertIn('output1', err.exception.args[0])

        with self.assertRaises(
                exceptions.DuplicateCallbackOutput,
                msg='multi output cannot contain a used single output'
        ) as err:
            view.dash.callback([Output('output3', 'children'), Output('output4', 'children')],
                               [Input('output-btn', 'n_clicks')])(view.on_click_duplicate_multi)

        self.assertIn('output3', err.exception.args[0])

        with self.assertRaises(
                exceptions.DuplicateCallbackOutput,
                msg='same output cannot be used twice in one callback'
        ) as err:
            view.dash.callback([Output('output5', 'children'), Output('output5', 'children')],
                               [Input('output-btn', 'n_clicks')])(view.on_click_same_output)

        self.assertIn('output5', err.exception.args[0])

        with self.assertRaises(
                exceptions.DuplicateCallbackOutput,
                msg='no part of an existing multi-output can be used in another'
        ) as err:
            view.dash.callback([Output('output1', 'children'), Output('output5', 'children')],
                               [Input('output-btn', 'n_clicks')])(view.overlapping_multi_output)

        self.assertTrue('{\'output1.children\'}' in err.exception.args[0]
                        or "set(['output1.children'])" in err.exception.args[0])

        self.open('dash/{}/'.format(view_class.dash_name))

        t = time.time()

        btn = self.driver.find_element_by_id('output-btn')
        btn.click()
        time.sleep(1)

        self.wait_for_text_to_equal('#output1', '1')

        self.assertTrue(int(self.driver.find_element_by_id('output2').text) > t)

    def _multi_output_no_update(self, view_class):
        self.open('dash/{}/'.format(view_class.dash_name))

        self.multiple_click('#btn', 10)

        self.wait_for_text_to_equal('#n1', '4')
        self.wait_for_text_to_equal('#n2', '2')
        self.wait_for_text_to_equal('#n3', 'initial3')

    def _no_update_chains(self, view_class):
        self.open('dash/{}/'.format(view_class.dash_name))

        a_in = self.find_element('#a_in')
        b_in = self.find_element('#b_in')

        b_in.send_keys('b')
        a_in.send_keys('a')
        self.wait_for_text_to_equal('#a_out', 'aa')
        self.wait_for_text_to_equal('#b_out', 'bb')
        self.wait_for_text_to_equal('#a_out_short', 'aa')
        self.wait_for_text_to_equal('#ab_out', 'aa bb')

        b_in.send_keys('b')
        a_in.send_keys('a')
        self.wait_for_text_to_equal('#a_out', 'aaa')
        self.wait_for_text_to_equal('#b_out', 'bbb')
        self.wait_for_text_to_equal('#a_out_short', 'aa')
        # ab_out has not been triggered because a_out_short received no_update
        self.wait_for_text_to_equal('#ab_out', 'aa bb')

        b_in.send_keys('b')
        a_in.send_keys(Keys.END)
        a_in.send_keys(Keys.BACKSPACE)
        self.wait_for_text_to_equal('#a_out', 'aa')
        self.wait_for_text_to_equal('#b_out', 'bbbb')
        self.wait_for_text_to_equal('#a_out_short', 'aa')
        # now ab_out *is* triggered - a_out_short got a new value
        # even though that value is the same as the last value it got
        self.wait_for_text_to_equal('#ab_out', 'aa bbbb')

    def _with_custom_renderer(self, view_class):
        self.open('dash/{}/'.format(view_class.dash_name))

        input1 = self.find_element('#input')
        self.clear_input(input1)

        input1.send_keys('fire request hooks')

        self.wait_for_text_to_equal('#output-1', 'fire request hooks')
        self.assertTrue(self.find_element('#output-pre').text == 'request_pre!!!')
        self.assertTrue(self.find_element('#output-post').text == 'request_post ran!')

    def _modified_response(self, view_class):
        self.open('dash/{}/'.format(view_class.dash_name))

        self.wait_for_text_to_equal('#output', 'ab - output')
        input1 = self.driver.find_element_by_id('input')

        input1.send_keys('cd')

        self.wait_for_text_to_equal('#output', 'abcd - output')
        cookie = self.driver.get_cookie('dash_cookie')
        # cookie gets json encoded
        self.assertEqual(cookie['value'], '"abcd - cookie"')

        self.assertTrue(self.is_console_clean())

    def _test_simple_callback(self):
        self._simple_callback(dynamic_views.DashSimpleCallback)
        self._simple_callback(static_views.DashSimpleCallback)

    def _test_wildcard_callback(self):
        self._wildcard_callback(dynamic_views.DashWildcardCallback)
        self._wildcard_callback(static_views.DashWildcardCallback)

    def _test_aborted_callback(self):
        self._aborted_callback(dynamic_views.DashAbortedCallback)
        self._aborted_callback(static_views.DashAbortedCallback)

    def _test_wildcard_data_attributes(self):
        self._wildcard_data_attributes(dynamic_views.DashWildcardDataAttributes)
        self._wildcard_data_attributes(static_views.DashWildcardDataAttributes)

    def _test_flow_component(self):
        self._flow_component(dynamic_views.DashFlowComponent)
        self._flow_component(static_views.DashFlowComponent)

    def _test_no_props_component(self):
        self._no_props_component(dynamic_views.DashNoPropsComponent)
        self._no_props_component(static_views.DashNoPropsComponent)

    def _test_meta_tags(self):
        self._meta_tags(dynamic_views.DashMetaTags)
        self._meta_tags(static_views.DashMetaTags)

    def _test_index_customization(self):
        self._index_customization(dynamic_views.DashIndexCustomization)
        self._index_customization(static_views.DashIndexCustomization)

    def _test_assets(self):
        self._assets(dynamic_views.DashAssets)
        self._assets(static_views.DashAssets)

    def _test_external_files_init(self):
        self._external_files_init(dynamic_views.DashExternalFilesInit)
        self._external_files_init(static_views.DashExternalFilesInit)

    def _test_func_layout_accepted(self):
        self._func_layout_accepted(dynamic_views.DashFuncLayoutAccepted)
        self._func_layout_accepted(static_views.DashFuncLayoutAccepted)

    def _test_late_component_register(self):
        self._late_component_register(dynamic_views.DashLateComponentRegister)
        self._late_component_register(static_views.DashLateComponentRegister)

    def _test_multi_output(self):
        self._multi_output(dynamic_views.DashMultiOutput)
        self._multi_output(static_views.DashMultiOutput)

    def _test_multi_output_no_update(self):
        self._multi_output_no_update(dynamic_views.DashMultiOutputNoUpdate)
        self._multi_output_no_update(static_views.DashMultiOutputNoUpdate)

    def _test_no_update_chains(self):
        self._no_update_chains(dynamic_views.DashNoUpdateChains)
        self._no_update_chains(static_views.DashNoUpdateChains)

    def test_with_custom_renderer(self):
        self._with_custom_renderer(dynamic_views.DashWithCustomRenderer)
        self._with_custom_renderer(static_views.DashWithCustomRenderer)

    def _test_modified_response(self):
        self._modified_response(dynamic_views.DashModifiedResponse)
        # self._modified_response(static_views.DashModifiedResponse)

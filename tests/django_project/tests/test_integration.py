import itertools
import re
import json
import time

from .IntegrationTests import IntegrationTests
from .utils import assert_clean_console, wait_for

from ..dynamic_dash import views as dynamic_views
from ..static_dash import views as static_views


class Tests(IntegrationTests):
    def _simple_callback(self, view_class):
        self.open('dash/{}/'.format(view_class.dash_name))

        output1 = self.wait_for_element_by_id('output-1')
        wait_for(lambda: output1.text == 'initial value', timeout=20)

        input1 = self.wait_for_element_by_id('input')
        input1.clear()

        input1.send_keys('hello world')

        output1 = self.wait_for_text_to_equal('#output-1', 'hello world')

        self.assertEqual(
            view_class.call_count.value,
            # an initial call to retrieve the first value
            1 +
            # one for each hello world character
            len('hello world')
        )

        assert_clean_console(self)

    def _wildcard_callback(self, view_class):
        self.open('dash/{}/'.format(view_class.dash_name))

        output1 = self.wait_for_text_to_equal('#output-1', 'initial value')

        input1 = self.wait_for_element_by_id('input')
        input1.clear()

        input1.send_keys('hello world')

        output1 = self.wait_for_text_to_equal('#output-1', 'hello world')

        self.assertEqual(
            view_class.call_count.value,
            # an initial call
            1 +
            # one for each hello world character
            len('hello world')
        )

        assert_clean_console(self)

    def _aborted_callback(self, view_class):
        """Raising PreventUpdate prevents update and triggering dependencies
        """
        self.open('dash/{}/'.format(view_class.dash_name))

        input_ = self.wait_for_element_by_id('input')
        input_.clear()
        input_.send_keys('x')
        output1 = self.wait_for_element_by_id('output1')
        output2 = self.wait_for_element_by_id('output2')

        # callback1 runs twice (initial page load and through send_keys)
        self.assertEqual(view_class.callback1_count.value, 2)

        # callback2 is never triggered, even on initial load
        self.assertEqual(view_class.callback2_count.value, 0)

        # double check that output1 and output2 children were not updated
        self.assertEqual(output1.text, view_class.initial_output)
        self.assertEqual(output2.text, view_class.initial_output)

        assert_clean_console(self)

    def _wildcard_data_attributes(self, view_class):
        self.open('dash/{}/'.format(view_class.dash_name))

        div = self.wait_for_element_by_id('data-element')

        # React wraps text and numbers with e.g. <!-- react-text: 20 -->
        # Remove those
        comment_regex = '<!--[^\[](.*?)-->'

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

        assert_clean_console(self)

    def _flow_component(self, view_class):
        self.open('dash/{}/'.format(view_class.dash_name))

        self.wait_for_element_by_id('waitfor')

    def _no_props_component(self, view_class):
        self.open('dash/{}/'.format(view_class.dash_name))

        assert_clean_console(self)

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

    def test_simple_callback(self):
        self._simple_callback(dynamic_views.DashSimpleCallback)
        self._simple_callback(static_views.DashSimpleCallback)

    def test_wildcard_callback(self):
        self._wildcard_callback(dynamic_views.DashWildcardCallback)
        self._wildcard_callback(static_views.DashWildcardCallback)

    def test_aborted_callback(self):
        self._aborted_callback(dynamic_views.DashAbortedCallback)
        self._aborted_callback(static_views.DashAbortedCallback)

    def test_wildcard_data_attributes(self):
        self._wildcard_data_attributes(dynamic_views.DashWildcardDataAttributes)
        self._wildcard_data_attributes(static_views.DashWildcardDataAttributes)

    def test_flow_component(self):
        self._flow_component(dynamic_views.DashFlowComponent)
        self._flow_component(static_views.DashFlowComponent)

    def test_no_props_component(self):
        self._no_props_component(dynamic_views.DashNoPropsComponent)
        self._no_props_component(static_views.DashNoPropsComponent)

    def test_meta_tags(self):
        self._meta_tags(dynamic_views.DashMetaTags)
        self._meta_tags(static_views.DashMetaTags)

    def test_index_customization(self):
        self._index_customization(dynamic_views.DashIndexCustomization)
        self._index_customization(static_views.DashIndexCustomization)

    def test_assets(self):
        self._assets(dynamic_views.DashAssets)
        self._assets(static_views.DashAssets)

    def test_external_files_init(self):
        self._external_files_init(dynamic_views.DashExternalFilesInit)
        self._external_files_init(static_views.DashExternalFilesInit)

    def test_func_layout_accepted(self):
        self._func_layout_accepted(dynamic_views.DashFuncLayoutAccepted)
        self._func_layout_accepted(static_views.DashFuncLayoutAccepted)

    def test_late_component_register(self):
        self._late_component_register(dynamic_views.DashLateComponentRegister)
        self._late_component_register(static_views.DashLateComponentRegister)

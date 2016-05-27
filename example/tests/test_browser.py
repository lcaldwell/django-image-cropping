from __future__ import division

import os

from pyvirtualdisplay import Display
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

from django.core.urlresolvers import reverse
from django.test.utils import override_settings

from image_cropping.config import settings

from . import factory

try:
    from django.contrib.staticfiles.testing import (
        StaticLiveServerTestCase as LiveServerTestCase)
except ImportError:
    from django.test import LiveServerTestCase

FIXTURES_LOCATION = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static',
    'images'
)


class BrowserTestBase(object):

    @classmethod
    def setUpClass(cls):
        if settings.HEADLESS:
            cls.display = Display(visible=0, size=(1024, 768))
            cls.display.start()
        cls.selenium = WebDriver()
        super(BrowserTestBase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        if settings.HEADLESS:
            cls.display.stop()
        super(BrowserTestBase, cls).tearDownClass()

    def setUp(self):
        self.image = factory.create_cropped_image()
        self.user = factory.create_superuser()
        super(BrowserTestBase, self).setUp()

    def _get_fixture_path(self, image_name):
        path = os.path.join(FIXTURES_LOCATION, image_name)
        return path

    def _wait_for_element_with_css(self, css_selector):
        element = WebDriverWait(self.selenium, timeout=45).until(
            lambda b:
                b.find_element_by_css_selector(css_selector)
        )
        return element

    def _ensure_images_roughly_match(self, image_element, width, height):
        aspect_ratio = width / height
        img_width = int(image_element.get_attribute('naturalWidth'))
        img_height = int(image_element.get_attribute('naturalHeight'))
        img_aspect_ratio = img_width / img_height
        ratios_nearly_equal = (
            0.98 * img_aspect_ratio <= aspect_ratio <= 1.02 * img_aspect_ratio
        )
        self.assertTrue(ratios_nearly_equal)

    def _ensure_page_loaded(self, url=None):
        # see: http://stackoverflow.com/questions/18729483/
        #             reliably-detect-page-load-or-time-out-selenium-2
        def readystate_complete(d):
            return d.execute_script("return document.readyState") == "complete"

        try:
            if url:
                self.selenium.get(url)
            WebDriverWait(self.selenium, 45).until(readystate_complete)
        except TimeoutException:
            self.selenium.execute_script("window.stop();")

    def _ensure_widget_rendered(self, **options):
        defaults = {
            'data-min-width': '120',
            'data-min-height': '100',
            'data-image-field': 'image_field',
            'data-my-name': 'cropping',
            'data-allow-fullsize': 'true',
            'data-size-warning': 'false',
            'data-adapt-rotation': 'false'
        }
        defaults.update(options)
        widget = self.selenium.find_element_by_css_selector('.image-ratio')
        for attr in defaults.keys():
            self.assertEqual(widget.get_attribute(attr), defaults[attr])

    def _ensure_thumbnail_rendered(self):
        img = self._wait_for_element_with_css('.image-ratio + img')
        # check images have same aspect ratio, since they no longer share urls
        stored_image = self.image.image_field
        self._ensure_images_roughly_match(
            img, stored_image.width, stored_image.height
        )

    def _ensure_jcrop_initialized(self):
        # make sure Jcrop is properly loaded
        def jcrop_initialized(d):
            try:
                d.find_element_by_css_selector('.jcrop-holder')
            except NoSuchElementException:
                return False
            return True

        try:
            WebDriverWait(self.selenium, 45).until(jcrop_initialized)
        except TimeoutException:
            self.selenium.execute_script("window.stop();")
            self.fail('Jcrop not initialized')


class AdminImageCroppingTestCase(BrowserTestBase, LiveServerTestCase):

    def setUp(self):
        super(AdminImageCroppingTestCase, self).setUp()
        self._ensure_page_loaded('%s%s' % (self.live_server_url, '/admin'))
        username_input = self.selenium.find_element_by_id("id_username")
        password_input = self.selenium.find_element_by_id("id_password")
        username_input.send_keys(factory.TEST_USERNAME)
        password_input.send_keys(factory.TEST_PASSWORD)
        self.selenium.find_element_by_xpath('//input[@value="Log in"]').click()
        self._ensure_page_loaded()


class AdminTest(AdminImageCroppingTestCase):

    def test_widget_rendered(self):
        edit_view = reverse('admin:example_image_change', args=[self.image.pk])
        self._ensure_page_loaded('%s%s' % (self.live_server_url, edit_view))
        self._ensure_widget_rendered()
        self._ensure_thumbnail_rendered()

    def test_live_update(self):
        add_view = reverse('admin:example_image_add')
        self._ensure_page_loaded('%s%s' % (self.live_server_url, add_view))
        image_input = self.selenium.find_element_by_xpath(
            '//input[@id="id_image_field"]')
        image_path = self._get_fixture_path('example_image.jpg')
        image_input.send_keys(image_path)
        self._ensure_thumbnail_rendered()
        self._ensure_jcrop_initialized()

    def test_exif_respected(self):
        add_view = reverse('admin:example_image_add')
        self._ensure_page_loaded('%s%s' % (self.live_server_url, add_view))
        image_input = self.selenium.find_element_by_xpath(
            '//input[@id="id_image_field"]')
        image_path = self._get_fixture_path('example_exif_6_image.jpg')
        image_input.send_keys(image_path)
        img = self._wait_for_element_with_css('.image-ratio + img')
        img_width = int(img.get_attribute('naturalWidth'))
        img_height = int(img.get_attribute('naturalHeight'))
        self.assertEqual(img_width, 600)
        self.assertEqual(img_height, 450)
        # Save and check dimensions of saved image match those of original
        self.selenium.find_element_by_xpath(
            '//input[@value="Save and continue editing"]').click()
        stored_img = self._wait_for_element_with_css('.image-ratio + img')
        self._ensure_images_roughly_match(stored_img, img_width, img_height)


class ModelFormCroppingTestCase(BrowserTestBase, LiveServerTestCase):

    def test_widget_rendered(self):
        edit_view = reverse('modelform_example', args=[self.image.pk])
        self._ensure_page_loaded('%s%s' % (self.live_server_url, edit_view))
        self._ensure_widget_rendered()
        self._ensure_thumbnail_rendered()

    def test_live_update(self):
        add_view = reverse('modelform_example')
        self._ensure_page_loaded('%s%s' % (self.live_server_url, add_view))
        image_input = self.selenium.find_element_by_xpath(
            '//input[@id="id_image_field"]')
        image_path = self._get_fixture_path('example_image.jpg')
        image_input.send_keys(image_path)
        self._ensure_thumbnail_rendered()
        self._ensure_jcrop_initialized()


class CropForeignKeyTest(AdminImageCroppingTestCase):

    def test_fk_cropping(self):
        changelist_view = reverse('admin:example_imagefk_changelist')
        self._ensure_page_loaded('%s%s' % (self.live_server_url, changelist_view))
        self.selenium.find_element_by_css_selector('.addlink').click()
        self.selenium.find_element_by_css_selector('#lookup_id_image').click()
        self.selenium.switch_to_window(self.selenium.window_handles[1])
        self.selenium.find_element_by_css_selector('#result_list a').click()
        self.selenium.switch_to_window(self.selenium.window_handles[0])
        self.selenium.find_element_by_xpath(
            '//input[@value="Save and continue editing"]').click()
        self._ensure_jcrop_initialized()
        self.selenium.find_element_by_css_selector('.jcrop-holder')
        self._ensure_widget_rendered(**{
            'data-allow-fullsize': 'false',
            'data-image-field': 'image'}
        )
        self._ensure_thumbnail_rendered()

    def test_fk_cropping_with_non_existent_fk_target(self):
        """Test if referencing a non existing image as fk target is not allowed"""
        changelist_view = reverse('admin:example_imagefk_changelist')
        self._ensure_page_loaded('%s%s' % (self.live_server_url, changelist_view))
        self.selenium.find_element_by_css_selector('.addlink').click()
        image_input = self.selenium.find_element_by_id("id_image")
        image_input.send_keys('10')
        self.selenium.find_element_by_xpath(
            '//input[@value="Save and continue editing"]').click()
        self._ensure_page_loaded()
        self.selenium.find_element_by_css_selector('.form-row.errors.field-image')


class SettingsTest(AdminImageCroppingTestCase):

    def test_widget_width_default(self):
        edit_view = reverse('admin:example_image_change', args=[self.image.pk])
        self._ensure_page_loaded('%s%s' % (self.live_server_url, edit_view))
        img = self.selenium.find_element_by_css_selector('.image-ratio + img')
        self.assertEqual(
            int(img.get_attribute('width')), settings.IMAGE_CROPPING_THUMB_SIZE[0])

    @override_settings(IMAGE_CROPPING_THUMB_SIZE=(500, 500))
    def test_widget_width_overridden(self):
        edit_view = reverse('admin:example_image_change', args=[self.image.pk])
        self._ensure_page_loaded('%s%s' % (self.live_server_url, edit_view))
        img = self.selenium.find_element_by_css_selector('.image-ratio + img')
        self.assertEqual(int(img.get_attribute('width')), 500)

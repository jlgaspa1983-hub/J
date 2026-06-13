import json
import pytest
import unittest

from modules.sfp_xquik import sfp_xquik
from sflib import SpiderFoot
from spiderfoot import SpiderFootEvent, SpiderFootTarget


@pytest.mark.usefixtures
class TestModuleXquik(unittest.TestCase):

    def test_opts(self):
        module = sfp_xquik()
        self.assertEqual(len(module.opts), len(module.optdescs))

    def test_setup(self):
        sf = SpiderFoot(self.default_options)
        module = sfp_xquik()
        module.setup(sf, dict())

    def test_watchedEvents_should_return_list(self):
        module = sfp_xquik()
        self.assertIsInstance(module.watchedEvents(), list)

    def test_producedEvents_should_return_list(self):
        module = sfp_xquik()
        self.assertIsInstance(module.producedEvents(), list)

    def test_extract_handle_should_parse_x_profile_url(self):
        module = sfp_xquik()
        result = module.extract_handle("X: <SFURL>https://x.com/xquik</SFURL>")
        self.assertEqual(result, "xquik")

    def test_extract_handle_should_skip_status_url(self):
        module = sfp_xquik()
        result = module.extract_handle("Twitter: <SFURL>https://twitter.com/xquik/status/1</SFURL>")
        self.assertIsNone(result)

    def test_handleEvent_no_api_key_should_set_errorState(self):
        sf = SpiderFoot(self.default_options)

        module = sfp_xquik()
        module.setup(sf, dict())

        target_value = 'spiderfoot.net'
        target_type = 'INTERNET_NAME'
        target = SpiderFootTarget(target_value, target_type)
        module.setTarget(target)

        event_type = 'SOCIAL_MEDIA'
        event_data = 'Twitter: <SFURL>https://twitter.com/xquik</SFURL>'
        event_module = 'example module'
        source_event = SpiderFootEvent('ROOT', target_value, '', '')
        evt = SpiderFootEvent(event_type, event_data, event_module, source_event)

        result = module.handleEvent(evt)

        self.assertIsNone(result)
        self.assertTrue(module.errorState)

    def test_handleEvent_should_emit_raw_data_and_username(self):
        sf = SpiderFoot(self.default_options)

        module = sfp_xquik()
        module.setup(sf, {"api_key": "test-key"})

        target_value = 'spiderfoot.net'
        target_type = 'INTERNET_NAME'
        target = SpiderFootTarget(target_value, target_type)
        module.setTarget(target)

        captured = list()

        def new_fetchUrl(url, timeout=0, useragent=None, headers=None):
            self.assertEqual(url, "https://xquik.com/api/v1/x/users/xquik")
            self.assertEqual(timeout, 30)
            self.assertEqual(useragent, "SpiderFoot")
            self.assertEqual(headers, {"x-api-key": "test-key"})
            return {
                "code": "200",
                "content": json.dumps({"data": {"username": "xquik", "followersCount": 42}})
            }

        def new_notifyListeners(self, event):
            captured.append(event)

        sf.fetchUrl = new_fetchUrl
        module.notifyListeners = new_notifyListeners.__get__(module, sfp_xquik)

        event_type = 'SOCIAL_MEDIA'
        event_data = 'Twitter: <SFURL>https://twitter.com/xquik</SFURL>'
        event_module = 'example module'
        source_event = SpiderFootEvent('ROOT', target_value, '', '')
        evt = SpiderFootEvent(event_type, event_data, event_module, source_event)

        result = module.handleEvent(evt)

        self.assertIsNone(result)
        self.assertEqual([event.eventType for event in captured], ["RAW_RIR_DATA", "USERNAME"])
        self.assertEqual(captured[1].data, "xquik")

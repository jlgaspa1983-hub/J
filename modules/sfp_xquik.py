# -------------------------------------------------------------------------------
# Name:         sfp_xquik
# Purpose:      Query Xquik for X/Twitter profile information.
#
# Author:      SpiderFoot contributors
#
# Created:     2026-06-13
# Copyright:   (c) SpiderFoot contributors 2026
# Licence:     MIT
# -------------------------------------------------------------------------------

import json
import re
import urllib.parse

from spiderfoot import SpiderFootEvent, SpiderFootPlugin


class sfp_xquik(SpiderFootPlugin):

    meta = {
        'name': "Xquik",
        'summary': "Gather X/Twitter user profile details from Xquik.",
        'flags': ["apikey"],
        'useCases': ["Footprint", "Investigate", "Passive"],
        'categories': ["Social Media"],
        'dataSource': {
            'website': "https://xquik.com/",
            'model': "FREE_AUTH_LIMITED",
            'references': [
                "https://docs.xquik.com/api-reference/overview"
            ],
            'apiKeyInstructions': [
                "Visit https://xquik.com/",
                "Create or sign in to your account",
                "Open API keys from the dashboard",
                "Create an API key and paste it into the module options"
            ],
            'favIcon': "https://xquik.com/icon.svg",
            'logo': "https://xquik.com/icon.svg",
            'description': "Xquik provides X/Twitter data APIs for profile lookup, "
            "tweet search, media download, monitoring, and automation workflows.",
        }
    }

    opts = {
        "api_key": "",
        "base_url": "https://xquik.com/api/v1"
    }

    optdescs = {
        "api_key": "Xquik API key.",
        "base_url": "Xquik API base URL."
    }

    handle_re = re.compile(r"^[A-Za-z0-9_]{1,15}$")

    results = None
    errorState = False

    def setup(self, sfc, userOpts=dict()):
        self.sf = sfc
        self.__dataSource__ = "Xquik"
        self.results = self.tempStorage()
        self.errorState = False

        for opt in list(userOpts.keys()):
            self.opts[opt] = userOpts[opt]

    def watchedEvents(self):
        return ["SOCIAL_MEDIA"]

    def producedEvents(self):
        return ["RAW_RIR_DATA", "USERNAME"]

    def extract_handle(self, event_data):
        try:
            network, value = event_data.split(": ", 1)
        except ValueError:
            return None

        if network.lower() not in ["twitter", "x"]:
            return None

        url = value.replace("<SFURL>", "").replace("</SFURL>", "").strip()

        try:
            parsed = urllib.parse.urlparse(url)
        except Exception:
            return None

        if parsed.scheme not in ["http", "https"]:
            return None

        if parsed.netloc.lower() not in ["twitter.com", "www.twitter.com", "x.com", "www.x.com"]:
            return None

        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) != 1:
            return None

        handle = parts[0].lstrip("@")
        if not self.handle_re.match(handle):
            return None

        if handle.lower() in ["home", "explore", "i", "intent", "messages", "notifications", "search"]:
            return None

        return handle

    def query(self, handle):
        base_url = self.opts["base_url"].rstrip("/")
        user = urllib.parse.quote(handle, safe="")
        headers = {
            "x-api-key": self.opts["api_key"]
        }

        return self.sf.fetchUrl(f"{base_url}/x/users/{user}",
                                timeout=self.opts.get("_fetchtimeout", 30),
                                useragent="SpiderFoot",
                                headers=headers)

    def handleEvent(self, event):
        eventData = event.data

        if self.errorState:
            return

        handle = self.extract_handle(eventData)
        if handle is None:
            return

        lookup_key = handle.lower()
        if lookup_key in self.results:
            return

        self.results[lookup_key] = True

        if self.opts["api_key"] == "":
            self.error("You enabled sfp_xquik but did not set an API key!")
            self.errorState = True
            return

        res = self.query(handle)
        if not res or not res.get("content"):
            return

        code = str(res.get("code"))
        if code in ["401", "402", "403"]:
            self.error(f"Xquik API request failed with HTTP {code}.")
            self.errorState = True
            return

        if code != "200":
            self.debug(f"Xquik API request failed with HTTP {code}.")
            return

        try:
            data = json.loads(res["content"])
        except Exception as e:
            self.error(f"Error processing JSON response from Xquik: {e}")
            return

        evt = SpiderFootEvent("RAW_RIR_DATA", json.dumps(data, sort_keys=True),
                              self.__name__, event)
        self.notifyListeners(evt)

        payload = data.get("data", data)
        if not isinstance(payload, dict):
            return

        username = payload.get("username") or payload.get("screen_name") or payload.get("handle")
        if not username or not isinstance(username, str):
            return

        username = username.lstrip("@")
        if not self.handle_re.match(username):
            return

        evt = SpiderFootEvent("USERNAME", username, self.__name__, event)
        self.notifyListeners(evt)

# End of sfp_xquik class

import asyncio
import os
import shutil
import sys
import unittest
from unittest.mock import patch

from pyppeteer import launch
from pyppeteer.errors import PageError
import yarl

from snare.cloner import BaseCloner, HeadlessCloner
from snare.utils.asyncmock import AsyncMock
from snare.utils.page_path_generator import generate_unique_path


class TestCloner(unittest.TestCase):
    def setUp(self):
        self.url = yarl.URL("http://example.com")
        self.main_page_path = generate_unique_path()
        os.makedirs(self.main_page_path)
        self.max_depth = sys.maxsize
        self.css_validate = False
        self.loop = asyncio.get_event_loop()
        self.base_handler = BaseCloner(self.url, self.max_depth, self.css_validate)
        self.headless_handler = HeadlessCloner(self.url, self.max_depth, self.css_validate)

    def test_basecloner_fetch_data(self):
        async def test():
            with self.assertRaises(NotImplementedError):
                _, _, _, _ = await self.base_handler.fetch_data(None, self.url, 0, 0)

        self.loop.run_until_complete(test())

    @patch("pyppeteer.browser.Browser")
    def test_headlesscloner_fetch_data_exception(self, mock_browser):
        mock_browser.newPage = AsyncMock(side_effect=PageError("Failed to create new page"))

        async def test():
            await self.headless_handler.fetch_data(mock_browser, self.url, 0, 0)

        with self.assertLogs(level="ERROR") as log:
            self.loop.run_until_complete(test())
            self.assertIn("ERROR:snare.cloner:Failed to create new page", "".join(log.output))

    def test_headlesscloner_fetch_data_redirect(self):
        self.expected_redirect_url = yarl.URL("http://www.example.com")
        p = patch("pyppeteer.network_manager.Response.url", new=self.expected_redirect_url)
        p.start()

        self.redirect_url = None

        async def test():
            browser = await launch()
            self.redirect_url, _, _, _ = await self.headless_handler.fetch_data(browser, self.url, 0, 0)
            await browser.close()

        self.loop.run_until_complete(test())
        self.assertEqual(self.redirect_url, self.expected_redirect_url)

        p.stop()

    def tearDown(self):
        shutil.rmtree(self.main_page_path)
from scrapy import version_info
from scrapy.utils.decorator import inthread
from scrapy.utils.misc import load_object
from scrapy.exceptions import IgnoreRequest, NotSupported, NotConfigured

import time
import logging

from .http import WebdriverActionRequest, WebdriverRequest, WebdriverResponse

if map(int, version_info) < [0, 18]:
    FALLBACK_HANDLER = 'http.HttpDownloadHandler'
elif map(int, version_info) >= [0, 24, 4]:
    FALLBACK_HANDLER = 'http.HTTPDownloadHandler'
else:
    FALLBACK_HANDLER = 'http10.HTTP10DownloadHandler'
FALLBACK_HANDLER = 'scrapy.core.downloader.handlers.%s' % FALLBACK_HANDLER


class WebdriverDownloadHandler(object):
    """This download handler uses webdriver, deferred in a thread.

    Falls back to the stock scrapy download handler for non-webdriver requests.

    """
    def __init__(self, settings):
        self._enabled = settings.get('WEBDRIVER_BROWSER') is not None
        self._fallback_handler = load_object(FALLBACK_HANDLER)(settings)

    def download_request(self, request, spider):
        """Return the result of the right download method for the request."""
        if self._enabled and isinstance(request, WebdriverRequest):
            if isinstance(request, WebdriverActionRequest):
                download = self._do_action_request
            else:
                download = self._download_request
        else:
            download = self._fallback_handler.download_request
        return download(request, spider)

    @inthread
    def _download_request(self, request, spider):
        """Download a request URL using webdriver."""
        logging.log(logging.DEBUG, 'Downloading %s with webdriver' % request.url)
        try:
            request.manager.webdriver.get(request.url)
        except:
            logging.log(logging.ERROR, 'Running webdriver timeout %s' % request.url)
            try:
                request.manager.restart_webdriver.get(request.url)
            except:
                logging.log(logging.ERROR, 'Restart webdriver timeout %s' % request.url)
        time.sleep(5)
        return WebdriverResponse(request.url, request.manager.webdriver)

    @inthread
    def _do_action_request(self, request, spider):
        """Perform an action on a previously webdriver-loaded page."""
        logging.log(logging.DEBUG, 'Running webdriver actions %s' % request.url)
        request.actions.perform()
        return WebdriverResponse(request.url, request.manager.webdriver)

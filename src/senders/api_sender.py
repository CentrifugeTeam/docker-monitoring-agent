# import requests
# import logging

# class ApiSender:
#   def __init__(self, url, api_key):
#     self.url = url
#     self.headers = {
#       "Authorization": f"Bearer {api_key}",
#       "Content-Encoding": "gzip"
#     }
#     self.logger = logging.getLogger(__name__)

#   def send(self, data):
#     try:
#       response = requests.post(
#         self.url,
#         data=data,
#         headers=self.headers,
#         timeout=10
#       )
#       response.raise_for_status()
#     except Exception as e:
#       self.logger.error(f"API send failed: {e}")
#       raise

import logging

class ApiSender:
    def __init__(self, url, api_key):
        self.logger = logging.getLogger(__name__)
        self.logger.warning(
            "ApiSender is disabled in debug mode. "
            "Metrics will be logged instead of sent."
        )

    def send(self, data):
        self.logger.debug(
            f"Debug mode active. Would send: {len(data)} bytes"
            "\nUncomment sender in agent.py to enable"
        )

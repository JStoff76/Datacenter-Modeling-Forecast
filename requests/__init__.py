from urllib.parse import urlparse, urljoin


class Response:
    def __init__(self, content: bytes = b"", status_code: int = 200, headers=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}


class Session:
    def __init__(self):
        self.headers = {}

    def mount(self, prefix, adapter):
        return None

    def get(self, url, timeout=10):
        return Response()


class adapters:
    class HTTPAdapter:
        def __init__(self, max_retries=None):
            self.max_retries = max_retries


def get(url, timeout=10):
    return Response()


class utils:
    @staticmethod
    def urlparse(url):
        return urlparse(url)


class compat:
    urljoin = staticmethod(urljoin)

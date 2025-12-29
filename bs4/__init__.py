from html.parser import HTMLParser


class SimpleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = None
            for k, v in attrs:
                if k == "href":
                    href = v
            self.links.append((href, ""))

    def handle_data(self, data):
        self.text.append(data)


class Tag:
    def __init__(self, href, text):
        self.href = href
        self.text = text

    def get(self, name, default=None):
        if name == "href":
            return self.href
        return default

    def get_text(self, strip=False):
        return self.text.strip() if strip else self.text


class BeautifulSoup:
    def __init__(self, html: str, parser: str = "html.parser"):
        parser_obj = SimpleParser()
        parser_obj.feed(html)
        self._links = [Tag(href, "") for href, _ in parser_obj.links if href]
        self._text = " ".join(parser_obj.text)

    def find_all(self, tag, href=None):
        if tag == "a" and href is not None:
            return [t for t in self._links if t.href]
        return []

    def get_text(self, separator=" ", strip=False):
        return self._text.strip() if strip else self._text

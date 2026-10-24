"""Conservative initial-App static declarations; not a JavaScript/HTML sandbox.

Supported: inline HTML, CSS and scripts; well-nested static SVG; local fragment
references; base64 PNG/JPEG/GIF/WebP image declarations. Relative/remote URLs,
external scripts/styles, nested documents, SVG animation and ambiguous resource
forms require separate qualification. Image signatures are not decoder safety
validation. Native settings/CSP, authored JavaScript and runtime data still need
their own review. This module never fetches, renders or executes supplied text.
"""
import base64
import binascii
from html.parser import HTMLParser
import re

ERROR = "app.initial_external_resource_requires_separate_qualification"
HTML_TAGS = set("""html head body title meta style script main header footer nav aside
section article div span p h1 h2 h3 h4 h5 h6 hgroup address blockquote pre code samp
kbd var strong em i b u s small mark sub sup br hr wbr abbr cite time data a button
input label select option optgroup textarea form fieldset legend details summary
dialog ul ol li dl dt dd table caption colgroup col thead tbody tfoot tr th td img
picture source video audio canvas output meter progress datalist map area ruby rt rp
ins del bdi bdo q template slot svg""".split())
SVG_TAGS = set("""svg g symbol view switch path rect circle ellipse line polyline polygon text tspan
textpath title desc defs clippath mask lineargradient radialgradient stop pattern
image use filter feimage fegaussianblur feoffset fecolormatrix feblend feflood
fecomponenttransfer fefuncr fefuncg fefuncb fefunca femerge femergenode fecomposite
fedropshadow feturbulence""".split())
UNSUPPORTED_ATTRIBUTES = {
    "srcset", "imagesrcset", "imagesizes", "srcdoc", "ping", "action", "formaction",
    "manifest", "xml:base", "codebase", "archive", "classid", "profile", "is", "lowsrc", "dynsrc",
}
SVG_CSS_ATTRIBUTES = {
    "fill", "stroke", "filter", "clip-path", "mask", "cursor", "marker",
    "marker-start", "marker-mid", "marker-end", "color-profile",
}
CSS_AT_RULES = {"media", "supports", "container", "layer", "keyframes",
                "-webkit-keyframes", "font-face", "page", "property", "starting-style"}
CSS_STRING_URL_FUNCTIONS = {"image", "image-set", "-webkit-image-set", "src"}
WS = " \t\r\n\f"
HEX = "0123456789abcdefABCDEF"


def require(condition):
    if not condition:
        raise ValueError(ERROR)


def local_url(value, image=False):
    """Only context-appropriate inert local references, after HTML/CSS decoding."""
    require(type(value) is str)
    value = value.strip(WS)
    require(value and not any(ord(c) < 32 or ord(c) == 127 for c in value))
    if re.fullmatch(r"#(?:[A-Za-z0-9_][A-Za-z0-9_.:-]*)?", value):
        return
    match = re.fullmatch(r"data:image/(png|jpeg|gif|webp);base64,([A-Za-z0-9+/]*={0,2})", value, re.I)
    require(image and match is not None)
    try:
        raw = base64.b64decode(match[2], validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError(ERROR) from exc
    kind = match[1].lower()
    require((kind == "png" and raw.startswith(b"\x89PNG\r\n\x1a\n")) or
            (kind == "jpeg" and raw.startswith(b"\xff\xd8\xff")) or
            (kind == "gif" and raw[:6] in (b"GIF87a", b"GIF89a")) or
            (kind == "webp" and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"))


def css_escape(text, at):
    """Consume one CSS escape without turning an escaped quote into syntax."""
    at += 1
    require(at < len(text))
    if text[at] in "\r\n\f":
        end = at + (2 if text[at:at + 2] == "\r\n" else 1)
        return "", end
    end = at
    while end < min(at + 6, len(text)) and text[end] in HEX:
        end += 1
    if end > at:
        code = int(text[at:end], 16)
        require(0 < code <= 0x10ffff and not 0xd800 <= code <= 0xdfff)
        if end < len(text) and text[end] in WS:
            end += 2 if text[end:end + 2] == "\r\n" else 1
        return chr(code), end
    return text[at], at + 1


def css_string(text, at):
    quote, result = text[at], []
    at += 1
    while at < len(text):
        char = text[at]
        if char == quote:
            return "".join(result), at + 1
        require(char not in "\r\n\f")
        if char == "\\":
            char, at = css_escape(text, at)
        else:
            at += 1
        result.append(char)
    raise ValueError(ERROR)


def css_space(text, at):
    while at < len(text):
        if text[at] in WS:
            at += 1
        elif text.startswith("/*", at):
            end = text.find("*/", at + 2)
            require(end >= 0)
            at = end + 2
        else:
            break
    return at


def css_word(text, at):
    word = []
    while at < len(text):
        char = text[at]
        if char == "\\":
            char, at = css_escape(text, at)
        elif char.isalnum() or char in "_-" or ord(char) >= 128:
            at += 1
        else:
            break
        word.append(char)
    return "".join(word).lower(), at


def css_url(text, at):
    # at is after '('; comments/malformed nested tokens inside URL are unsupported.
    while at < len(text) and text[at] in WS:
        at += 1
    require(at < len(text))
    if text[at] in "\"'":
        value, at = css_string(text, at)
        while at < len(text) and text[at] in WS:
            at += 1
    else:
        chars = []
        while at < len(text) and text[at] != ")":
            char = text[at]
            require(char not in "\"'(" and not text.startswith("/*", at))
            if char == "\\":
                char, at = css_escape(text, at)
            else:
                at += 1
            chars.append(char)
        value = "".join(chars).strip(WS)
        require(not any(c in WS for c in value))
    require(at < len(text) and text[at] == ")")
    local_url(value, image=True)
    return at + 1


def check_css(text):
    """Scan CSS tokens, preserving string/comment boundaries and CSS escapes.

    Unknown at-rules and image functions accepting bare URL strings are outside
    this subset. Ordinary strings (for example content labels) are not URLs.
    """
    at = 0
    while at < len(text):
        at = css_space(text, at)
        if at == len(text):
            break
        char = text[at]
        if char in "\"'":
            _, at = css_string(text, at)
        elif char == "@":
            word, at = css_word(text, at + 1)
            require(word in CSS_AT_RULES)
        elif char.isalpha() or char in "_-\\" or ord(char) >= 128:
            word, at = css_word(text, at)
            next_at = css_space(text, at)
            if next_at < len(text) and text[next_at] == "(":
                require(word not in CSS_STRING_URL_FUNCTIONS)
                if word == "url":
                    at = css_url(text, next_at + 1)
        else:
            at += 1


class StaticResources(HTMLParser):
    def __init__(self):
        # Attribute entities are decoded by HTMLParser in either mode. Keeping
        # text entities separate distinguishes escaped '<' from malformed markup.
        super().__init__(convert_charrefs=False)
        self.svg = []
        self.raw_tag = None
        self.style_parts = []

    def handle_starttag(self, tag, attrs):
        require(tag in (SVG_TAGS if self.svg else HTML_TAGS))
        names = [key for key, _ in attrs]
        require(len(names) == len(set(names)))
        attributes = dict(attrs)
        if self.svg or tag == "svg":
            self.svg.append(tag)
        if tag == "script":
            require("src" not in attributes and
                    (attributes.get("type") or "").strip().lower() not in {"importmap", "speculationrules"})
        if tag == "meta":
            require("http-equiv" not in attributes)
        if tag == "style":
            require((attributes.get("type") or "text/css").strip().lower() == "text/css")
        for name, value in attrs:
            require(name not in UNSUPPORTED_ATTRIBUTES)
            require(":" not in name or name in {"xlink:href", "xmlns:xlink", "xml:lang", "xml:space"})
            if name in {"src", "href", "xlink:href", "poster", "background", "cite", "longdesc", "usemap"}:
                image = ((name == "src" and tag in {"img", "input"}) or
                         (name in {"href", "xlink:href"} and tag in {"image", "feimage"}) or
                         (name == "poster" and tag == "video") or
                         (name == "background" and tag in {"body", "table", "td", "th"}))
                require(image or (name in {"href", "xlink:href"} and tag in {
                            "a", "area", "use", "textpath", "lineargradient", "radialgradient", "pattern"}) or
                        name in {"cite", "longdesc", "usemap"})
                local_url(value, image=image)
            elif name == "style" or (self.svg and name in SVG_CSS_ATTRIBUTES):
                require(type(value) is str)
                check_css(value)
            elif name in {"xmlns", "xmlns:xlink"}:
                require(value in {"http://www.w3.org/2000/svg", "http://www.w3.org/1999/xhtml",
                                  "http://www.w3.org/1999/xlink"})
        if tag in {"script", "style"}:
            require(self.raw_tag is None)
            self.raw_tag = tag
            self.style_parts = []

    def handle_startendtag(self, tag, attrs):
        # HTML does not self-close raw-text tags, unlike HTMLParser's callback.
        require(tag not in {"script", "style"})
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.raw_tag is not None:
            require(tag == self.raw_tag)
            if tag == "style":
                check_css("".join(self.style_parts))
            self.raw_tag = None
        if self.svg:
            require(tag == self.svg[-1])
            self.svg.pop()

    def handle_data(self, data):
        if self.raw_tag == "style":
            self.style_parts.append(data)
        elif self.raw_tag != "script":
            require("<" not in data)

    def handle_comment(self, data):
        require(not any(part in data for part in ("<", ">", "--")))

    def handle_decl(self, decl):
        require(decl.strip().lower() == "doctype html")

    def unknown_decl(self, data):
        raise ValueError(ERROR)

    def handle_pi(self, data):
        raise ValueError(ERROR)


def check_initial_resources(html):
    require(not any((ord(c) < 32 and c not in "\t\r\n") or ord(c) == 127 for c in html))
    parser = StaticResources()
    parser.feed(html)
    parser.close()
    require(parser.raw_tag is None and not parser.svg)

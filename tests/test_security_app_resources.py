"""Synthetic initial-body declarations only: no browser, network or native calls."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "security_app_under_test", ROOT / "skills/omni-app-engineer/scripts/omni_app_native.py")
app = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = app
spec.loader.exec_module(app)

# Original, bounded inline fixture; no decoder is invoked by these checks.
PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aDWQAAAAASUVORK5CYII="


class InitialStaticResources(unittest.TestCase):
    def body(self, html):
        return {"html": html, "settings": copy.deepcopy(app.LOCKED_SETTINGS)}

    def rejected(self, html):
        with self.assertRaisesRegex(ValueError, "external_resource|static_resource"):
            app.initial_body(self.body(html))

    def test_original_equivalent_resource_bypasses(self):
        for html in ('<img src="https://synthetic.invalid/a.png">',
                     '<IMG SRC=https://synthetic.invalid/a.png>',
                     '<img src="https&#58;//synthetic.invalid/a.png">',
                     '<style>@import "https://synthetic.invalid/a.css";</style>'):
            with self.subTest(html=html):
                self.rejected(html)

    def test_urls_are_local_not_merely_non_https(self):
        for url in ('//synthetic.invalid/a.png', '/relative.png', 'relative.png',
                    'https:\\synthetic.invalid/a.png', 'blob:synthetic',
                    'data:image/svg+xml,<svg/>'):
            with self.subTest(url=url):
                self.rejected('<img src="' + url + '">')

    def test_css_escapes_comments_and_string_url_forms(self):
        for css in (r'.x{background:u\72l(//synthetic.invalid/a)}',
                    r'@\69mport "https://synthetic.invalid/a.css";',
                    '.x{background:URL(/* ambiguous */https://synthetic.invalid/a)}',
                    '.x{background:image-set("https://synthetic.invalid/a" 1x)}',
                    '.x{background:src("https://synthetic.invalid/a")}',
                    '.x{background:url("unterminated)}'):
            with self.subTest(css=css):
                self.rejected('<style>' + css + '</style>')
        self.rejected('<p style="background:url(&quot;https://synthetic.invalid/a&quot;)">x</p>')

    def test_ambiguous_and_nested_declarations_need_qualification(self):
        for html in ('<img srcset="https://synthetic.invalid/a 1x">',
                     '<base href="https://synthetic.invalid/">',
                     '<iframe srcdoc="&lt;img src=//synthetic.invalid/a&gt;"></iframe>',
                     '<object data="https://synthetic.invalid/a"></object>',
                     '<meta http-equiv=refresh content="0;url=https://synthetic.invalid/">',
                     '<link rel=stylesheet href="data:text/css,body{}">',
                     '<script type=importmap>{"imports":{"x":"https://synthetic.invalid/x"}}</script>',
                     '<img src="' + PNG + '" SRC="https://synthetic.invalid/a">'):
            with self.subTest(html=html):
                self.rejected(html)

    def test_svg_resource_and_parser_contexts(self):
        for html in ('<svg><image href="https://synthetic.invalid/a"/></svg>',
                     '<svg><use xlink:href="//synthetic.invalid/a#icon"/></svg>',
                     '<svg><set attributeName="href" to="https://synthetic.invalid/a"/></svg>',
                     '<svg><style><img src="https://synthetic.invalid/a"></style></svg>',
                     '<svg><foreignObject><p>x</p></foreignObject></svg>',
                     '<math><mtext>x</mtext></math>', '<style/>.x{background:url(//synthetic.invalid/a)}'):
            with self.subTest(html=html):
                self.rejected(html)

    def test_self_contained_app_css_and_static_svg_remain_valid(self):
        html = '''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
        <style>@media(max-width:600px){.grid{display:grid}} .x{background:url("''' + PNG + '''");filter:url(#soft)}
        .hint::after{content:"url(https://example.invalid) is explanatory text"}</style></head><body>
        <!-- owned-region --><main><a href="#details">Inspect</a><a href="#">Top</a><form><input type=search><button type=button>Search</button></form>
        <img src="''' + PNG + '''" alt="original fixture"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">
        <defs><filter id="soft"><feGaussianBlur stdDeviation="1"/></filter><path id="mark" d="M0 0L1 1"/>
        <linearGradient id="base"><stop offset="0%" stop-color="red"/></linearGradient><linearGradient id="tone" href="#base"/></defs>
        <use href="#mark"/><text x="1" y="2">A</text></svg><section id="details">Local evidence</section></main>
        <script>const example = "https://synthetic.invalid"; document.title = "Local App";</script></body></html>'''
        body = self.body(html)
        self.assertIs(app.initial_body(body), body)

    def test_inline_script_is_explicitly_not_a_javascript_sandbox(self):
        body = self.body('<script>const sourceText = \'<img src="https://synthetic.invalid/a">\';</script>')
        self.assertIs(app.initial_body(body), body)

    def test_locked_settings_and_embedded_image_shape(self):
        body = self.body('<p>Local</p>')
        body['settings']['safeDomainsEnabled'] = True
        with self.assertRaisesRegex(ValueError, 'locked_settings'):
            app.initial_body(body)
        self.rejected('<img src="data:image/png;base64,not-base64!">')


if __name__ == '__main__':
    unittest.main()

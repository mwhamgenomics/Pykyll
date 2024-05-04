import unittest
from unittest.mock import Mock
import pykyll


class TestFrontmatterPreProcessor(unittest.TestCase):
    def test_run(self):
        fake_md = Mock()
        p = pykyll.preprocessors.FrontmatterPreprocessor(fake_md)
        no_front_matter = ['body text']
        with_front_matter = [
            '---',
            "extends: 'post.html'",
            "title: 'A title'",
            'category: Programming',
            "tags: ['c', 'python']",
            'external_links:',
            "    - title: 'An external link'",
            '      link: https://github.com/mwhamgenomics',
            '---',
            'body text'
        ]

        self.assertListEqual(p.run(no_front_matter), ['body text'])
        self.assertDictEqual(fake_md.front_matter, {})
        fake_md.reset_mock()

        self.assertListEqual(p.run(with_front_matter), ['body text'])
        self.assertDictEqual(
            fake_md.front_matter,
            {
                'extends': 'post.html',
                'title': 'A title',
                'category': 'Programming',
                'tags': ['c', 'python'],
                'external_links': [{'title': 'An external link', 'link': 'https://github.com/mwhamgenomics'}]
            }
        )


class TestCodeBlockPreprocessor(unittest.TestCase):
    def test_run(self):
        p = pykyll.preprocessors.CodeBlockPreprocessor()
        content = [
            'body text',
            '```', 'some pseudocode', '```',

            '```bash',
            'for d in this that other',
            'do',
            '    ls -d ${d}',
            'done',
            '```',
            'more body text',
            '```jinja',
            '<!doctype html>',
            '<html lang="en">',
            '    <body>',
            '    Body text',
            '    </body>',
            '</html>',
            '```'
        ]
        obs = p.run(content)
        exp = [
            'body text',
            '```', 'some pseudocode', '```',
            '',
            '',
            '<div class="code">'
            '<div class="highlight">'
            '<pre>'
            '<span></span>'
            '<span class="k">for</span><span class="w"> </span>d<span class="w"> </span><span class="k">in</span><span class="w"> </span>this<span class="w"> </span>that<span class="w"> </span>other<br />'
            '<span class="k">do</span><br />'
            '<span class="w">    </span>ls<span class="w"> </span>-d<span class="w"> </span><span class="si">${</span><span class="nv">d</span><span class="si">}</span><br />'
            '<span class="k">done</span><br />'
            '</pre>'
            '</div><br />'
            '</div>',
            'more body text',
            '',
            '',
            '<div class="code">'
            '{% raw %}'
            '<div class="highlight">'
            '<pre>'
            '<span></span>'
            '<span class="x">&lt;!doctype html&gt;</span><br />'
            '<span class="x">&lt;html lang=&quot;en&quot;&gt;</span>'
            '<br />'
            '<span class="x">    &lt;body&gt;</span><br />'
            '<span class="x">    Body text</span><br />'
            '<span class="x">    &lt;/body&gt;</span><br />'
            '<span class="x">&lt;/html&gt;</span><br />'
            '</pre>'
            '</div><br />'
            '{% endraw %}'
            '</div>'
        ]
        self.assertListEqual(obs, exp)

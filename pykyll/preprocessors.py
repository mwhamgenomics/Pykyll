import re
import yaml
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, TextLexer
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor


class FrontmatterPreprocessor(Preprocessor):
    """
    Front matter extension for Python-Markdown. Adds a Jekyll-style Yaml field in front of a markdown template and adds
    it to a field in the Markdown object. Similar to MetaExtension but parses it as Yaml.

    Example:

    ---
    title: a title
    some:
        - more: metadata
          in: yaml format
    ---
    """

    boundary_line = '---'

    def run(self, lines):
        front_matter = []
        in_front_matter = False

        while lines:
            line = lines[0]

            if in_front_matter:
                lines.pop(0)
                if line == self.boundary_line:  # end of front matter
                    break
                else:
                    front_matter.append(line)

            else:
                if line == self.boundary_line:  # start of front matter
                    lines.pop(0)
                    in_front_matter = True
                else:  # not '---' and not encountered any front matter - assume none in file
                    break

        data = '\n'.join(front_matter)
        self.md.front_matter = yaml.safe_load(data) or {}
        return lines


class FrontMatterExtension(Extension):
    def extendMarkdown(self, md):
        md.registerExtension(self)
        self.md = md
        md.preprocessors.register(FrontmatterPreprocessor(md), 'frontmatter', 27)

    def reset(self):
        self.md.front_matter = {}


class CodeBlockPreprocessor(Preprocessor):
    """
    Modified version of the markdown-processor.py extension from Pygments:
    https://github.com/pygments/pygments/blob/master/external/markdown-processor.py
    https://pypi.python.org/pypi/Markdown

    Usage:

        import markdown
        html = markdown.markdown(someText, extensions=[CodeBlockExtension()])

    To generate a CSS stylesheet:
    `pygmentize -S <style> -f html > pygments.css`

    Available styles can be found in the Pygments source in pygments/styles/__init__.py.

    The processor in Pygments uses this syntax for highlighting:

        [sourcecode:lang]
        some code
        [/sourcecode]

    This one uses GitHub-style syntax:

        ```lang
        some code
        ```
    """
    pattern = re.compile(r'```([^\n]+)(.+?)```', re.S)
    formatter = HtmlFormatter()

    def run(self, lines):
        def repl(match):
            lang = match.group(1)
            code = match.group(2)

            lexer = get_lexer_by_name(lang)
            code = highlight(code, lexer, self.formatter)
            code = code.replace('\n\n', '\n&nbsp;\n').replace('\n', '<br />')
            if lang in ('jinja', 'jinja2'):
                code = '{% raw %}' + code + '{% endraw %}'  # special case - if it's Jinja2 code, don't interpret it

            return '\n\n<div class="code">%s</div>' % code

        joined_lines = '\n'.join(lines)
        joined_lines = self.pattern.sub(repl, joined_lines)
        return joined_lines.split('\n')


class CodeBlockExtension(Extension):
    def extendMarkdown(self, md):
        md.preprocessors.register(CodeBlockPreprocessor(), 'codeblock', 26)

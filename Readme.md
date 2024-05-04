Pykyll
------

> (ˈpɪkl̩) - A static site builder that does what I want.

This is what I use to build mwhamgenomics.github.io. I built it because of some frustrations I had with Jekyll, and
because it was 2020 and I had an itch to write something.

## Templating

The intended use case for building websites with Pykyll is to write Jekyll-style Markdown files with Yaml front matter.
These are interpreted by [Python-Markdown](https://python-markdown.github.io) into HTML. Syntax highlighting of code
blocks is done with [Pygments](https://pygments.org). This is then put through template processing with
[Jinja2](https://jinja.palletsprojects.com).

All you need to get started is a folder called 'templates', containing at least a Jinja template called 'base.html'
which defines a block called 'content':

```jinja
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Site title</title>
  </head>
  <body>
   {% block content %}{% endblock %}
  </body>
</html>
```

You can then write an MD file that will be picked up by this default template. Front matter is accessible via the value
`page.metadata`:

```jinja

---
some_metadata: [1, 2, 3]
---

Some content including {% page.metadata.some_metadata %}
```

If you want to write templates that extend `base.html`, you can refer to this by specifying the front matter value
`extends`:

```jinja

---
extends: another_template.html
---

Some content
```

## Syntax highlighting

Formatting of code blocks is done with Pygments. This will replace any triple-backquoted code blocks with formatted
HTML. You can specify languages as well:

```
\`\`\`python
def example():
    print('Some Python code')
\`\`\`

```

This won't do much without a stylesheet, but Pygments can output several highlighting styles as CSS, which can be
referenced in your Jinja templates:

    $ pygmentize -L styles  # prints available styles
    $ pygmentize -f html -S solarized-dark > css/syntax_highlighting.css


## Resources

Pykyll will build all resource files into the built site in the same tree structure as they are in the resource dir. Any
non-Markdown files will be built site as-is, without modification.

## Building

Basic usage of Pykyll is as below:

    $ python pykyll/__init__.py

By default, the source dir will be `.` (i.e. current working dir) and the build dir will be `./build`. Pykyll will not
try to build the build dir, so it's safe for the build dir to be inside the source dir. The build and source dirs can be
specified as arguments. Pykyll does a chdir to the source dir, so the build dir should be relative to it.

A file will be built in any of the following cases:

- The file's built counterpart does not yet exist in the build dir
- The source file is newer than the built counterpart
- The builder has been told to always build it with `--force <file>`
- The option `--force` (no files specified) has been used to always build everything

A file will *not* be built in any of the following cases:

- Its name starts with a `-` or `.`
- Any of the directories containing it start with a `-` or `.`
- In the case of MD files, the front matter field `publish: False` is present

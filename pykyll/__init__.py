import os
import sys
import yaml
import jinja2
import logging
import argparse
import markdown
from shutil import copyfile
from datetime import datetime, date
from pykyll import preprocessors, dev_server

with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'version.txt')) as f:
    __version__ = f.read().strip()

formatter = logging.Formatter('[%(asctime)s][%(name)s][%(levelname)s] %(message)s')
logger = logging.getLogger('pykyll')


class Pykyller:
    """
    Main site builder
    """
    md_converter = markdown.Markdown(
        extensions=[
            'markdown.extensions.fenced_code',
            'markdown.extensions.tables',
            preprocessors.FrontMatterExtension(),
            preprocessors.CodeBlockExtension()
        ]
    )

    def __init__(self, build_dir='build', templates_dir='templates', force_build=None):
        self.tree = {}
        self.site_info = {
            'categories': {},
            'tags': {},
            'posts': []
        }

        if os.path.isfile('config.yaml'):
            with open('config.yaml') as f:
                self.site_info.update(yaml.safe_load(f))

        self.build_dir = build_dir
        self.templates_dir = templates_dir
        self.ignore_dirs = (self.templates_dir, self.build_dir, 'pykyll', 'tests')

        self.jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(self.templates_dir))

        self.always_build = False
        self.force_build_files = []
        if force_build:  # ['this.html', 'that.html']
            self.force_build_files = force_build
        elif force_build is not None:  # []
            self.always_build = True

    def discover_pages(self):
        skip_prefixes = ('.', '_')

        for path, dirs, files in os.walk('.'):
            path = os.path.relpath(path)

            if path == '.':
                path = []
            else:
                path = path.split(os.path.sep)

            if path and (any(p[0] in skip_prefixes for p in path) or path[0] in self.ignore_dirs):
                continue

            for f in files:
                if f[0] in skip_prefixes:
                    continue

                if f == 'config.yaml':
                    continue

                self._build_tree(path, f)

    def _build_tree(self, path, filename):
        """
        Given a path of, e.g, this/that and filename other.txt, build a contents structure of:
        {
            'this': {
                'that': {
                    'other.txt': File('other.txt')
                }
            }
        }

        :param list path: Path to directory containing the file - like the first element in each result from os.walk
        :param str filename: Basename of the file to add

        """
        current_level = self.tree

        for part in path:
            if part not in current_level:
                current_level[part] = {}

            current_level = current_level[part]

        if filename not in current_level:
            base, ext = os.path.splitext(filename)
            if ext in ('.md', '.html'):
                cls = Page
            else:
                cls = File

            file_obj = cls(os.path.join(os.path.sep.join(path), filename), self)
            current_level[filename] = file_obj

        return current_level[filename]

    def traverse_tree(self, cls, func, current_level: dict=None):
        """
        Traverse through self.tree recursively, picking up all instances of cls and running func on it.
        :param cls:
        :param func: Takes a single argument corresponding to the object to process
        :param current_level: For recursion
        """
        if current_level is None:
            current_level = self.tree

        for k, v in current_level.items():
            if isinstance(v, cls):
                func(v)
            elif isinstance(v, dict):
                self.traverse_tree(cls, func, v)

    def build(self):
        """
        Run build() on all File objects
        """
        logger.info('Building site')

        def process_page(file):
            if file.should_build():
                logger.info('Building %s' % file)
                file.build()

        self.traverse_tree(File, process_page)

        logger.info('Done')

    def process(self):
        """
        Collect information on categories and tags, and populate automatic Post fields.
        """
        def process_page(post):
            if post.unpublished():
                return

            category = post.metadata.get('category')
            tags = post.metadata.get('tags', [])

            if category:
                if category not in self.site_info['categories']:
                    self.site_info['categories'][category] = []

                self.site_info['categories'][category].append(post)

            for t in tags:
                if t not in self.site_info['tags']:
                    self.site_info['tags'][t] = []

                self.site_info['tags'][t].append(post)

        posts = [v for k, v in self.tree['posts'].items() if not v.unpublished()]
        posts.sort(key=lambda p: p.metadata['date'])
        for i, p in enumerate(posts):
            previous = posts[i - 1] if i > 0 else None
            next_ = posts[i + 1] if i + 1 < len(posts) else None

            p.metadata['previous'] = previous
            p.metadata['next'] = next_

            pdate = p.metadata['date']
            p.url = '/%s/%i/%.2i/%.2i/%s' % (
                p.metadata['category'].lower(), pdate.year, pdate.month, pdate.day, os.path.basename(p.dest)
            )

        self.site_info['posts'] = posts
        self.traverse_tree(Page, process_page)

        for k in self.site_info['categories']:
            self.site_info['categories'][k].sort(key=lambda p: p.metadata['date'])

        for k in self.site_info['tags']:
            self.site_info['tags'][k].sort(key=lambda p: p.metadata['date'])


class File:
    """Doesn't load files into memory - just copies the file over if needed."""

    def __init__(self, path, builder):
        self.path = path
        self.builder = builder
        basename = os.path.basename(path)
        self.file_type = basename.split('.')[-1]
        self.url = '/' + self.path

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self.path)

    def __eq__(self, other):
        return super().__eq__(other) and self.file_type == other.file_type and self.dest == other.dest

    @property
    def dest(self):
        return self.builder.build_dir + self.url

    def build(self):
        os.makedirs(os.path.dirname(self.dest), exist_ok=True)
        copyfile(self.path, self.dest)

    @staticmethod
    def file_age(f):
        return datetime.fromtimestamp(os.stat(f).st_mtime)

    def should_build(self):
        return self.path in self.builder.force_build_files or \
            self.builder.always_build or \
            not os.path.isfile(self.dest) or \
            self.file_age(self.path) > self.file_age(self.dest)


class Page(File):
    def __init__(self, path, builder):
        self.metadata = {}
        super().__init__(path, builder)
        self.content = self._load_content()
        self.url = self.metadata.get('url', self.url)
        if 'url' in self.metadata:
            self.url = self.metadata['url']

    @property
    def dest(self):
        # ext is always .html, even if md file or self.url is set
        return os.path.splitext(super().dest)[0] + '.html'

    def _load_content(self):
        with open(self.path) as f:
            content = f.read()

        if self.file_type == 'md':
            content = self.builder.md_converter.convert(content)
            self.metadata = self.builder.md_converter.front_matter

            if 'date' in self.metadata:
                # parsing to a datetime lets us, e.g, sort pages by date at build time
                post_date = self.metadata['date']
                if isinstance(post_date, datetime):
                    pass
                elif isinstance(post_date, date):
                    self.metadata['date'] = datetime(post_date.year, post_date.month, post_date.day)
                elif isinstance(post_date, str):
                    try:
                        self.metadata['date'] = datetime.strptime(post_date, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        self.metadata['date'] = datetime.strptime(post_date, '%Y-%m-%d')
                else:
                    raise TypeError('Unexpected type for date %s: %s' % (post_date, post_date.__class__))

                # for convenience - reference with {{ page.metadata.human_readable_date }}
                self.metadata['human_readable_date'] = self.metadata['date'].strftime('%-d %b %Y')

            # I can't use normal template inheritance because then Jinja syntax won't work inside MD templates
            content = "{%% extends '%s' %%}{%% block post_content %%}%s{%% endblock %%}" % (
                self.metadata.get('extends', 'base.html'), content
            )

        return content

    def build(self):
        logger.info('Building %s' % self)
        os.makedirs(os.path.dirname(self.dest), exist_ok=True)
        template = self.builder.jinja_env.from_string(self.content)
        with open(self.dest, 'w') as fh:
            fh.write(template.render(site=self.builder.site_info, page=self, post_content=self.content))

        self.builder.md_converter.reset()

    def should_build(self):
        if self.unpublished():
            return False

        return super().should_build()

    def unpublished(self):
        return not self.metadata.get('publish', True)


def main():
    a = argparse.ArgumentParser()
    a.add_argument('-r', '--root', default='.', help='Project root')
    a.add_argument('-b', '--build_dir', default='build', help='Build the site here, or run a dev server here with -s')
    a.add_argument('-f', '--force', nargs='*', help='Force rebuild specified pages, or all')
    a.add_argument('-s', '--server', action='store_true', help='Set up a dev server for testing')
    a.add_argument('-l', '--log_level', default='info', help='Set log level. Can be given in lower case.')
    a.add_argument('-v', '--version', action='store_true', help='Show version')
    args = a.parse_args()

    log_level = logging.getLevelName(args.log_level.upper())
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(log_level)
    logger.addHandler(handler)
    logger.setLevel(log_level)
    logger.addHandler(handler)

    if args.version:
        print(__version__)
        sys.exit(0)
    elif args.server:
        os.chdir(args.build_dir)
        dev_server.DevServer.run()
    else:
        os.chdir(args.root)

        builder = Pykyller(args.build_dir, force_build=args.force)

        builder.discover_pages()
        builder.process()
        builder.build()


if __name__ == '__main__':
    main()

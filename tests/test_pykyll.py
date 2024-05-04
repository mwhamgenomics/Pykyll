import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import pykyll


class TestPykyller(unittest.TestCase):
    def setUp(self):
        self.builder = pykyll.Pykyller()

    @patch('os.walk')
    @patch.object(pykyll, 'File', new=lambda path, builder: path)
    @patch.object(pykyll, 'Page', new=lambda path, builder: path)
    def test_discover_pages(self, patched_walk):
        patched_walk.return_value = (
            ('.', ['.hidden', 'this', 'empty_dir'], ['top_level.md']),
            ('./.hidden', ['should_not_be_picked_up'], ['should_not_be_picked_up']),
            ('./.hidden/should_not_be_picked_up', [], ['should_not_be_picked_up']),
            ('./this/_private', ['should_not_be_picked_up'], ['should_not_be_picked_up']),
            ('./this/_private/should_not_be_picked_up', [], ['should_not_be_picked_up']),
            ('./this', ['that'], ['that.txt', 'other.md', '.should_not_be_picked_up', '_should_not_be_picked_up']),
            ('./this/that', [], ['other.html']),
            ('./empty_dir', [], [])
        )

        self.builder.discover_pages()
        self.assertDictEqual(
            self.builder.tree,
            {
                'top_level.md': 'top_level.md',
                'this': {
                    'that': {
                        'other.html': 'this/that/other.html'
                    },
                    'that.txt': 'this/that.txt',
                    'other.md': 'this/other.md'
                }
            }
        )

    @patch.object(pykyll.File, 'build')
    def test_build(self, patched_file_build):
        self.builder.tree = {
            'top_level.txt': pykyll.File('top_level.txt', self.builder),
            'this': {
                'that': {
                    'other.txt': pykyll.File('this/that/other.txt', self.builder)
                }
            }
        }
        self.builder.build()
        self.assertEqual(patched_file_build.call_count, 2)


class TestFile(unittest.TestCase):
    def setUp(self):
        self.builder = pykyll.Pykyller()
        self.file = pykyll.File('this/that.txt', self.builder)
        self.top_level_file = pykyll.File('this.txt', self.builder)

    def test_fields(self):
        self.assertEqual(self.file.file_type, 'txt')
        self.assertEqual(self.file.dest, 'build/this/that.txt')
        self.assertEqual(self.top_level_file.dest, 'build/this.txt')

    @patch('os.makedirs')
    @patch('pykyll.copyfile')
    def test_build(self, patched_copyfile, patched_makedirs):
        self.file.build()

        patched_makedirs.assert_called_with('build/this', exist_ok=True)

        patched_copyfile.assert_called_with('this/that.txt', 'build/this/that.txt')
        patched_copyfile.reset_mock()

    @patch('os.stat', return_value=Mock(st_mtime=1585866692))
    def test_file_age(self, patched_stat):
        self.assertEqual(self.file.file_age('this.txt'), datetime(2020, 4, 2, 23, 31, 32))
        patched_stat.assert_called_with('this.txt')

    def test_should_build(self):
        older = datetime(2020, 4, 1, 12)
        newer = datetime(2020, 4, 1, 17)

        self.builder.always_build = True
        self.assertTrue(self.file.should_build())

        self.builder.always_build = False
        with patch('os.path.isfile', return_value=False):
            self.assertTrue(self.file.should_build())

        with patch('os.path.isfile', return_value=True):
            with patch.object(pykyll.File, 'file_age', side_effect=(newer, older)):
                self.assertTrue(self.file.should_build())

            with patch.object(pykyll.File, 'file_age', side_effect=(older, older)):
                self.assertFalse(self.file.should_build())


class TestPage(TestFile):
    def test_fields(self):
        self.builder = pykyll.Pykyller()
        with patch.object(pykyll.Page, '_load_content', return_value='some content'):
            md_file = pykyll.Page('this/that.md', self.builder)
            self.assertEqual(md_file.dest, 'build/this/that.html')

    @patch.object(pykyll.Pykyller, 'md_converter', new=Mock(convert=lambda content: content, front_matter={'date': '2020-04-04 12:00:00'}))
    def test_load_content(self):
        with patch('builtins.open', return_value=MagicMock(__enter__=Mock(return_value=Mock(read=Mock(return_value='some content'))))):
            html_file = pykyll.Page('this/this.html', self.builder)
            md_file = pykyll.Page('this/that.md', self.builder)

        self.assertEqual(html_file.content, 'some content')
        self.assertEqual(md_file.content, "{% extends 'base.html' %}{% block post_content %}some content{% endblock %}")
        self.assertDictEqual(
            md_file.metadata,
            {'date': datetime(2020, 4, 4, 12), 'human_readable_date': '4 Apr 2020'}
        )

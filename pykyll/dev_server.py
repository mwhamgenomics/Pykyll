import os
import http.server
import urllib.parse
from http import HTTPStatus


class DevServer(http.server.SimpleHTTPRequestHandler):
    @classmethod
    def run(cls, port=5000):
        """Serve from the current working directory."""
        http.server.test(cls, port=port)

    def send_head(self):
        """
        Mostly identical to send_head from SimpleHTTPRequestHandler in the standard library, but with
        Jekyll/GitHub-style aliasing:

        GET /this.html -> /this.html
        GET /this      -> /this.html
        GET /this/     -> /this/index.html
        """
        path = self.translate_path(self.path)
        f = None

        # Next few lines are the important bit. Handle file requests normally, and try looking for implicit .html
        # suffixes. It's buried in the middle of the function, so I have to include the entire thing.
        if os.path.isfile(path):
            pass

        elif not path.endswith('.html') and os.path.isfile(path + '.html'):
            path += '.html'

        elif os.path.isdir(path):
            # The rest of the function from here is as it appears in the stdlib.

            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (parts[0], parts[1], parts[2] + '/',
                             parts[3], parts[4])
                new_url = urllib.parse.urlunsplit(new_parts)
                self.send_header("Location", new_url)
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)

        ctype = self.guess_type(path)
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None
        try:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", ctype)
            fs = os.fstat(f.fileno())
            self.send_header("Content-Length", str(fs[6]))
            self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
            self.end_headers()
            return f
        except:
            f.close()
            raise

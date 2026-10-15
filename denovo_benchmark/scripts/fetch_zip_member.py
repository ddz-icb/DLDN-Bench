"""
Download a single file from a (large) remote zip archive using HTTP range requests, without downloading the whole
archive. The CRC of the file is verified by zipfile while extracting.

Usage:
    python fetch_zip_member.py URL member_name output_file
"""
import io
import shutil
import sys
import urllib.request
import zipfile


class HttpFile(io.RawIOBase):
    """Seekable read-only file object backed by HTTP range requests."""

    def __init__(self, url):
        self.url, self.pos = url, 0
        _, content_range = self._get(0, 0)
        self.size = int(content_range.split('/')[1])

    def _get(self, start, end):
        request = urllib.request.Request(self.url, headers={'Range': f'bytes={start}-{end}'})
        with urllib.request.urlopen(request, timeout=300) as response:
            return response.read(), response.headers.get('Content-Range')

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        return self.pos

    def readinto(self, buffer):
        n = min(len(buffer), self.size - self.pos)
        if n <= 0:
            return 0
        data, _ = self._get(self.pos, self.pos + n - 1)
        buffer[:len(data)] = data
        self.pos += len(data)
        return len(data)


if __name__ == '__main__':
    url, member, output = sys.argv[1:4]
    archive = zipfile.ZipFile(io.BufferedReader(HttpFile(url), buffer_size=8 << 20))
    with archive.open(member) as src, open(output, 'wb') as dst:
        shutil.copyfileobj(src, dst, 8 << 20)
    print(f'Extracted {member} to {output}')

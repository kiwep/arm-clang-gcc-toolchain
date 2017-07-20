import os
import sys
import shutil
import platform
import argparse
import urllib.request
import zipfile
import tarfile

def which(cmd, mode=os.F_OK | os.X_OK, path=None, win_defaults=None):
    """searches an executable on the system path
    cmd: the name of the executable
    mode: file mode
    path: use the path for search instead of the system path
    win_defaults: additional paths to search on windows (for program default locations not on path)
    """
    def _access_check(fname, mode):
        return os.path.exists(fname) and os.access(fname, mode) and not os.path.isdir(fname)

    if _access_check(cmd, mode):
        return cmd

    path = (path or os.environ.get('PATH', os.defpath)).split(os.pathsep)

    if platform.system() == 'Windows':
        if win_defaults is not None:
            path.extend(win_defaults)
        if os.curdir not in path:
            path.insert(0, os.curdir)

        pathext = os.environ.get('PATHEXT', '').split(os.pathsep)
        matches = [cmd for ext in pathext if cmd.lower().endswith(ext.lower())]
        files = [cmd] if matches else [cmd + ext.lower() for ext in pathext]

    else:
        files = [cmd]

    seen = set()
    for dirname in path:
        dirname = os.path.normcase(dirname)
        if dirname not in seen:
            seen.add(dirname)
            for thefile in files:
                name = os.path.join(dirname, thefile)
                if _access_check(name, mode):
                    return name
    return None


def http_parse_links(url, pattern):
    """loads a html page and searches all links starting with pattern
    url: the page url
    pattern: the matching string
    """
    res = []
    socket = urllib.request.urlopen(url)
    while True:
        line = socket.readline().decode('utf-8')
        if not line:
            break
        pos = line.find(pattern)
        if pos > -1:
            pos1 = line.rfind('"', 0, pos) + 1
            pos2 = line.find('"', pos)
            res.append(line[pos1:pos2])

    socket.close()
    return res


def download_file(url, fname):
    """downloads a file and saves it to disk
    url: the file url (encoded)
    fname: file name
    """
    socket = urllib.request.urlopen(url)
    with open(fname, "wb") as fdesc:
        while True:
            buff = socket.read(65536)
            if not buff:
                break
            fdesc.write(buff)
    socket.close()


def endswithany(str, items):
    for istr in items:
        if str.endswith(istr):
            return True
    return False


def extract_file(fname, path="."):
    """extracts all content from a zip or tar file
    fname: file name on disk
    path: the save path (defaults to current directory)
    """
    if fname.endswith(".zip"):
        with zipfile.ZipFile(fname, "r") as zfile:
            zfile.extractall(path)
    elif endswithany(fname, ['.tar', '.tar.bz2', '.tar.gz', '.tar.xz']):
        with tarfile.open(fname, "r") as tfile:
            tfile.extractall(path)


def match_first(items, pattern):
    def f(item):
        return item.find(pattern) > -1
    res = list(filter(f, items))
    return res[0] if len(res) > 0 else None


def movefiles(src, dest):
    for fname in os.listdir(src):
        shutil.move(os.path.join(src, fname), dest)


def rmdircontent(dirpath):
    for filename in os.listdir(dirpath):
        filepath = os.path.join(dirpath, filename)
        try:
            shutil.rmtree(filepath)
        except OSError:
            os.remove(filepath)

def set_default_subparser(self, name, args=None):
    """default subparser selection. Call after setup, just before parse_args()
    name: is the name of the subparser to call by default
    args: if set is the argument list handed to parse_args()

    , tested with 2.7, 3.2, 3.3, 3.4
    it works with 2.6 assuming argparse is installed
    """
    subparser_found = False
    for arg in sys.argv[1:]:
        if arg in ['-h', '--help']:  # global help if no subparser
            break
    else:
        for x in self._subparsers._actions:
            if not isinstance(x, argparse._SubParsersAction):
                continue
            for sp_name in x._name_parser_map.keys():
                if sp_name in sys.argv[1:]:
                    subparser_found = True
        if not subparser_found:
            if args is None:
                sys.argv.append(name)
            else:
                args.append(name)

argparse.ArgumentParser.set_default_subparser = set_default_subparser

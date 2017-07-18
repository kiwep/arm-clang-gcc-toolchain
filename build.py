#!/usr/bin/env python
"""
build.py
Downloads, configures and builds a cross-platform ARM compiler toolchain
"""
import platform
import os
import sys
import subprocess
import urllib2
import zipfile
import tarfile

import sources

ROOTDIR = os.getcwd()
SRCDIR = "src"
BUILDDIR = "build"
LLVMDIR = "llvm"
CLANGROOT = os.path.join(LLVMDIR, "tools")
CLANGDIR = "clang"

OS = platform.system()
EXT = ""

if OS == "Windows":
    EXT = ".exe"

def which(cmd, mode=os.F_OK | os.X_OK, path=None, win_defaults=None):
    """Backported from python 3.3"""

    def _access_check(fname, mode):
        return os.path.exists(fname) and os.access(fname, mode) and not os.path.isdir(fname)

    if _access_check(cmd, mode):
        return cmd

    path = (path or os.environ.get("PATH", os.defpath)).split(os.pathsep)

    if OS == "Windows":
        if win_defaults is not None:
            path.extend(win_defaults)
        if os.curdir not in path:
            path.insert(0, os.curdir)

        pathext = os.environ.get("PATHEXT", "").split(os.pathsep)
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

def missing_tool(name):
    """Report missing tool and quit"""
    print "Error: the required tool " + name + " is missing!"
    sys.exit(1)

def load_http_links(url, pattern):
    """Parses a html page for links matching pattern"""
    res = []
    socket = urllib2.urlopen(url)
    while True:
        line = socket.readline()
        if not line:
            break
        pos1 = line.find(pattern)
        if pos1 > -1:
            pos2 = line.find('"', pos1)
            res.append(line[pos1:pos2])

    socket.close()
    return res

def download_file(url, fname):
    """Downloads a file"""
    socket = urllib2.urlopen(url)
    with open(fname, "wb") as fdesc:
        while True:
            buff = socket.read(65536)
            if not buff:
                break
            fdesc.write(buff)
    socket.close()

def unpack_file(fname, path="."):
    """Unpacks a zip or tar file"""
    if fname.endswith(".zip"):
        with zipfile.ZipFile(fname, "r") as zfile:
            zfile.extractall(path)
    elif fname.endswith(".tar") or fname.endswith(".tar.bz2") or fname.endswith(".tar.gz"):
        with tarfile.open(fname, "r") as tfile:
            tfile.extractall(path)

SVN = which("svn", win_defaults=[
    "c:\\program files\\tortoisesvn\\bin",
    "c:\\program files (x86)\\tortoisesvn\\bin",
    "c:\\program files (x86)\\subversion\\bin"
])

if SVN is None:
    missing_tool("Subversion")

CMAKE = which("cmake", win_defaults=[
    "c:\\program files\\cmake\\bin"
])

if CMAKE is None:
    missing_tool("CMake")

CALLENV = dict(os.environ)
CLANG = which("clang")
if CLANG is not None:
    CALLENV = dict(os.environ, CC="clang", CXX="clang++")

def run():
    """The main processing"""

    #
    # Sources
    #
    if os.path.isdir(SRCDIR) is False:
        os.mkdir(SRCDIR)
    os.chdir(SRCDIR)

    if os.path.isdir(LLVMDIR) is False:
        print "Checking out LLVM source (this will take a while)..."
        exit_code = subprocess.call([SVN, "co", "-q", sources.svn["llvm"], LLVMDIR])
        if exit_code != 0:
            sys.exit(exit_code)

    if os.path.isdir(os.path.join(CLANGROOT, CLANGDIR)) is False:
        print "Checking out Clang source (this will take a while)..."
        os.chdir(CLANGROOT)
        exit_code = subprocess.call([SVN, "co", "-q", sources.svn["clang"], CLANGDIR])
        if exit_code != 0:
            sys.exit(exit_code)

    armgcc_suffix = {
        "Windows": "-win32.zip",
        "Linux": "-linux.tar.bz2",
        "Darwin": "-mac.tar.bz2"
    }[OS]

    armgcc_dl_link = sources.arm["base"]
    for link in load_http_links(sources.arm["base"] + sources.arm["dlpage"], sources.arm["link"]):
        if armgcc_suffix in link:
            armgcc_dl_link += link
            break
    armgcc_dl_filename = armgcc_dl_link.split("?")[0].split("/")[-1]
    armgcc_dl_link = armgcc_dl_link.replace(" ", "%20")
    armgcc_dir = armgcc_dl_filename.split(armgcc_suffix)[0]

    if os.path.isdir(armgcc_dir) is False:
        if os.path.isfile(armgcc_dl_filename) is False:
            print "Downloading " + armgcc_dl_filename + "..."
            download_file(armgcc_dl_link, armgcc_dl_filename)
        print "Unpacking " + armgcc_dl_filename + "..."
        tpath = "."
        if armgcc_dl_filename.endswith(".zip"):
            tpath = armgcc_dir
        unpack_file(armgcc_dl_filename, path=tpath)

    os.chdir(ROOTDIR)

    #
    # Configure and build
    #

    if os.path.isdir(BUILDDIR) is False:
        os.mkdir(BUILDDIR)
    os.chdir(BUILDDIR)

    if os.path.isdir(LLVMDIR) is False:
        os.mkdir(LLVMDIR)
    os.chdir(LLVMDIR)

    cm_gen = "Unix Makefiles"
    if OS == "Windows":
        cm_gen = "Visual Studio 14 2015 Win64"

    args = [
        CMAKE,
        "-Wno-dev",
        '-G', cm_gen,
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_CROSSCOMPILING=True",
        "-DLLVM_ENABLE_PIC=False",
        "-DLLVM_TARGETS_TO_BUILD=X86;ARM;AArch64",
        "-DLLVM_DEFAULT_TARGET_TRIPLE=arm-none-eabi"
    ]

    if OS == "Windows":
        args.append("-Thost=x64")

    if CLANG is not None:
        args.append('-DCMAKE_CXX_FLAGS=-std=c++11 -stdlib=libc++')

    args.append(os.path.join("..", "..", SRCDIR, LLVMDIR))

    print "Configuring LLVM+Clang..."
    exit_code = subprocess.call(args, env=CALLENV)
    if exit_code != 0:
        sys.exit(exit_code)

    print "Building LLVM+Clang..."
    if OS == "Windows":
        exit_code = subprocess.call([
            "MSBuild",
            "LLVM.sln",
            "/t:Build",
            "/p:Configuration=Release",
            "/m"
        ], env=CALLENV)
    else:
        exit_code = subprocess.call(["make"])
    if exit_code != 0:
        sys.exit(exit_code)


#
run()

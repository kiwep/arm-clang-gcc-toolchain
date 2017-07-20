"""
Build script
"""
import util
import defs

import os
import sys
import platform

PYVER = platform.python_version_tuple()
if int(PYVER[0]) < 3 or int(PYVER[1]) < 5:
    print('Error: This script requires Python 3.5 or later!')
    sys.exit(1)

import shutil
import argparse
import subprocess
from distutils.dir_util import copy_tree

IS_WIN = platform.system() == 'Windows'

ROOT_DIR = os.getcwd()
os.chdir(ROOT_DIR)

WORK_DIR = 'work'
SRC_DIR = os.path.join(WORK_DIR, 'src')
DL_DIR = os.path.join(WORK_DIR, 'dl')
BUILD_DIR = os.path.join(WORK_DIR, 'build')

DIST_DIR = os.path.join('dist', 'arm-none-eabi-llvm-%s' % sys.platform)
TRIPLE = 'arm-none-eabi'

ARMGCC = {}
LLVM = {}

CMAKE = util.which('cmake', win_defaults=defs.defpath['cmake'])
CALLENV = dict(os.environ)
CLANG = util.which('clang')
if CLANG is not None:
    CALLENV = dict(os.environ, CC='clang', CXX='clang++')

#

def missing_tool(name):
    print('Error: The %s utility is required but missing!')
    print('To install this utility on your system check the tools documentation.')
    sys.exit(1)

#

def clean(args=None):
    print('Cleaning...')
    if os.path.isdir(WORK_DIR):
        shutil.rmtree(WORK_DIR)
    if os.path.isdir(DIST_DIR):
        shutil.rmtree(DIST_DIR)

#

def prepare_dirs():
    if os.path.isdir(SRC_DIR) is False:
        os.makedirs(SRC_DIR)
    if os.path.isdir(DIST_DIR) is False:
        os.mkdir(DIST_DIR)

#

def download_arm_gcc():
    armgcc_link_suffix = {
        'Windows': '-win32.zip',
        'Linux': '-linux.tar.bz2',
        'Darwin': '-mac.tar.bz2'
    }[platform.system()]

    print('Fetching GNU ARM Embedded Toolchain releases...')
    armgcc_dl_link = defs.arm['base']
    for link in util.http_parse_links(defs.arm['base'] + defs.arm['dlpage'], defs.arm['link_pattern']):
        if armgcc_link_suffix in link:
            armgcc_dl_link += link
            break

    armgcc_filename = armgcc_dl_link.split('?')[0].split('/')[-1]
    armgcc_dl_link = armgcc_dl_link.replace(' ', '%20')
    armgcc_dirname = armgcc_filename.split(armgcc_link_suffix)[0]

    if os.path.isfile(armgcc_filename) is False:
        print('> Downloading "%s"... ' % armgcc_filename)
        util.download_file(armgcc_dl_link, armgcc_filename)
    else:
        print('> Latest archive "%s" already present' % armgcc_filename)

    ARMGCC['filename'] = armgcc_filename
    ARMGCC['dirname'] = armgcc_dirname

#

def download_llvm_archive(dl_link, filename):
    if os.path.isfile(filename) is False:
        print('> Downloading "%s"... ' % filename)
        util.download_file(dl_link, filename)
    else:
        print('> Latest archive "%s" already present' % filename)

#

def download_llvm():
    print('Fetching LLVM releases...')
    links = util.http_parse_links(defs.llvm['base'] + defs.llvm['dlpage'], defs.llvm['link_pattern'])

    llvm_dl_link = defs.llvm['base'] + util.match_first(links, 'llvm-')
    llvm_filename = llvm_dl_link.split('/')[-1]
    download_llvm_archive(llvm_dl_link, llvm_filename)
    LLVM['llvm'] = llvm_filename

    clang_dl_link = defs.llvm['base'] + util.match_first(links, 'cfe-')
    clang_filename = clang_dl_link.split('/')[-1]
    download_llvm_archive(clang_dl_link, clang_filename)
    LLVM['clang'] = clang_filename

    lld_dl_link = defs.llvm['base'] + util.match_first(links, 'lld-')
    lld_filename = lld_dl_link.split('/')[-1]
    download_llvm_archive(lld_dl_link, lld_filename)
    LLVM['lld'] = lld_filename

#
#
#

def download(args=None):
    print('Checking downloaded files...')
    if os.path.isdir(DL_DIR) is False:
        os.makedirs(DL_DIR)

    os.chdir(DL_DIR)

    # GNU ARM Embedded Toolchain
    download_arm_gcc()

    # LLVM+Clang sources
    download_llvm()

    os.chdir(ROOT_DIR)

#

def unpack(args=None):
    if args is not None and args.cmd == 'unpack':
        download()

    if os.path.isdir(SRC_DIR) is False:
        os.makedirs(SRC_DIR)
    if os.path.isdir(DIST_DIR) is False:
        os.mkdir(DIST_DIR)

    # Unpack GNU ARM Toolchain
    # os.chdir(DIST_DIR)
    # if os.path.isdir(TRIPLE) is False:
    #     print('> Extracting %s...' % ARMGCC['filename'])
    #     path = ARMGCC['dirname'] if sys.platform == 'win32' else '.'
    #     util.extract_file(os.path.join(ROOT_DIR, DL_DIR, ARMGCC['filename']), path)
    #     util.movefiles(ARMGCC['dirname'], '.')
    #     os.rmdir(ARMGCC['dirname'])

    os.chdir(os.path.join(ROOT_DIR, SRC_DIR))

    # Unpack GNU ARM Toolchain
    if os.path.isdir(ARMGCC['dirname']) is False:
        print('> Extracting %s...' % ARMGCC['filename'])
        path = ARMGCC['dirname'] if sys.platform == 'win32' else '.'
        util.extract_file(os.path.join(ROOT_DIR, DL_DIR, ARMGCC['filename']), path)

    # Copy files from GNU ARM Toolchain
    dest = os.path.join(ROOT_DIR, DIST_DIR)
    for dpath in ['include', 'lib']:
        if os.path.isdir(os.path.join(dest, TRIPLE, dpath)) is False:
            shutil.copytree(os.path.join(ARMGCC['dirname'], TRIPLE, dpath), os.path.join(dest, TRIPLE, dpath))

    if os.path.isdir(os.path.join(dest, 'lib')) is False:
        shutil.copytree(os.path.join(ARMGCC['dirname'], 'lib'), os.path.join(dest, 'lib'))

    if os.path.isdir(os.path.join(dest, 'bin')) is False:
        os.mkdir(os.path.join(dest, 'bin'))

    for bname in [
        'ar', 'as', 'gdb', 'gdb-py', 'ld', 'ld.bfd', 'nm', 'objcopy', 'objdump',
        'ranlib', 'readelf', 'size', 'strings', 'strip'
    ]:
        src = os.path.join(ARMGCC['dirname'], 'bin', '%s-%s' % (TRIPLE, bname))
        dst = os.path.join(dest, 'bin', bname)
        if os.path.isfile(dst) is False:
            shutil.copy2(src, dst)

    libdest = os.path.join(dest, TRIPLE, 'lib')
    if os.path.isfile(os.path.join(libdest, 'crtbegin.o')) is False:
        gcclib = os.path.join(dest, 'lib', 'gcc', TRIPLE)
        gcclibver = os.listdir(gcclib)[0]
        copy_tree(os.path.join(gcclib, gcclibver), libdest)

    cppincbase = os.path.join(dest, TRIPLE, 'include', 'c++')
    if os.path.isfile(os.path.join(cppincbase, 'algorithm')) is False:
        cppver = os.listdir(cppincbase)[0]
        src = os.path.join(cppincbase, cppver)
        util.movefiles(src, cppincbase)
        os.rmdir(src)

    # Unpack LLVM
    LLVM['src'] = LLVM['llvm'].split('.src.tar.xz')[0]
    if os.path.isdir(LLVM['src']) is False:
        print('> Extracting %s...' % LLVM['llvm'])
        util.extract_file(os.path.join(ROOT_DIR, DL_DIR, LLVM['llvm']))
        os.rename(LLVM['src'] + '.src', LLVM['src'])

    # Unpack Clang
    clang_tmp_dir = LLVM['clang'].split('.src.tar.xz')[0]
    clang_src_dir = os.path.join(LLVM['src'], 'tools', 'clang')
    if os.path.isdir(clang_src_dir) is False:
        print('> Extracting %s...' % LLVM['clang'])
        util.extract_file(os.path.join(ROOT_DIR, DL_DIR, LLVM['clang']))
        os.rename(clang_tmp_dir + '.src', clang_src_dir)

    # Unpack LLD
    lld_tmp_dir = LLVM['lld'].split('.src.tar.xz')[0]
    lld_src_dir = os.path.join(LLVM['src'], 'tools', 'lld')
    if os.path.isdir(lld_src_dir) is False:
        print('> Extracting %s...' % LLVM['lld'])
        util.extract_file(os.path.join(ROOT_DIR, DL_DIR, LLVM['lld']))
        os.rename(lld_tmp_dir + '.src', lld_src_dir)

    os.chdir(ROOT_DIR)

#

def configure(args=None):
    if CMAKE is None:
        missing_tool('CMake')

    if args is not None and args.cmd == 'configure':
        download()
        unpack()

    LLVM['build'] = os.path.join(BUILD_DIR, LLVM['src'])
    if os.path.isdir(LLVM['build']) is False:
        os.makedirs(LLVM['build'])

    print('Configuring sources...')

    if args is not None and args.reconfigure:
        util.rmdircontent(LLVM['build'])

    os.chdir(LLVM['build'])

    if os.path.isdir('CMakeFiles'):
        print('> LLVM is already configured')
    else:
        print('> Configuring LLVM...')
        args = [CMAKE]

        cm_gen = 'Unix Makefiles'
        if os.name == 'win32':
            cm_gen = 'Visual Studio 14 2015 Win64'
            args.append('-Thost=x64')

        install_dir = os.path.join('..', '..', '..', DIST_DIR)
        args += [
            '-Wno-dev',
            '-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_CROSSCOMPILING=True',
            '-DCMAKE_INSTALL_PREFIX=%s' % install_dir,
            '-DCMAKE_PREFIX_PATH=%s' % install_dir,
            '-DLLVM_INCLUDE_TESTS=OFF',
            '-DLLVM_INCLUDE_EXAMPLES=OFF',
            '-DCLANG_INCLUDE_DOCS=OFF',
            '-DLLVM_TARGETS_TO_BUILD=ARM',
            '-DLLVM_DEFAULT_TARGET_TRIPLE=%s' % TRIPLE
        ]

        if CLANG is not None:
            args.append('-DCMAKE_CXX_FLAGS=-std=c++11 -stdlib=libc++')

        args.append(os.path.join('..', '..', '..', SRC_DIR, LLVM['src']))

        exit_code = subprocess.call(args, env=CALLENV)
        if exit_code != 0:
            sys.exit(exit_code)

    os.chdir(ROOT_DIR)

#

def build(args):
    download(args)
    unpack(args)
    configure(args)

    os.chdir(LLVM['build'])

    print('Building LLVM...')
    if os.name == 'win32':
        exit_code = subprocess.call([
            'MSBuild',
            'LLVM.sln',
            '/t:Build',
            '/p:Configuration=Release',
            '/m'
        ], env=CALLENV)
    else:
        exit_code = subprocess.call(['make', 'install', '-j2'])

    if exit_code != 0:
        sys.exit(exit_code)

    # print('Moving LLVM into place...')
    # if os.name == 'win32':
    #     pass
    # else:
    #     exit_code = subprocess.call(['make', 'install'])

    # if exit_code != 0:
    #     sys.exit(exit_code)

    os.chdir(ROOT_DIR)

#
#
#

parser = argparse.ArgumentParser(prog='toolchain')
parser.add_argument('-c', '--clean', action='store_true', help='clean the projects before executing subcommand')
subparsers = parser.add_subparsers(title='subcommands', dest='cmd')

parser_clean = subparsers.add_parser('clean', help='remove build files')
parser_clean.set_defaults(func=clean)

parser_download = subparsers.add_parser('download', help='download the source files')
parser_download.set_defaults(func=download)

parser_unpack = subparsers.add_parser('unpack', help='unpack the source files')
parser_unpack.set_defaults(func=unpack)

parser_configure = subparsers.add_parser('configure', help='configure the build targets')
parser_configure.add_argument('-rc', '--reconfigure', action='store_true', help='clean the projects before executing subcommand')
parser_configure.set_defaults(func=configure)

parser_build = subparsers.add_parser('build', help='build the toolchain (default)')
parser_build.add_argument('-rc', '--reconfigure', action='store_true', help='clean the projects before executing subcommand')
parser_build.set_defaults(func=build)

parser.set_default_subparser('build')
args = parser.parse_args()

if args.clean is True:
    clean()

args.func(args)

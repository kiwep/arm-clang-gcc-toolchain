#!/bin/bash

#
# Working parameters and defines
#

export LLVM_TARGETS="ARM;AArch64"
export TARGET_TRIPLE="arm-none-eabi"

TARGET_ROOT="/usr/local/embedded"

PKG_BINUTILS_URL="http://ftp.gnu.org/gnu/binutils/binutils-2.24.tar.gz"
PKG_ARMTOOLS_URL="http://launchpad.net/gcc-arm-embedded/4.8/4.8-2014-q2-update/+download/gcc-arm-none-eabi-4_8-2014q2-20140609-mac.tar.bz2"
PKG_LLVM_URL="http://llvm.org/pre-releases/3.5/rc4/llvm-3.5.0rc4.src.tar.xz"
PKG_CLANG_URL="http://llvm.org/pre-releases/3.5/rc4/cfe-3.5.0rc4.src.tar.xz"
PKG_LLD_URL="http://llvm.org/pre-releases/3.5/rc4/lld-3.5.0rc4.src.tar.xz"

# ----------------------------------------

#
# Color term support
#

COLORS="0"
blue_arrow=""
green_arrow=""
norm=""

if [[ -t 1 ]]; then
  ncolors=$(tput colors)
  if [[ -n "$ncolors" && $ncolors -ge 7 ]]; then
    COLORS=1
    blue_arrow=$'\e[34;1m==> \e[39m'
    green_arrow=$'\e[32;1m==> \e[39m'
    norm=$'\e[0m'
  fi
fi

#
# Helper methods
#

function unpackToPlace {
  if [ ! -d "$2" ]; then
    local aname=$(basename "$1")
    echo $blue_arrow"Unpacking $aname..."$norm
    tar xf "$aname"
    local dname=$(find . -type d -maxdepth 1 | tail -n1)
    mv "$dname" "$2"
  fi
}

function downloadPackage {
  local bname=$(basename "$1")
  if [ ! -f "$bname" ]; then
    echo $blue_arrow"Downloading $bname..."$norm
    curl -#OL "$1"
  fi
}

function cleandir {
  if [ -d "$1" ]; then
    rm -rf "$1"
    mkdir -p "$1"
  fi
}

function check_brew {
  BREW=$(which brew)
  if [[ $BREW = "" ]]; then
    echo "This summon script requires the CMake and Ninja helper tools to compile the toolchain."
    echo "The easiest way to obtain these is via the free Brew package manager from http://brew.sh"
    echo "Please install Brew and run this script again."
    echo ""
    exit 1
  fi
}

function brew_install_cmake {
  check_brew
  echo $blue_arrow"Installing CMake..."$norm
  $BREW install cmake || exit 1
  CMAKE=$(which cmake)
  [[ $CMAKE ]] || exit 1
}

function brew_install_ninja {
  check_brew
  echo $blue_arrow"Installing Ninja..."$norm
  $BREW install ninja || exit 1
  NINJA=$(which ninja)
  [[ $NINJA ]] || exit 1
}

# ----------------------------------------

DTMP=".tmp"
ORIG_ROOT=$(pwd)
pushd $(dirname "$0") > /dev/null
SCRIPT_ROOT=$(pwd)
popd > /dev/null

# ----------------------------------------

#
# Check OS type and required tools
#

OS=""
case "$OSTYPE" in

  # OS X
  darwin*)
    OS="mac"

    # Cmake
    CMAKE=$(which cmake)
    [[ $CMAKE ]] || brew_install_cmake

    # Ninja
    NINJA=$(which ninja)
    [[ $NINJA ]] || brew_install_ninja

    [[ $LIBCXX_TRIPLE ]] || export LIBCXX_TRIPLE=-apple-

    ;;

  # TODO: GNU Linux
  # linux-gnu)
  #   OS="linux"
  #   ;;

  *)
    echo "Sorry this script does not yet support your operating system"
    exit 1
esac

#
# Checking parameters
#

PARAM=""
if [[ $# > 0 ]]; then
  case $1 in
    --clean|--rebuild)
      PARAM=$1
      shift
    ;;
  esac
fi

if [[ $# > 0 ]]; then
  TARGET_ROOT="$1"
fi

echo $blue_arrow"Summon target directory is $TARGET_ROOT"$norm

#
# Handling special parameters
#

if [ -d "$TARGET_ROOT/$DTMP" ]; then
  if [[ $PARAM = "--clean" ]]; then
    echo $blue_arrow"Cleaning intermediate files in $TARGET_ROOT..."$norm
    cleandir "$TARGET_ROOT/$DTMP"
  fi

  if [[ $PARAM = "--rebuild" ]]; then
    echo $blue_arrow"Rebuild requested"$norm
    cleandir "$TARGET_ROOT/$DTMP/build/binutils"
    cleandir "$TARGET_ROOT/$DTMP/build/llvm"
  fi
fi

#
# Make target directory structure
#

mkdir -p "$TARGET_ROOT" || exit 1
cd "$TARGET_ROOT"
mkdir -p $DTMP/build/{llvm,binutils} $DTMP/{orig,src} || exit 1

#
# Download sources
#

cd $DTMP/orig

downloadPackage "$PKG_BINUTILS_URL"
downloadPackage "$PKG_ARMTOOLS_URL"
downloadPackage "$PKG_LLVM_URL"
downloadPackage "$PKG_CLANG_URL"
downloadPackage "$PKG_LLD_URL"

unpackToPlace "$PKG_BINUTILS_URL" ../src/binutils
unpackToPlace "$PKG_ARMTOOLS_URL" ../src/$TARGET_TRIPLE
unpackToPlace "$PKG_LLVM_URL" ../src/llvm
unpackToPlace "$PKG_CLANG_URL" ../src/llvm/tools/clang
unpackToPlace "$PKG_LLD_URL" ../src/llvm/tools/lld

cd "$TARGET_ROOT"

#
# Configure binutils
#

if [ ! -f $DTMP/build/binutils/.config.succeeded ]; then
  echo $green_arrow"Configuring binutils..."$norm
  cd $DTMP/build/binutils
  ../../src/binutils/configure \
  --prefix=$TARGET_ROOT \
  --target=$TARGET_TRIPLE \
  --program-prefix=$TARGET_TRIPLE- \
  --with-pic \
  --enable-gold=no \
  --enable-plugins \
  --enable-ld \
  --enable-interworks \
  --enable-multilib \
  --enable-nlsi=no \
  --enable-libssp=no \
  --enable-lto \
  --enable-werror=no \
  || exit 1
  touch .config.succeeded
  cd "$TARGET_ROOT"
fi

#
# Building binutils
#

if [ ! -f $DTMP/build/binutils/.build.succeeded ]; then
  echo $green_arrow"Building binutils..."$norm
  cd $DTMP/build/binutils
  make -j 4 -l .75 \
  || exit 1
  touch .build.succeeded
  cd "$TARGET_ROOT"
fi

#
# Installing binutils
#

if [ ! -f $DTMP/build/binutils/.install.succeeded ]; then
  echo $green_arrow"Installing binutils..."$norm
  cd $DTMP/build/binutils
  make install \
  || exit 1
  touch .install.succeeded
  cd "$TARGET_ROOT"
fi

#
# Configuring LLVM
#

#  TODO: -DC_INCLUDE_DIRS="$CLANG_INC_ABS"
if [ ! -f $DTMP/build/llvm/.config.succeeded ]; then
  echo $green_arrow"Configuring llvm..."$norm
  cd $DTMP/build/llvm
  CC='clang' CXX='clang++' \
  $CMAKE \
  -Wno-dev \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CROSSCOMPILING=True \
  -DCMAKE_INSTALL_PREFIX="$TARGET_ROOT/$TARGET_TRIPLE" \
  -DCMAKE_PREFIX_PATH=$TARGET_ROOT \
  -DCMAKE_CXX_FLAGS="-std=c++11 -stdlib=libc++" \
  -DLLVM_TARGETS_TO_BUILD=$LLVM_TARGETS \
  -DLLVM_DEFAULT_TARGET_TRIPLE=$TARGET_TRIPLE \
  -DLLVM_TARGET_ARCH=host \
  -DLLVM_ENABLE_PIC=True \
  -DGCC_INSTALL_PREFIX="$TARGET_ROOT/$TARGET_TRIPLE" \
  ../../src/llvm \
  || exit 1
  touch .config.succeeded
  cd "$TARGET_ROOT"
fi

#
# Building LLVM
#

if [ ! -f $DTMP/build/llvm/.build.succeeded ]; then
  echo $green_arrow"Building llvm (this may take a while)..."$norm
  cd $DTMP/build/llvm && \
  $NINJA \
  || exit 1
  touch .build.succeeded
  cd "$TARGET_ROOT"
fi

#
# Installing LLVM
#

if [ ! -f $DTMP/build/llvm/.install.succeeded ]; then
  echo $green_arrow"Installing llvm..."$norm
  cd $DTMP/build/llvm && \
  $NINJA install \
  || exit 1
  touch .install.succeeded
  cd "$TARGET_ROOT"
fi

#
# Creating symlinks
#

if [ ! -f "bin/$TARGET_TRIPLE-clang" ]; then
  echo $green_arrow"Creating links to binaries..."$norm
  cd bin
  TARGETS="clang clang++ clang-check clang-format llc lld opt"
  for N in $TARGETS; do
    S="../$TARGET_TRIPLE/bin/$N"
    T="$TARGET_TRIPLE-$N"
    if [ ! -f "$T" ]; then
      ln -s "$S" "$T"
    fi
  done
  cd "$TARGET_ROOT"
fi

#
# Copying headers from GCC arm-none-eabi package
#

if [ ! -f "$TARGET_TRIPLE/include/_ansi.h" ]; then
  echo $green_arrow"Moving headers into place..."$norm
  cp -fr $DTMP/src/$TARGET_TRIPLE/$TARGET_TRIPLE/include/{*.h,bits,machine,rpc,sys} "$TARGET_TRIPLE/include/"
  mkdir "$TARGET_TRIPLE/include/c++"
  cp -fr $DTMP/src/$TARGET_TRIPLE/$TARGET_TRIPLE/include/c++/4.8.4/* "$TARGET_TRIPLE/include/c++/"
fi

#
# Copying libraries from GCC arm-none-eabi package
#

if [ ! -f "$TARGET_TRIPLE/lib/libc.a" ]; then
  echo $green_arrow"Moving libraries into place..."$norm
  cp -fr $DTMP/src/$TARGET_TRIPLE/$TARGET_TRIPLE/lib/* "$TARGET_TRIPLE/lib"
  cp -r $DTMP/src/$TARGET_TRIPLE/lib/gcc/$TARGET_TRIPLE/4.8.4/* "$TARGET_TRIPLE/lib"
fi

#
# Applying patched files
#

cp -fr $SCRIPT_ROOT/patches/* "$TARGET_TRIPLE/"

#
# Cleanup
#

if [ -d $DTMP ]; then
  echo $blue_arrow"Removing intermediate files..."$norm
  rm -rf $DTMP
fi

#
# Done
#

echo $blue_arrow"Done"$norm
echo ""

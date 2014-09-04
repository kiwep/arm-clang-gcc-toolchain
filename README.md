# Clang/GCC ARM Cortex-M toolchain

A hybrid toolchain for compiling ARM Cortex-M code with the LLVM Clang compiler and GCC linker.

## Supported platforms

* Mac OS X
* Linux coming soon

## The scripts requirements

The script needs the CMake and Ninja build tools, and a working clang compiler for your platform. On OS X you need Xcode and Brew. Linux support coming soon.

## Usage

1. Clone this repository
2. Run `./summon.sh` with an optional target directory argument, the default is `/usr/local/embedded`

## Project status

At this stage this is a working prototype. Use it for your own risk.
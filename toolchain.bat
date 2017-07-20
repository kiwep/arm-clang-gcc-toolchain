@echo off
call "%VS140COMNTOOLS%VsDevCmd.bat"
py scripts\build.py %*

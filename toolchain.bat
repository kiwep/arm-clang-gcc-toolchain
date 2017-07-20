@echo off

if not "%WindowsSdkDir%" == "" goto DevEnvLoaded
call "%VS140COMNTOOLS%VsDevCmd.bat"
:DevEnvLoaded

py scripts\build.py %*

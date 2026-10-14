@echo off
REM ============================================================
REM  smoke driver build - classic WDK toolchain (cl + link)
REM  No VS integration needed: explicit paths to headers/libs.
REM  Output: smoke.sys + smoke.pdb in this directory.
REM  Usage:  build.cmd   (run from this directory; any shell)
REM ============================================================
setlocal

set "VSROOT=C:\Program Files\Microsoft Visual Studio\18\Community"
set "TOOLSET=14.51.36231"
set "KITS=C:\Program Files (x86)\Windows Kits\10"
set "SDK=10.0.26100.0"

set "BIN=%VSROOT%\VC\Tools\MSVC\%TOOLSET%\bin\Hostx64\x64"
set "INC_MSVC=%VSROOT%\VC\Tools\MSVC\%TOOLSET%\include"
set "INC_KM=%KITS%\Include\%SDK%\km"
set "INC_SHARED=%KITS%\Include\%SDK%\shared"
set "INC_UCRT=%KITS%\Include\%SDK%\ucrt"

"%BIN%\cl.exe" /nologo /c /kernel /W4 /WX /Gz /Zp8 /Z7 ^
  /D _AMD64_ /D NTDDI_VERSION=0x0A00000D ^
  /I "%INC_MSVC%" /I "%INC_KM%" /I "%INC_SHARED%" /I "%INC_UCRT%" ^
  smoke.c
if errorlevel 1 goto :fail

"%BIN%\link.exe" /NOLOGO /INCREMENTAL:NO /OUT:smoke.sys ^
  /DRIVER:WDM /SUBSYSTEM:NATIVE /ENTRY:DriverEntry /NODEFAULTLIB ^
  /DEBUG /MACHINE:X64 ^
  smoke.obj "%KITS%\Lib\%SDK%\km\x64\wdm.lib"
if errorlevel 1 goto :fail

echo.
echo Built: %CD%\smoke.sys
exit /b 0

:fail
echo BUILD FAILED
exit /b 1

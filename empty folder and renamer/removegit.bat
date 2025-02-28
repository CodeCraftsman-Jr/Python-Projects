@echo off
setlocal enabledelayedexpansion

REM Define the base directory
set "BASE_DIR=C:\Users\evasa\Documents\GitHub\MyPlugins"

REM Loop through all subdirectories
for /d %%D in ("%BASE_DIR%\*") do (
    if exist "%%D\.git" (
        echo Deleting "%%D\.git"...
        rmdir /s /q "%%D\.git"
    )
)

echo All .git folders deleted.
pause

@echo off
setlocal enabledelayedexpansion

set "source=C:\Users\evasa\Documents\GitHub\MyPlugins"
set "destination=C:\Users\evasa\Documents\GitHub\Empty"
set "logfile=%destination%\log.txt"

echo ==== Empty Folder Move Log - %DATE% %TIME% ==== >> "%logfile%"
echo ==== Empty Folder Move Log - %DATE% %TIME% ====

:: Set a flag to check if any empty folder was found
set "emptyFoldersFound=0"

:: Find all directories and process them in reverse order
for /f "delims=" %%F in ('dir "%source%" /ad /s /b ^| sort /r') do (
    :: Check if the folder is empty
    dir "%%F" /b | findstr "." >nul
    if errorlevel 1 (
        echo Moving: "%%F"
        echo Moving: "%%F" >> "%logfile%"
        move "%%F" "%destination%" >> "%logfile%" 2>&1
        set "emptyFoldersFound=1"
    )
)

:: If no empty folders were found, display a message
if "%emptyFoldersFound%"=="0" (
    echo No empty folders found.
    echo No empty folders found. >> "%logfile%"
)

echo ==== Process Completed ==== >> "%logfile%"
echo ==== Process Completed ====

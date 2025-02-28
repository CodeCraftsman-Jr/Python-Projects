@echo off
setlocal enabledelayedexpansion

:: Define the base directory
set BASE_DIR=C:\Users\evasa\Documents\WP_PLUGINS

:: Check if the base directory exists
if not exist "%BASE_DIR%" (
    echo ERROR: Directory %BASE_DIR% does not exist!
    exit /b
)

:: Loop through each folder inside BASE_DIR
for /d %%F in ("%BASE_DIR%\*") do (
    echo ------------------------
    echo Processing folder: %%F
    cd /d "%%F"
    
    :: Check if it's a Git repository
    if exist ".git" (
        echo Found Git repository in %%F
        
        git status >nul 2>&1
        if %errorlevel% neq 0 (
            echo ERROR: Git repository in %%F is not accessible!
            cd /d "%BASE_DIR%"
            goto :continue
        )

        git add .
        git commit -m "Automated commit from batch script"
        git push origin main
    ) else (
        echo Skipping %%F (not a Git repository)
    )

    cd /d "%BASE_DIR%"  :: Go back to base directory

    :continue
)

echo ------------------------
echo All Git operations completed!
pause

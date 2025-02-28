# Define paths
$sourcePath = "C:\Users\evasa\Documents\GitHub\MyPlugins"
$logFilePath = "C:\Users\evasa\Documents\GitHub\MyPlugins\empty_folders_log.txt"

# Create or clear the log file
Clear-Content -Path $logFilePath -Force

# Initialize COM object for moving to Recycle Bin
$shell = New-Object -ComObject Shell.Application

# Find all empty folders
$emptyFolders = Get-ChildItem -Path $sourcePath -Directory | Where-Object { (Get-ChildItem -Path $_.FullName -Recurse | Measure-Object).Count -eq 0 }

# Check if there are empty folders
if ($emptyFolders.Count -eq 0) {
    Write-Host "No empty folders found in $sourcePath"
    Add-Content -Path $logFilePath -Value "No empty folders found at $(Get-Date)"
} else {
    # Loop through each empty folder
    foreach ($folder in $emptyFolders) {
        $message = "Moving empty folder: $($folder.FullName)"
        
        # Log to screen
        Write-Host $message
        
        # Log to file
        Add-Content -Path $logFilePath -Value "$message - $(Get-Date)"

        # Move to Recycle Bin using Shell COM object
        try {
            $folderPath = $folder.FullName
            $recycleBin = $shell.NameSpace(10) # 10 is the Recycle Bin constant
            $recycleBin.MoveHere($folderPath)
            
            # Log success
            $logMessage = "Moved to Recycle Bin: $($folder.FullName)"
            Add-Content -Path $logFilePath -Value "$logMessage - $(Get-Date)"
            Write-Host $logMessage
        } catch {
            # Log error if any
            $errorMessage = "Failed to move folder to Recycle Bin: $($folder.FullName) - Error: $_"
            Add-Content -Path $logFilePath -Value "$errorMessage - $(Get-Date)"
            Write-Host $errorMessage
        }
    }
}

# Pause to keep window open
Read-Host "Press Enter to exit"

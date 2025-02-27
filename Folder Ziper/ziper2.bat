$source = "C:\Users\MUGUNDARAM  P\OneDrive\ドキュメント\GitHub\New folder"  # Change this to your folder path
$destination = "C:\Users\MUGUNDARAM  P\OneDrive\ドキュメント\GitHub\WP_Plugins_Pub"  # Change this to where you want the zips

# Get all folders inside the source directory
$folders = Get-ChildItem -Path $source -Directory

# Use ForEach-Object -Parallel for faster execution
$folders | ForEach-Object -Parallel {
    $zipPath = "$using:destination\$($_.Name).zip"

    # Compress the folder
    Compress-Archive -Path $_.FullName -DestinationPath $zipPath -Force

    # Remove the original folder after zipping
    Remove-Item -Path $_.FullName -Recurse -Force
} -ThrottleLimit 4  # Adjust the number of parallel jobs as needed

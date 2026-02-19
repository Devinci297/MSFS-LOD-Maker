$version = "0.1.5"
$zipName = "MSFS-LOD-Maker-v$version.zip"
$exclude = @(".git", ".gitignore", ".claude", "__pycache__", "*.zip", "create_release.ps1")

Get-ChildItem -Path . -Exclude $exclude | Compress-Archive -DestinationPath $zipName -Force
Write-Host "Created release zip: $zipName"

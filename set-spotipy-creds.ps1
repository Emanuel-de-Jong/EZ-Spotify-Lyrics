Write-Host "Get them at https://developer.spotify.com/dashboard/"

$SPOTIPY_CLIENT_ID = Read-Host -Prompt "Please enter your SPOTIPY_CLIENT_ID"
$SPOTIPY_CLIENT_SECRET = Read-Host -Prompt "Please enter your SPOTIPY_CLIENT_SECRET"

$env:SPOTIPY_CLIENT_ID = $SPOTIPY_CLIENT_ID
$env:SPOTIPY_CLIENT_SECRET = $SPOTIPY_CLIENT_SECRET

# Permanent
# [System.Environment]::SetEnvironmentVariable("SPOTIPY_CLIENT_ID", $SPOTIPY_CLIENT_ID, "User")
# [System.Environment]::SetEnvironmentVariable("SPOTIPY_CLIENT_SECRET", $SPOTIPY_CLIENT_SECRET, "User")

Write-Host "Done!"
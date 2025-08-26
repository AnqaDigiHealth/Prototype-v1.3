param(
  [string]$Server = "chat.anqa.cloud",
  [string]$User = "anqa",
  [int]$Port = 8000
)
Write-Host "Opening SSH tunnel $Port -> $Server:127.0.0.1:$Port"
Write-Host "Enter password when prompted. KEEP THIS WINDOW OPEN."
ssh -N -L $Port`:127.0.0.1:$Port $User@$Server

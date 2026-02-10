#Requires -Version 5.1
$ErrorActionPreference = 'Stop'

# Get auth token
$loginBody = @{
    username = "admin"
    password = "admin"
} | ConvertTo-Json

Write-Host "Logging in..." -ForegroundColor Yellow
$tokenResponse = Invoke-WebRequest -Uri "http://localhost:12080/api/v1/auth/login" `
  -Method Post `
  -Headers @{"Content-Type" = "application/json"} `
  -Body $loginBody

Write-Host "Login successful!" -ForegroundColor Green
$parsedToken = $tokenResponse.Content | ConvertFrom-Json 
$token = $parsedToken.access_token

Write-Host "`nTesting /api/v1/compression/stats..." -ForegroundColor Cyan

# Test compression stats with the token
$response = Invoke-WebRequest -Uri "http://localhost:12080/api/v1/compression/stats" `
  -Method Get `
  -Headers @{"Authorization" = "Bearer $token"}

Write-Host "HTTP Status: $($response.StatusCode)" -ForegroundColor Green
Write-Host "`nStats Response:" -ForegroundColor Green
$response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10

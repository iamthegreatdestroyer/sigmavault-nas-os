#Requires -Version 5.1
$ErrorActionPreference = 'Continue'

# Get auth token
$loginBody = @{
    username = "admin"
    password = "admin"
} | ConvertTo-Json

Write-Host "Logging in..." -ForegroundColor Yellow
$tokenResponse = Invoke-WebRequest -Uri "http://localhost:12080/api/v1/auth/login" `
    -Method Post `
    -Headers @{"Content-Type" = "application/json" } `
    -Body $loginBody `
    -UseBasicParsing

Write-Host "Login successful!" -ForegroundColor Green
$parsedToken = $tokenResponse.Content | ConvertFrom-Json 
$token = $parsedToken.access_token

Write-Host "`nTesting /api/v1/compression/stats..." -ForegroundColor Cyan

# Test compression stats with the token (ignore HTTP errors)
$response = Invoke-WebRequest -Uri "http://localhost:12080/api/v1/compression/stats" `
    -Method Get `
    -Headers @{"Authorization" = "Bearer $token" } `
    -SkipHttpErrorCheck `
    -UseBasicParsing

Write-Host "HTTP Status: $($response.StatusCode)" -ForegroundColor $(if ($response.StatusCode -eq 200) { "Green" } else { "Red" })
Write-Host "`nResponse Content:" -ForegroundColor Green
Write-Host $response.Content
Write-Host ""
try {
    $response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
}
catch {
    Write-Host "Failed to parse JSON: $_" -ForegroundColor Yellow
}

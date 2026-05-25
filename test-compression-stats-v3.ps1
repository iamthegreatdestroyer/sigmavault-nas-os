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

# Test compression stats with the token
try {
    $response = Invoke-WebRequest -Uri "http://localhost:12080/api/v1/compression/stats" `
        -Method Get `
        -Headers @{"Authorization" = "Bearer $token" } `
        -UseBasicParsing

    Write-Host "HTTP Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "`nResponse Content:" -ForegroundColor Green
    $response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
}
catch {
    $response = $_.Exception.Response
    $content = $_.Exception.Response.GetResponseStream() | ForEach-Object { New-Object -TypeName System.IO.StreamReader -ArgumentList $_ } | Select-Object -ExpandProperty Value
    Write-Host "HTTP Error: $($response.StatusCode)" -ForegroundColor Red
    Write-Host "Error Response:" -ForegroundColor Yellow
    Write-Host $content
}

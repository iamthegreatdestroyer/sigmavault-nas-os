#!/usr/bin/env pwsh
# Test all Go API agent HTTP endpoints

# First, get authorization token
$loginUrl = "http://localhost:12080/api/v1/login"
$loginPayload = @{
    username = "admin"
    password = "SigmaVault@123"
} | ConvertTo-Json

Write-Host "Getting authorization token..." -ForegroundColor Gray
try {
    $loginResponse = Invoke-WebRequest -Uri $loginUrl `
        -Method Post `
        -Headers @{"Content-Type" = "application/json" } `
        -Body $loginPayload `
        -UseBasicParsing

    $loginData = $loginResponse.Content | ConvertFrom-Json
    $token = $loginData.access_token
    Write-Host "✅ Got token" -ForegroundColor Green
}
catch {
    Write-Host "❌ Login failed:" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type"  = "application/json"
}

$tests = @(
    @{
        name   = "List all agents"
        method = "GET"
        url    = "http://localhost:12080/api/v1/agents"
        body   = $null
    },
    @{
        name   = "Get agent by ID (agent-001)"
        method = "GET"
        url    = "http://localhost:12080/api/v1/agents/agent-001"
        body   = $null
    },
    @{
        name   = "Get agent metrics (agent-001)"
        method = "GET"
        url    = "http://localhost:12080/api/v1/agents/agent-001/metrics"
        body   = $null
    }
)

Write-Host ""
Write-Host "Testing Go API Agent Endpoints" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan

foreach ($test in $tests) {
    Write-Host ""
    Write-Host "Testing: $($test.name)" -ForegroundColor Yellow
    Write-Host "URL: $($test.url)" -ForegroundColor Gray
    
    try {
        $response = Invoke-WebRequest -Uri $test.url `
            -Method $test.method `
            -Headers $headers `
            -UseBasicParsing

        Write-Host "✅ SUCCESS - HTTP $($response.StatusCode)" -ForegroundColor Green
        
        $data = $response.Content | ConvertFrom-Json
        
        if ($data -is [array]) {
            Write-Host "  Returned array with $($data.Count) items$(if ($data.Count -gt 0) { " (first item shown)" })"
            if ($data.Count -gt 0) {
                Write-Host "  Sample:" -ForegroundColor Gray
                $data[0] | ConvertTo-Json -Depth 1 | ForEach-Object { Write-Host "    $_" }
            }
        }
        else {
            Write-Host "  Response:" -ForegroundColor Gray
            $data | Get-Member -MemberType NoteProperty | Select-Object -First 8 -ExpandProperty Name | ForEach-Object {
                Write-Host "    $($_): $($data.$_)" -ForegroundColor Gray
            }
        }
    }
    catch {
        Write-Host "❌ ERROR - $($_.Exception.Response.StatusCode)" -ForegroundColor Red
        Write-Host $_.Exception.Message
    }
}

Write-Host ""
Write-Host "Test Complete" -ForegroundColor Cyan

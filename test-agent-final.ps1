#!/usr/bin/env pwsh
# Test agent endpoints 

$baseUrl = "http://localhost:5000/api/v1/rpc"

$tests = @(
    @{
        description = "List all agents"
        method      = "agents.list"
        params      = @{}
    },
    @{
        description = "Get agent by ID (TENSOR)"
        method      = "agents.get"
        params      = @{"id" = "agent-001" }
    },
    @{
        description = "Get agent by codename (APEX)"
        method      = "agents.get_by_codename"
        params      = @{"codename" = "APEX" }
    },
    @{
        description = "Get agent metrics (agent-001)"
        method      = "agents.metrics"
        params      = @{"id" = "agent-001" }
    },
    @{
        description = "List agent tiers"
        method      = "agents.list_tiers"
        params      = @{}
    },
    @{
        description = "Get swarm status"
        method      = "agents.status"
        params      = @{}
    }
)

Write-Host "Agent Management Feature - RPC Verification" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

$passed = 0
$failed = 0

foreach ($test in $tests) {
    $payload = @{
        jsonrpc = "2.0"
        method  = $test.method
        params  = $test.params
        id      = 1
    } | ConvertTo-Json

    Write-Host "Testing: $($test.description)" -ForegroundColor Yellow
    
    try {
        $response = Invoke-WebRequest -Uri $baseUrl `
            -Method Post `
            -Headers @{"Content-Type" = "application/json" } `
            -Body $payload `
            -UseBasicParsing

        $parsed = $response.Content | ConvertFrom-Json
        
        if ($parsed.error) {
            Write-Host "  ERROR: $($parsed.error.message)" -ForegroundColor Red
            $failed++
        }
        else {
            Write-Host "  OK" -ForegroundColor Green
            $passed++
        }
    }
    catch {
        Write-Host "  FAILED: $($_.Exception.Message)" -ForegroundColor Red
        $failed++
    }
}

Write-Host ""
Write-Host "Results:" -ForegroundColor Cyan
Write-Host "Passed: $passed / $(($passed + $failed))"
Write-Host "Failed: $failed / $(($passed + $failed))"

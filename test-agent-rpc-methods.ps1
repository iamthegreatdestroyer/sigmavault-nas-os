#!/usr/bin/env pwsh
# Test all agent RPC endpoints

$baseUrl = "http://localhost:5000/api/v1/rpc"
$methods = @(
    @{
        method      = "agents.list"
        params      = @{}
        description = "List all agents"
    },
    @{
        method      = "agents.status"
        params      = @{}
        description = "Get swarm status"
    },
    @{
        method      = "agents.get"
        params      = @{"id" = "agent-001" }
        description = "Get specific agent (agent-001)"
    },
    @{
        method      = "agents.get_by_codename"
        params      = @{"codename" = "TENSOR" }
        description = "Get agent by codename (TENSOR)"
    },
    @{
        method      = "agents.metrics"
        params      = @{"id" = "agent-001" }
        description = "Get agent metrics (agent-001)"
    },
    @{
        method      = "agents.list_tiers"
        params      = @{}
        description = "List agent tiers"
    },
    @{
        method      = "agents.swarm_status"
        params      = @{}
        description = "Get swarm status (alias)"
    }
)

Write-Host "Testing Agent RPC Methods" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan

foreach ($test in $methods) {
    $payload = @{
        jsonrpc = "2.0"
        method  = $test.method
        params  = $test.params
        id      = 1
    } | ConvertTo-Json

    Write-Host ""
    Write-Host "Testing: $($test.description)" -ForegroundColor Yellow
    Write-Host "Method: $($test.method)" -ForegroundColor Gray
    
    try {
        $response = Invoke-WebRequest -Uri $baseUrl `
            -Method Post `
            -Headers @{"Content-Type" = "application/json" } `
            -Body $payload `
            -UseBasicParsing

        $parsed = $response.Content | ConvertFrom-Json
        
        if ($parsed.error) {
            Write-Host "❌ RPC Error:" -ForegroundColor Red
            Write-Host $parsed.error | ConvertTo-Json -Depth 2
        }
        else {
            Write-Host "✅ SUCCESS" -ForegroundColor Green
            
            # Show result summary
            if ($parsed.result -is [array]) {
                Write-Host "  Returned array with $($parsed.result.Count) items$(if ($parsed.result.Count -gt 0) { " (first item shown)" })"
                if ($parsed.result.Count -gt 0) {
                    Write-Host "  Sample:" -ForegroundColor Gray
                    $parsed.result[0] | ConvertTo-Json -Depth 2 | ForEach-Object { Write-Host "    $_" }
                }
            }
            elseif ($parsed.result -is [PSCustomObject]) {
                Write-Host "  Returned object:"
                # Show key properties
                $parsed.result | Get-Member -MemberType NoteProperty | Select-Object -First 5 -ExpandProperty Name | ForEach-Object {
                    Write-Host "    $($_): $($parsed.result.$_)" -ForegroundColor Gray
                }
            }
            else {
                Write-Host "  Result: $($parsed.result | ConvertTo-Json -Compress -Depth 1)"
            }
        }
    }
    catch {
        Write-Host "❌ ERROR:" -ForegroundColor Red
        Write-Host $_.Exception.Message
    }
}

Write-Host ""
Write-Host "Test Complete" -ForegroundColor Cyan

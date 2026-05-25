#!/usr/bin/env pwsh
# Test agent endpoints directly via Engine RPC (since Go API might be having startup issues)

$baseUrl = "http://localhost:5000/api/v1/rpc"

$tests = @(
    @{
        description = "List all agents"
        method      = "agents.list"
        params      = @{}
    },
    @{
        description = "Get specific agent (TENSOR - agent-001)"
        method      = "agents.get"
        params      = @{"id" = "agent-001" }
    },
    @{
        description = "Get agent by codename (APEX agent)"
        method      = "agents.get_by_codename"
        params      = @{"codename" = "APEX" }
    },
    @{
        description = "Get agent metrics (agent-001)"
        method      = "agents.metrics"
        params      = @{"id" = "agent-001" }
    },
    @{
        description = "List agent tiers (distribution)"
        method      = "agents.list_tiers"
        params      = @{}
    },
    @{
        description = "Get swarm status"
        method      = "agents.status"
        params      = @{}
    }
)

Write-Host "Agent Management Feature Verification" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
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

    Write-Host "📋 $($test.description)" -ForegroundColor Yellow
    
    try {
        $response = Invoke-WebRequest -Uri $baseUrl `
            -Method Post `
            -Headers @{"Content-Type" = "application/json" } `
            -Body $payload `
            -UseBasicParsing

        $parsed = $response.Content | ConvertFrom-Json
        
        if ($parsed.error) {
            Write-Host "  ❌ RPC Error: $($parsed.error.message)" -ForegroundColor Red
            $failed++
        }
        else {
            Write-Host "  ✅ SUCCESS" -ForegroundColor Green
            $passed++
            
            # Show brief result info
            if ($parsed.result -is [array]) {
                Write-Host "     → Returned $($parsed.result.Count) items" -ForegroundColor Gray
            }
            elseif ($parsed.result -is [PSCustomObject]) {
                $propCount = ($parsed.result | Get-Member -MemberType NoteProperty | Measure-Object).Count
                Write-Host "     → Returned object with $propCount properties" -ForegroundColor Gray
            }
        }
    }
    catch {
        Write-Host "  ❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
        $failed++
    }
    
    Write-Host ""
}

Write-Host "Summary" -ForegroundColor Cyan
Write-Host "=======" -ForegroundColor Cyan
Write-Host "✅ Passed: $passed / $(($passed + $failed))" -ForegroundColor Green
Write-Host "❌ Failed: $failed / $(($passed + $failed))" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })

if ($failed -eq 0) {
    Write-Host ""
    Write-Host "Feature 2.3.2 (Agent Management - RPC Layer): COMPLETE!" -ForegroundColor Green
}

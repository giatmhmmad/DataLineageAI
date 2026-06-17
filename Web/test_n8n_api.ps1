# Test N8N Lineage API
# Script untuk test endpoint Django dari PowerShell

$url = "http://localhost:8000/api/n8n/lineage/"

# Buat data JSON yang proper
$data = @(
    @{
        "source_table_name" = "AUDIT_TRAIL.MIN_MAX_AUDIT_LOG"
        "source_table_category" = "DATAMART"
        "schema_name" = "AUDIT_TRAIL"
        "table_name" = "MIN_MAX_AUDIT_LOG"
        "JobName" = "CDP_DMT_WHL_MCM_KLN_TRX_DLY_H1_TEST_1"
        "MatchJobName" = $false
        "PICJob" = "[8]"
        "FinalTable" = @("MCM_KLN_HK_TRX")
        "job_id" = 49
    }
)

# Convert ke JSON string
$jsonBody = $data | ConvertTo-Json -Depth 10

Write-Host "Sending request to: $url"
Write-Host "Body: $jsonBody"
Write-Host "---"

try {
    # Send POST request
    $response = Invoke-WebRequest -Uri $url `
        -Method POST `
        -ContentType "application/json" `
        -Body $jsonBody `
        -ErrorAction Stop
    
    Write-Host "Status Code: $($response.StatusCode)"
    Write-Host "Response:"
    Write-Host ($response.Content | ConvertFrom-Json | ConvertTo-Json)
    
} catch {
    Write-Host "Error: $($_.Exception.Message)"
    Write-Host "Response Body: $($_.Exception.Response.Content)"
}

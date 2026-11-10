# Local inventory entry for a real personal asset; no AWS or remote website calls.
$ErrorActionPreference = 'Stop'
$base = 'http://localhost:8080'
$assetBody = @{
    name = 'Dani WebWorks public website'
    service = 'Website'
    project = 'Dani WebWorks'
    reference = 'https://daniwebworks.com'
    environment = 'personal-business'
} | ConvertTo-Json
$asset = Invoke-RestMethod -Uri "$base/assets" -Method Post -ContentType 'application/json' -Body $assetBody
$taskBody = @{
    title = 'Review website availability and document the result'
    asset_id = $asset.id
    priority = 'medium'
} | ConvertTo-Json
$task = Invoke-RestMethod -Uri "$base/tasks" -Method Post -ContentType 'application/json' -Body $taskBody
'ASSET REGISTERED'; $asset | Format-List
'TASK CREATED'; $task | Format-List
'CURRENT ASSETS'; Invoke-RestMethod "$base/assets" | ConvertTo-Json -Depth 5
'CURRENT TASKS'; Invoke-RestMethod "$base/tasks" | ConvertTo-Json -Depth 5
Write-Host 'The task remains OPEN. Perform the review manually before marking it done.'
Write-Host "Asset ID: $($asset.id)"
Write-Host "Task ID: $($task.id)"
Write-Host 'To mark it in progress:'
Write-Host "Invoke-RestMethod -Uri '$base/tasks/$($task.id)' -Method Patch -ContentType 'application/json' -Body '{`"status`":`"in_progress`"}'"

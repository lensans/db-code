param(
    [string]$PsqlPath = 'psql',
    [string]$Database = 'genealogy_db',
    [string]$Username = 'postgres',
    [string]$DataDir = '',
    [switch]$SkipIndexes
)

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$deliveryDir = Get-ChildItem -LiteralPath $projectRoot -Directory |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'sql\schema.sql') } |
    Select-Object -First 1

if (-not $deliveryDir) {
    throw 'Cannot find a delivery directory containing sql\schema.sql.'
}

$sqlDir = Join-Path $deliveryDir.FullName 'sql'
if (-not $DataDir) {
    $DataDir = Join-Path $deliveryDir.FullName 'data\generated_full'
}

$schemaPath = Join-Path $sqlDir 'schema.sql'
$triggersPath = Join-Path $sqlDir 'triggers.sql'
$indexesPath = Join-Path $sqlDir 'indexes.sql'
$sequencePath = Join-Path $sqlDir 'sequence_sync.sql'

foreach ($required in @($schemaPath, $triggersPath, $sequencePath)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing required file: $required"
    }
}

foreach ($csvName in @('users.csv', 'genealogies.csv', 'members.csv', 'parent_child_relations.csv', 'marriages.csv')) {
    $csvPath = Join-Path $DataDir $csvName
    if (-not (Test-Path -LiteralPath $csvPath)) {
        throw "Missing CSV file: $csvPath"
    }
}

$stagingDir = Join-Path $env:TEMP 'genealogy_import_staging'
if (Test-Path -LiteralPath $stagingDir) {
    Remove-Item -LiteralPath $stagingDir -Recurse -Force
}
New-Item -ItemType Directory -Path $stagingDir | Out-Null

foreach ($csvName in @('users.csv', 'genealogies.csv', 'members.csv', 'parent_child_relations.csv', 'marriages.csv')) {
    Copy-Item -LiteralPath (Join-Path $DataDir $csvName) -Destination (Join-Path $stagingDir $csvName)
}

function Invoke-PsqlFile {
    param([string]$FilePath)
    Write-Host "Running SQL file: $FilePath"
    & $PsqlPath -U $Username -d $Database -v ON_ERROR_STOP=1 -f $FilePath
    if ($LASTEXITCODE -ne 0) {
        throw "psql failed on file: $FilePath"
    }
}

function Invoke-PsqlCommand {
    param([string]$CommandText)
    & $PsqlPath -U $Username -d $Database -v ON_ERROR_STOP=1 -c $CommandText
    if ($LASTEXITCODE -ne 0) {
        throw 'psql command failed.'
    }
}

Write-Host "Using psql: $PsqlPath"
Write-Host "Target database: $Database"
Write-Host "Delivery directory: $($deliveryDir.FullName)"
Write-Host "Data directory: $DataDir"
Write-Host "Staging directory: $stagingDir"

Invoke-PsqlFile -FilePath $schemaPath

$usersCsv = (Join-Path $stagingDir 'users.csv').Replace('\', '/')
$genealogiesCsv = (Join-Path $stagingDir 'genealogies.csv').Replace('\', '/')
$membersCsv = (Join-Path $stagingDir 'members.csv').Replace('\', '/')
$relationsCsv = (Join-Path $stagingDir 'parent_child_relations.csv').Replace('\', '/')
$marriagesCsv = (Join-Path $stagingDir 'marriages.csv').Replace('\', '/')

Invoke-PsqlCommand "COPY users(user_id, username, password_hash, created_at) FROM '$usersCsv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');"
Invoke-PsqlCommand "COPY genealogies(genealogy_id, title, surname, revision_year, owner_user_id, created_at) FROM '$genealogiesCsv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');"
Invoke-PsqlCommand "COPY members(member_id, genealogy_id, name, gender, birth_year, death_year, biography, generation_no) FROM '$membersCsv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');"
Invoke-PsqlFile -FilePath $triggersPath
Invoke-PsqlCommand "COPY parent_child_relations(genealogy_id, parent_id, child_id, parent_type) FROM '$relationsCsv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');"
Invoke-PsqlCommand "COPY marriages(genealogy_id, spouse1_id, spouse2_id, married_year) FROM '$marriagesCsv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');"
Invoke-PsqlFile -FilePath $sequencePath

if (-not $SkipIndexes) {
    Invoke-PsqlFile -FilePath $indexesPath
}

Write-Host 'Validating import summary...'
Invoke-PsqlCommand 'SELECT COUNT(*) AS genealogies FROM genealogies;'
Invoke-PsqlCommand 'SELECT COUNT(*) AS members FROM members;'
Invoke-PsqlCommand 'SELECT MAX(member_count) AS max_genealogy_members FROM (SELECT genealogy_id, COUNT(*) AS member_count FROM members GROUP BY genealogy_id) t;'
Invoke-PsqlCommand 'SELECT MIN(max_generation) AS min_generations_per_genealogy FROM (SELECT genealogy_id, MAX(generation_no) AS max_generation FROM members GROUP BY genealogy_id) t;'

Write-Host 'Import completed.'

if (Test-Path -LiteralPath $stagingDir) {
    Remove-Item -LiteralPath $stagingDir -Recurse -Force
}

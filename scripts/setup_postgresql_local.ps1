# Installe PostgreSQL portable (binaires) pour le dev local SGHL
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Tools = Join-Path $Root "backend\tools\postgres"
$PgData = Join-Path $Root "backend\tools\pgdata"
$ZipUrl = "https://get.enterprisedb.com/postgresql/postgresql-16.6-1-windows-x64-binaries.zip"
$ZipPath = Join-Path $Tools "postgresql-binaries.zip"
$PgBin = Join-Path $Tools "pgsql\bin"
$PgCtl = Join-Path $PgBin "pg_ctl.exe"
$Psql = Join-Path $PgBin "psql.exe"
$InitDb = Join-Path $PgBin "initdb.exe"
$Createdb = Join-Path $PgBin "createdb.exe"
$LogFile = Join-Path $Tools "postgres.log"
$DbUser = "sghl"
$DbPass = "sghl"
$DbName = "sghl"
$Port = "5432"

function Write-Step($msg) { Write-Host ">> $msg" -ForegroundColor Cyan }

New-Item -ItemType Directory -Force -Path $Tools | Out-Null

if (-not (Test-Path $PgCtl)) {
    Write-Step "Telechargement PostgreSQL 16 (binaires)..."
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipPath -UseBasicParsing
    Write-Step "Extraction..."
    Expand-Archive -Path $ZipPath -DestinationPath $Tools -Force
    Remove-Item $ZipPath -Force -ErrorAction SilentlyContinue
}

if (-not (Test-Path $PgCtl)) {
    throw "pg_ctl introuvable apres extraction dans $PgBin"
}

if (-not (Test-Path (Join-Path $PgData "PG_VERSION"))) {
    Write-Step "Initialisation du cluster PostgreSQL..."
    if (Test-Path $PgData) { Remove-Item -Recurse -Force $PgData }
    & $InitDb -D $PgData -U postgres -E UTF8 -A trust --locale=C
}

$running = $false
try {
    $probe = & $Psql -h localhost -p $Port -U postgres -d postgres -tAc "SELECT 1" 2>$null
    if ($probe -eq "1") { $running = $true }
} catch {}

if (-not $running) {
    Write-Step "Demarrage du serveur PostgreSQL sur le port $Port..."
    & $PgCtl -D $PgData -l $LogFile -o "-p $Port" start
    Start-Sleep -Seconds 3
}

Write-Step "Creation utilisateur et base $DbName..."
$env:PGPASSWORD = ""
& $Psql -h localhost -p $Port -U postgres -d postgres -v ON_ERROR_STOP=1 -c "DO `$`$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DbUser') THEN CREATE ROLE $DbUser LOGIN PASSWORD '$DbPass' CREATEDB; END IF; END `$`$;"
& $Psql -h localhost -p $Port -U postgres -d postgres -v ON_ERROR_STOP=1 -c "SELECT 1 FROM pg_database WHERE datname = '$DbName'" | Out-Null
$dbExists = & $Psql -h localhost -p $Port -U postgres -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$DbName'"
if ($dbExists -ne "1") {
    & $Createdb -h localhost -p $Port -U postgres -O $DbUser $DbName
}
& $Psql -h localhost -p $Port -U postgres -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DbName TO $DbUser;"

Write-Step "Verification connexion Django..."
$env:PGPASSWORD = $DbPass
$ok = & $Psql -h localhost -p $Port -U $DbUser -d $DbName -tAc "SELECT 1"
if ($ok -ne "1") { throw "Connexion $DbUser@$DbName echouee" }

Write-Step "PostgreSQL pret : $DbUser@localhost:$Port/$DbName"

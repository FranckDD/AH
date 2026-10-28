<#
.SYNOPSIS
  Copie le depot de sauvegarde restic du serveur AH2 vers le PC de l'administrateur.

.DESCRIPTION
  Recupere (scp, via la cle SSH EN LECTURE SEULE) la copie COHERENTE du depot que le serveur
  prepare lui-meme (dossier <RemotePath>/.pull : liens physiques figes par hourly.sh et nightly.sh
  sous le verrou des sauvegardes). Ce que le PC lit ne change donc pas pendant la copie, meme si un
  export horaire ou le nettoyage du dimanche tourne. Le depot est CHIFFRE : sans le mot de passe
  restic, la copie est illisible (a conserver a part, jamais dans ce dossier).

  Securite des donnees (jamais une bonne copie remplacee par une mauvaise) :
   - la copie arrive d'abord dans un dossier temporaire a cote (repo.new) ; rien d'autre n'est touche.
   - controles avant tout remplacement : structure du depot (config, keys, data, snapshots, index
     non vides) ; PULL_MANIFEST.json present et nombre de fichiers recus = nombre annonce par le
     serveur (une copie tronquee est donc detectee SANS mot de passe) ; taille au moins 70 % de la
     generation precedente (sauf -Force) ; "restic check --read-data-subset" si -ResticPasswordFile
     est fourni (fortement recommande : fichier garde AILLEURS que dans la copie).
   - seulement alors les generations tournent : repo -> repo.prev -> repo.prev2 (la plus ancienne
     est supprimee en dernier). Une copie rejetee est laissee dans repo.rejected pour examen.
   - refuse de demarrer si le disque de destination a moins de -MinFreeGB Go libres
     (2 Go par defaut), ou moins de 2 x la taille de la copie actuelle.
   - journal : <Destination>\pull_backups.log ; dernier succes : <Destination>\last_success.txt

  Codes de sortie : 0 succes, 2 disque insuffisant, 3 echec de la copie, 4 copie rejetee (controle).

.PARAMETER VpsHost
  Nom ou adresse du serveur AH2.
.PARAMETER User
  Utilisateur SSH en lecture seule (defaut : ah2backup, uid 10001 sur le serveur).
.PARAMETER KeyFile
  Cle privee SSH de ce PC (celle dont la partie publique est dans authorized_keys avec
  restrict,command="internal-sftp -R"). Defaut : $env:USERPROFILE\.ssh\ah2_backup_pull
.PARAMETER Destination
  Dossier local qui recevra repo\, repo.prev\, repo.prev2\, le journal. Defaut : D:\AH2-backups
.PARAMETER RemotePath
  Dossier du depot sur le serveur (defaut /srv/ah2-backups).
.PARAMETER RemoteSubdir
  Sous-dossier de la copie figee preparee par le serveur (defaut .pull).
.PARAMETER ResticPasswordFile
  Facultatif mais recommande : fichier contenant le mot de passe restic, pour lancer
  "restic check --read-data-subset=5%" sur la copie (restic.exe doit etre installe).
.PARAMETER MinFreeGB
  Espace libre minimal exige sur le disque de destination (defaut 2).
.PARAMETER Retries
  Nombre d'essais de la copie (defaut 3, RetryDelaySeconds entre deux).
.PARAMETER Force
  Accepte une copie nettement plus petite que la precedente (moins de 70 %) ou sans manifeste.
.PARAMETER DryRun
  Ne copie rien : verifie les prerequis (disque, cle, commandes) et affiche ce qui serait fait.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File C:\AH2\pull_backups.ps1 -VpsHost ah2.example.org

.NOTES
  PLANIFICATION TOUS LES 3 JOURS (Planificateur de taches Windows), a lancer UNE fois dans une
  fenetre PowerShell ouverte en tant que l'utilisateur qui possede la cle :

    $a = New-ScheduledTaskAction -Execute "powershell.exe" -Argument '-NoProfile -ExecutionPolicy Bypass -File "C:\AH2\pull_backups.ps1" -VpsHost ah2.example.org -Destination "D:\AH2-backups"'
    $t = New-ScheduledTaskTrigger -Daily -DaysInterval 3 -At 12:00
    $s = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun:$false -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 30)
    Register-ScheduledTask -TaskName "AH2 copie des sauvegardes (3 jours)" -Action $a -Trigger $t -Settings $s

  -StartWhenAvailable : si le PC etait eteint a 12:00, la copie part des qu'il se rallume.
  Equivalent en une ligne : schtasks /Create /SC DAILY /MO 3 /ST 12:00 /TN "AH2 copie des sauvegardes" /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\AH2\pull_backups.ps1 -VpsHost ah2.example.org"
  Prerequis : le client OpenSSH de Windows (scp.exe : Parametres > Applications >
  Fonctionnalites facultatives > Client OpenSSH).
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$VpsHost,
  [string]$User = 'ah2backup',
  [string]$KeyFile = (Join-Path $env:USERPROFILE '.ssh\ah2_backup_pull'),
  [string]$Destination = 'D:\AH2-backups',
  [string]$RemotePath = '/srv/ah2-backups',
  [string]$RemoteSubdir = '.pull',
  [int]$Port = 22,
  [string]$ResticPasswordFile = '',
  [double]$MinFreeGB = 2,
  [int]$Retries = 3,
  [int]$RetryDelaySeconds = 60,
  [switch]$Force,
  [switch]$DryRun
)

# Pas de 'Stop' global : dans Windows PowerShell 5.1, une ligne sur stderr d'un programme natif
# (scp, restic) redirigee par 2>&1 devient une erreur FATALE (NativeCommandError) et ferait
# sortir le script avec le code 1 sans journal. Les appels natifs passent par Invoke-Native
# (code de sortie lu dans $LASTEXITCODE, sortie capturee et journalisee).
$ErrorActionPreference = 'Continue'
$null = New-Item -ItemType Directory -Force -Path $Destination -ErrorAction SilentlyContinue
$Log = Join-Path $Destination 'pull_backups.log'

function Write-Log([string]$msg) {
  $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg
  Write-Host $line
  Add-Content -Path $Log -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
}

# Lance un programme natif sans jamais lever d'exception a cause de stderr : sortie standard et
# erreur capturees dans un tableau de chaines, code de sortie lu dans $LASTEXITCODE.
function Invoke-Native([string]$Exe, [string[]]$ArgList) {
  $saved = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  $code = -1
  $lines = @()
  try {
    $global:LASTEXITCODE = 0
    $lines = @(& $Exe @ArgList 2>&1 | ForEach-Object { [string]$_ })
    $code = $LASTEXITCODE
  } catch {
    $lines = @("exception : $($_.Exception.Message)")
    $code = -1
  } finally {
    $ErrorActionPreference = $saved
  }
  if ($null -eq $code) { $code = 0 }
  return [pscustomobject]@{ ExitCode = [int]$code; Output = $lines }
}

function Write-NativeOutput([string]$prefix, $result, [int]$max = 30) {
  $out = @($result.Output | Where-Object { $_ -ne '' })
  $n = 0
  foreach ($l in $out) {
    if ($n -ge $max) { Write-Log ("{0}: ... ({1} lignes de plus omises)" -f $prefix, ($out.Count - $max)); break }
    Write-Log "${prefix}: $l"
    $n++
  }
}

function Get-FreeGB([string]$path) {
  $root = [System.IO.Path]::GetPathRoot((Resolve-Path -LiteralPath $path).Path)
  return [math]::Round(([System.IO.DriveInfo]::new($root)).AvailableFreeSpace / 1GB, 2)
}

function Get-DirBytes([string]$path) {
  if (-not (Test-Path -LiteralPath $path)) { return 0 }
  $sum = (Get-ChildItem -LiteralPath $path -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
  if ($null -eq $sum) { return 0 }
  return [double]$sum
}

function Get-FileCount([string]$path) {
  return @(Get-ChildItem -LiteralPath $path -Recurse -File -Force -ErrorAction SilentlyContinue).Count
}

# Controle d'une copie : retourne les problemes (vide = valide) et les avertissements.
function Test-PulledRepo([string]$dir, [double]$prevBytes) {
  $problems = New-Object System.Collections.ArrayList
  $warnings = New-Object System.Collections.ArrayList
  if (-not (Test-Path -LiteralPath (Join-Path $dir 'config') -PathType Leaf)) { [void]$problems.Add('fichier config absent') }
  foreach ($d in 'keys', 'data', 'snapshots', 'index') {
    $p = Join-Path $dir $d
    if (-not (Test-Path -LiteralPath $p -PathType Container)) { [void]$problems.Add("dossier $d absent") }
    elseif ((Get-FileCount $p) -eq 0) { [void]$problems.Add("dossier $d vide") }
  }
  # Manifeste ecrit par le serveur : nombre de fichiers du depot au moment de la copie figee.
  $mf = Join-Path $dir 'PULL_MANIFEST.json'
  $nfiles = Get-FileCount $dir
  if (Test-Path -LiteralPath $mf -PathType Leaf) {
    try {
      $m = Get-Content -LiteralPath $mf -Raw | ConvertFrom-Json
      if ([int]$m.files -ne ($nfiles - 1)) {
        [void]$problems.Add(('copie tronquee ou modifiee pendant la lecture : le serveur annonce {0} fichiers, {1} recus' -f $m.files, ($nfiles - 1)))
      }
      $age = [int64]([DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) - [int64]$m.ts
      if ($age -gt 172800) { [void]$warnings.Add(('la copie figee du serveur date de {0} h : les exports horaires ne tournent plus ?' -f [math]::Round($age / 3600, 1))) }
    } catch {
      [void]$problems.Add('PULL_MANIFEST.json illisible')
    }
  } elseif (-not $Force) {
    [void]$problems.Add('PULL_MANIFEST.json absent (serveur sans copie figee ? -Force pour accepter)')
  } else {
    [void]$warnings.Add('PULL_MANIFEST.json absent (accepte avec -Force)')
  }
  # Taille : pas de chute brutale par rapport a la generation precedente.
  $bytes = Get-DirBytes $dir
  if ($prevBytes -gt 0 -and $bytes -lt (0.7 * $prevBytes) -and -not $Force) {
    [void]$problems.Add(('copie trop petite : {0} Mo contre {1} Mo pour la precedente (moins de 70 %, -Force pour accepter)' -f [math]::Round($bytes / 1MB, 1), [math]::Round($prevBytes / 1MB, 1)))
  }
  return [pscustomobject]@{ Problems = @($problems); Warnings = @($warnings); Files = $nfiles; Bytes = $bytes }
}

try {
  $repo = Join-Path $Destination 'repo'
  $prev = Join-Path $Destination 'repo.prev'
  $prev2 = Join-Path $Destination 'repo.prev2'
  $new = Join-Path $Destination 'repo.new'
  $rejected = Join-Path $Destination 'repo.rejected'

  # --- 1. Disque : jamais sous MinFreeGB, ni sous 2 x la taille de la copie actuelle ---------------
  $free = Get-FreeGB $Destination
  $currentBytes = Get-DirBytes $repo
  $currentGB = [math]::Round($currentBytes / 1GB, 2)
  $needGB = [math]::Max($MinFreeGB, 2 * $currentGB)
  Write-Log ('Disque {0} : {1} Go libres (minimum exige {2} Go, copie actuelle {3} Go)' -f $Destination, $free, $needGB, $currentGB)
  if ($free -lt $needGB) {
    Write-Log "REFUS: espace libre insuffisant ($free Go < $needGB Go). Liberer de la place ou changer -Destination. Rien n'a ete copie."
    exit 2
  }

  # --- 2. Prerequis -------------------------------------------------------------------------------
  if (-not (Get-Command scp -ErrorAction SilentlyContinue)) {
    Write-Log 'ERREUR: scp.exe introuvable (installer la fonctionnalite Client OpenSSH de Windows).'
    exit 3
  }
  if (-not (Test-Path -LiteralPath $KeyFile)) {
    Write-Log "ERREUR: cle SSH absente : $KeyFile"
    exit 3
  }
  $sshOpts = @('-i', $KeyFile, '-P', "$Port", '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=20')
  $remote = '{0}@{1}:{2}/{3}/*' -f $User, $VpsHost, $RemotePath.TrimEnd('/'), $RemoteSubdir.Trim('/')

  if ($DryRun) {
    Write-Log "DryRun: copierait $remote vers $new, controlerait, puis ferait tourner repo -> repo.prev -> repo.prev2. Rien n'est modifie."
    exit 0
  }

  # --- 3. Copie dans un dossier temporaire (nouvel essai si la copie echoue) ------------------------
  $started = Get-Date
  $copied = $false
  for ($try = 1; $try -le [math]::Max(1, $Retries); $try++) {
    if (Test-Path -LiteralPath $new) { Remove-Item -LiteralPath $new -Recurse -Force -ErrorAction SilentlyContinue }
    $null = New-Item -ItemType Directory -Path $new -ErrorAction SilentlyContinue
    Write-Log "Copie (essai $try/$Retries) de $remote vers $new ..."
    $r = Invoke-Native 'scp' ($sshOpts + @('-r', '-q', $remote, $new))
    Write-NativeOutput 'scp' $r
    if ($r.ExitCode -eq 0) { $copied = $true; break }
    Write-Log "scp a retourne $($r.ExitCode)."
    if ($try -lt $Retries) { Start-Sleep -Seconds $RetryDelaySeconds }
  }
  if (-not $copied) {
    Write-Log "ECHEC: la copie a echoue apres $Retries essai(s). Les copies existantes (repo, repo.prev, repo.prev2) sont intactes."
    Remove-Item -LiteralPath $new -Recurse -Force -ErrorAction SilentlyContinue
    exit 3
  }

  # --- 4. Controles AVANT tout remplacement --------------------------------------------------------
  $check = Test-PulledRepo $new $currentBytes
  Write-Log ('Copie recue : {0} fichiers, {1} Mo, en {2:N0} s' -f $check.Files, [math]::Round($check.Bytes / 1MB, 1), ((Get-Date) - $started).TotalSeconds)
  foreach ($w in $check.Warnings) { Write-Log "AVERTISSEMENT: $w" }
  $problems = New-Object System.Collections.ArrayList
  foreach ($p in $check.Problems) { [void]$problems.Add($p) }
  if ($problems.Count -eq 0) {
    if ($ResticPasswordFile) {
      if (-not (Test-Path -LiteralPath $ResticPasswordFile)) {
        [void]$problems.Add("fichier de mot de passe restic introuvable : $ResticPasswordFile")
      } elseif (-not (Get-Command restic -ErrorAction SilentlyContinue)) {
        Write-Log 'AVERTISSEMENT: restic.exe introuvable, restic check non execute (controles de structure et de manifeste seulement).'
      } else {
        Write-Log 'restic check --read-data-subset=5% sur la copie ...'
        $r = Invoke-Native 'restic' @('-r', $new, '--password-file', $ResticPasswordFile, 'check', '--no-lock', '--read-data-subset=5%')
        Write-NativeOutput 'restic' $r
        if ($r.ExitCode -ne 0) { [void]$problems.Add("restic check a echoue (code $($r.ExitCode))") }
      }
    } else {
      Write-Log 'Pas de -ResticPasswordFile : seuls la structure, le manifeste et la taille ont ete controles (restic check non execute).'
    }
  }
  if ($problems.Count -gt 0) {
    foreach ($p in $problems) { Write-Log "REJET: $p" }
    if (Test-Path -LiteralPath $rejected) { Remove-Item -LiteralPath $rejected -Recurse -Force -ErrorAction SilentlyContinue }
    Rename-Item -LiteralPath $new -NewName 'repo.rejected' -ErrorAction SilentlyContinue
    Write-Log "Les copies existantes sont intactes ; la copie rejetee est dans $rejected pour examen."
    exit 4
  }

  # --- 5. Rotation des generations (la copie est VALIDEE ; la plus ancienne part en dernier) --------
  try {
    if (Test-Path -LiteralPath $prev2) { Remove-Item -LiteralPath $prev2 -Recurse -Force -ErrorAction Stop }
    if (Test-Path -LiteralPath $prev) { Rename-Item -LiteralPath $prev -NewName 'repo.prev2' -ErrorAction Stop }
    if (Test-Path -LiteralPath $repo) { Rename-Item -LiteralPath $repo -NewName 'repo.prev' -ErrorAction Stop }
    Rename-Item -LiteralPath $new -NewName 'repo' -ErrorAction Stop
  } catch {
    Write-Log "ECHEC pendant la rotation des generations : $($_.Exception.Message)"
    # Retour arriere : remettre la derniere bonne copie a sa place si elle a ete deplacee.
    if (-not (Test-Path -LiteralPath $repo)) {
      if (Test-Path -LiteralPath $prev) { Rename-Item -LiteralPath $prev -NewName 'repo' -ErrorAction SilentlyContinue }
      if (-not (Test-Path -LiteralPath $prev) -and (Test-Path -LiteralPath $prev2)) { Rename-Item -LiteralPath $prev2 -NewName 'repo.prev' -ErrorAction SilentlyContinue }
    }
    exit 3
  }
  Set-Content -Path (Join-Path $Destination 'last_success.txt') -Value (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') -Encoding ASCII
  Write-Log 'SUCCES: copie a jour dans repo (precedentes : repo.prev, repo.prev2).'
  exit 0
} catch {
  Write-Log "ERREUR inattendue : $($_.Exception.Message)"
  exit 3
}

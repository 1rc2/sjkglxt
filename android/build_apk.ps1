# ============================================================================
#  Build script: package web UI into Android APK (local SDK, no Gradle)
#  Output : sjkglxt.apk at project root
#  Builds in a temp ASCII-only workspace (aapt2 cannot handle Chinese paths)
#  Run    : powershell -ExecutionPolicy Bypass -File build_apk.ps1
# ============================================================================
$ErrorActionPreference = 'Stop'

$sdk        = 'C:\Users\82708\AppData\Local\Android\Sdk'
$buildTools = "$sdk\build-tools\34.0.0"
$platform   = "$sdk\platforms\android-34\android.jar"
$keystore   = "$env:USERPROFILE\.android\debug.keystore"

$root = Split-Path $PSScriptRoot -Parent
$ws   = Join-Path $env:TEMP 'sjkglxt_apk_build'

# ---- 0. Prepare temp workspace ----
if (Test-Path $ws) { Remove-Item $ws -Recurse -Force }
foreach ($d in @($ws, "$ws\gen", "$ws\classes", "$ws\res\mipmap-xxxhdpi")) {
    New-Item -ItemType Directory -Path $d -Force | Out-Null
}

# ---- 1. Copy web UI + android sources ----
Write-Host '[1/8] Copy sources ...'
Copy-Item "$root\app" "$ws\assets" -Recurse -Force
Copy-Item "$PSScriptRoot\AndroidManifest.xml" $ws -Force
Copy-Item "$PSScriptRoot\src" $ws -Recurse -Force
Copy-Item "$PSScriptRoot\icon_char.txt" $ws -Force

# ---- 2. Generate launcher icon ----
Write-Host '[2/8] Generate icon ...'
Add-Type -AssemblyName System.Drawing
$size = 192
$bmp = New-Object System.Drawing.Bitmap $size, $size
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.Clear([System.Drawing.Color]::Transparent)
$rect = New-Object System.Drawing.Rectangle 8, 8, 176, 176
$rectF = New-Object System.Drawing.RectangleF 8, 8, 176, 176
$path = New-Object System.Drawing.Drawing2D.GraphicsPath
$r = 40
$path.AddArc($rect.X, $rect.Y, $r, $r, 180, 90)
$path.AddArc($rect.Right - $r, $rect.Y, $r, $r, 270, 90)
$path.AddArc($rect.Right - $r, $rect.Bottom - $r, $r, $r, 0, 90)
$path.AddArc($rect.X, $rect.Bottom - $r, $r, $r, 90, 90)
$path.CloseFigure()
$blue = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 26, 111, 181))
$g.FillPath($blue, $path)
$font = New-Object System.Drawing.Font 'Microsoft YaHei', 92, ([System.Drawing.FontStyle]::Bold), ([System.Drawing.GraphicsUnit]::Pixel)
$fmt = New-Object System.Drawing.StringFormat
$fmt.Alignment = [System.Drawing.StringAlignment]::Center
$fmt.LineAlignment = [System.Drawing.StringAlignment]::Center
$g.DrawString([System.IO.File]::ReadAllText("$ws\icon_char.txt", [System.Text.Encoding]::UTF8).Trim(), $font, [System.Drawing.Brushes]::White, $rectF, $fmt)
$bmp.Save("$ws\res\mipmap-xxxhdpi\ic_launcher.png", [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()

# ---- 3. aapt2 compile ----
Write-Host '[3/8] aapt2 compile ...'
& "$buildTools\aapt2.exe" compile --dir "$ws\res" -o "$ws\res.zip"
if ($LASTEXITCODE -ne 0) { throw 'aapt2 compile failed' }

# ---- 4. aapt2 link (assets 由第7步手动加入，确保使用正斜杠路径) ----
Write-Host '[4/8] aapt2 link ...'
& "$buildTools\aapt2.exe" link -o "$ws\base.apk" -I $platform `
    --manifest "$ws\AndroidManifest.xml" `
    --java "$ws\gen" `
    --min-sdk-version 21 --target-sdk-version 34 `
    "$ws\res.zip"
if ($LASTEXITCODE -ne 0) { throw 'aapt2 link failed' }

# ---- 5. javac ----
Write-Host '[5/8] javac ...'
& javac --release 8 -encoding UTF-8 -classpath $platform `
    -d "$ws\classes" `
    "$ws\gen\com\sjkglxt\app\R.java" `
    "$ws\src\com\sjkglxt\app\MainActivity.java"
if ($LASTEXITCODE -ne 0) { throw 'javac failed' }

# ---- 6. d8 ----
Write-Host '[6/8] d8 ...'
& java -cp "$buildTools\lib\d8.jar" com.android.tools.r8.D8 `
    --lib $platform --output $ws `
    "$ws\classes\com\sjkglxt\app\R.class" `
    "$ws\classes\com\sjkglxt\app\MainActivity.class"
if ($LASTEXITCODE -ne 0) { throw 'd8 failed' }

# ---- 7. add assets + dex, then zipalign ----
Write-Host '[7/8] add assets + dex, zipalign ...'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::Open("$ws\base.apk", 'Update')
# assets (force forward-slash entry names for Android AssetManager)
foreach ($f in Get-ChildItem "$ws\assets" -Recurse -File) {
    $rel = $f.FullName.Substring("$ws\assets".Length).TrimStart('\', '/') -replace '\\', '/'
    $entry = $zip.CreateEntry("assets/$rel", [System.IO.Compression.CompressionLevel]::Optimal)
    $es = $entry.Open()
    $fs = [System.IO.File]::OpenRead($f.FullName)
    $fs.CopyTo($es)
    $fs.Close(); $es.Close()
}
# classes.dex
$entry = $zip.CreateEntry('classes.dex', [System.IO.Compression.CompressionLevel]::Optimal)
$es = $entry.Open()
$fs = [System.IO.File]::OpenRead("$ws\classes.dex")
$fs.CopyTo($es)
$fs.Close(); $es.Close(); $zip.Dispose()
& "$buildTools\zipalign.exe" -f 4 "$ws\base.apk" "$ws\aligned.apk"
if ($LASTEXITCODE -ne 0) { throw 'zipalign failed' }

# ---- 8. sign ----
Write-Host '[8/8] apksigner ...'
if (-not (Test-Path $keystore)) { throw "debug keystore not found: $keystore" }
& java -jar "$buildTools\lib\apksigner.jar" sign `
    --ks $keystore --ks-pass pass:android `
    --ks-key-alias androiddebugkey --key-pass pass:android `
    --out "$ws\sjkglxt.apk" "$ws\aligned.apk"
if ($LASTEXITCODE -ne 0) { throw 'apksigner failed' }

# ---- 9. copy result back ----
Copy-Item "$ws\sjkglxt.apk" "$root\sjkglxt.apk" -Force
$apk = Get-Item "$root\sjkglxt.apk"
Write-Host ""
Write-Host "BUILD OK: $($apk.FullName)  ($([math]::Round($apk.Length/1MB,2)) MB)"

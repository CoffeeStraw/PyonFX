$clnt = new-object System.Net.WebClient
$clnt.DownloadFile("https://mirrors.tuna.tsinghua.edu.cn/osdn/mix-mplus-ipa/58720/migu-1p-20130430.zip", "migu.zip")

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory("migu.zip", "C:\InstallFont\")
[System.IO.File]::Delete("migu.zip")

$SourceDir   = "C:\InstallFont\"
$Source      = "C:\InstallFont\*"
$Destination = (New-Object -ComObject Shell.Application).Namespace(0x14)
$TempFolder  = "C:\Windows\Temp\Fonts"

# Create the source directory if it doesn't already exist
New-Item -ItemType Directory -Force -Path $SourceDir
New-Item $TempFolder -Type Directory -Force | Out-Null
Get-ChildItem -Path $Source -Include '*.ttf','*.ttc','*.otf' -Recurse | ForEach {
    If (-not(Test-Path "C:\Windows\Fonts\$($_.Name)")) {

        $Font = "$TempFolder\$($_.Name)"
        
        # Copy font to local temporary folder
        Copy-Item $($_.FullName) -Destination $TempFolder
        
        # Install font
        $Destination.CopyHere($Font,0x10)

        # Delete temporary copy of font
        Remove-Item $Font -Force
    }
}
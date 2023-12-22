<#
    .SYNOPSIS
        Builds ATV-Annotation tool as EXE file for Windows
    .DESCRIPTION
        The build-tools.ps1 uses Pyinstaller to build labelImg adapted by ATV for the Annotation jobs.
        Builds the app and dumps all necessary files into a directory that can be deployed.
    .PARAMETER PathToAnnotation
        Path to the ATV-Annotation repository that contains
    .PARAMETER PathToAnaconda3
        Specify where is the Anaconda3 installed.
    .PARAMETER OutputPath
        Specify Path where output will be put.
    .PARAMETER CompressBuild
        Compress ZIP ready for deployment and put it at OutputPath
#>

param(
    [parameter(Mandatory, HelpMessage= 'Provide path to ATV-Annotation repository')] [String] $PathToAnnotation,
    [parameter(Mandatory, HelpMessage= 'Provide path to Anaconda3 installation')] [String] $PathToAnaconda3,
    [parameter(HelpMessage= 'Specify build output path. Default=<PathToAnnotation>\ATV-Annotation-builds')] [String] $OutputPath="${PathToAnnotation}\ATV-Annotation-builds",
    [switch]$CompressBuild
)

$curr_pwd=$(Get-Location)
Set-Location ${PathToAnnotation}

$VERSION=$(git describe --abbrev=0 --tags)
$BUILD_VERSION="ATV-Annotation-Client-${VERSION}"

Set-Location ${curr_pwd}
# If you want to build with darknet-yolo models, add them with --add-data and -p (follow the examples):
# Each model should have a data, names, cfg and weights file.
pyinstaller `
    --add-data "${PathToAnnotation}\annotation\data\*;.\data" `
    --add-data "${PathToAnnotation}\annotation\resources_dl\darknet\*;.\resources_dl\darknet" `
    --add-data "${PathToAnnotation}\annotation\resources_dl\darknet\win\darknet\lib\*;.\resources_dl\darknet\win\darknet\lib" `
    --add-data "${PathToAnnotation}\annotation\3rd_party\*;.\3rd_party" `
    --add-data "${PathToAnaconda3}\Lib\site-packages\certifi\cacert.pem;.\certifi\" `
    --hidden-import=resources_dl --hidden-import=xml --hidden-import=xml.etree --hidden-import=xml.etree.ElementTree --hidden-import=lxml.etree --hidden-import=lxml._elementpath `
    -n labelImg -D -c "${PathToAnnotation}\annotation\labelImg.py" `
    --distpath ${OutputPath}\${BUILD_VERSION}\dist `
    --workpath ${OutputPath}\${BUILD_VERSION}\build `
    -p ${PathToAnnotation}\annotation\libs\ `
    -p ${PathToAnnotation}\annotation\ `
    -p ${PathToAnnotation}\annotation\resources_dl\darknet `
    -p ${PathToAnnotation}\annotation\resources_dl\darknet\win\darknet\lib `
    -p ${PathToAnnotation}\annotation\data\ `
    -p ${PathToAnnotation}\annotation\3rd_party\

if (${CompressBuild})
{
    Compress-Archive -Path "${OutputPath}\${BUILD_VERSION}\dist\*" `
        -DestinationPath "${OutputPath}\${BUILD_VERSION}.zip" `
        -CompressionLevel "Optimal" `
        -Force

    Remove-Item -Recurse -Force ${OutputPath}\${BUILD_VERSION}
    
}

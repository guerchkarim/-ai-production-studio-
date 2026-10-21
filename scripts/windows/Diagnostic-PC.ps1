$ErrorActionPreference='Stop'
$StudioComputer=Get-CimInstance Win32_ComputerSystem
$StudioOS=Get-CimInstance Win32_OperatingSystem
$StudioReport=[ordered]@{
    systeme=$StudioOS.Caption
    architecture=$StudioOS.OSArchitecture
    ram_go=[math]::Round($StudioComputer.TotalPhysicalMemory/1GB,1)
    cpu=@(Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors)
    graphiques=@(Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion)
    disques=@(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Select-Object DeviceID,@{N='libre_go';E={[math]::Round($_.FreeSpace/1GB,1)}},@{N='taille_go';E={[math]::Round($_.Size/1GB,1)}})
    outils=[ordered]@{}
}
foreach($StudioTool in @('python','node','npm','ffmpeg','nvidia-smi')) { $StudioReport.outils[$StudioTool]=[bool](Get-Command $StudioTool -ErrorAction SilentlyContinue) }
$StudioReport | ConvertTo-Json -Depth 6
# Ne lit ni fichiers personnels, ni environnement, ni cles API. Aucun envoi reseau.

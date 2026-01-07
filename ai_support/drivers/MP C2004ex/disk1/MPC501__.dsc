;
; Driver Installer Section (For DrvInst)
;
; Copyright (c) 2007-2024 RICOH COMPANY, LTD
; All Rights Reserved
;

[DrvInst]
DrvInst=LANIER MP C501 PS,NRG MP C501 PS,RICOH MP C501 PS,SAVIN MP C501 PS
Comment="PS Driver (For Windows)"
DriverType=PS
DriverArchitecture=ARC2010ALFA
Version=3
IniFileName=rpdinstv.ini,allusers
IniFileSupport=4
ScenarioInstallOK=ON
RConfigFileOSVersion=3
DriverVersion=3.0.0.0
Platform=NTamd64
RCFFormatVersion=1.0
ModelName.LANIER MP C501 PS = "MP C501"
ModelName.NRG MP C501 PS = "MP C501"
ModelName.RICOH MP C501 PS = "MP C501"
ModelName.SAVIN MP C501 PS = "MP C501"
CheckDriverAlreadyInstalled=OFF
PreventSameKindUpdate=ON
InstallBidiOK=ON
UserIDSupportLevel=1
PackageInstall=ON
IniFileCharacterSet=UTF8
ForceSettingDeviceProperty=ON
BidiUpdateEnableUserPrivilegeSupport=ON
NXIdentify=1

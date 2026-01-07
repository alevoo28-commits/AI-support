;
; Driver Installer Section (For DrvInst)
;
; Copyright (c) 2007-2024 RICOH COMPANY, LTD
; All Rights Reserved
;

[DrvInst]
DrvInst=LANIER SP C352DN PS,NRG SP C352DN PS,RICOH SP C352DN PS,SAVIN SP C352DN PS
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
ModelName.LANIER SP C352DN PS = "SP C352DN"
ModelName.NRG SP C352DN PS = "SP C352DN"
ModelName.RICOH SP C352DN PS = "SP C352DN"
ModelName.SAVIN SP C352DN PS = "SP C352DN"
CheckDriverAlreadyInstalled=OFF
PreventSameKindUpdate=ON
InstallBidiOK=ON
UserIDSupportLevel=1
PackageInstall=ON
IniFileCharacterSet=UTF8
ForceSettingDeviceProperty=ON
BidiUpdateEnableUserPrivilegeSupport=ON
NXIdentify=1

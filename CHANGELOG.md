# Changelog

All notable changes to this project will be documented in this file.

***

## [v0.1.12] - 2024-05-10

- Minor fix


## [v0.1.11] - 2024-05-05

- Updated API url mount point


## [v0.1.10] - 2024-04-24

- Added watchdog feature (test notification channel)
- Added a new endpoint to obtain the current version (from GitHub) of Velero-UI complementary projects  


## [v0.1.9] - 2024-04-02

- Automatic generation token keys (access and login) if the user has not provided keys.<br>They persist until a reboot.

## [v0.1.8] - 2024-03-31

- Added watchdog feature
- Added refresh token mechanism


## [v0.1.7] - 2024-03-16

- Added restic check feature
- Added websocket authentication
- Updated execution of secondary processes from synchronous to asynchronous
- Improved notifications and messages system
- Minor fix


## [v0.1.6] - 2024-03-05

- Fixed error in get storage class
- Added endpoint to get the logs for the pod that execute the script API
- Added restic feature (check locks, unlock, unlock --remove-all)
- Updated k8s files
- Updated RBAC: Implemented new roles/cluster roles with minimum requirements for the application, following the principle of least privilege (PoLP)


## [v0.1.5] - 2024-03-02

- The PrinterHelper class internally handles the print level output
- Fixed error in backup expiration update


## [v0.1.4] - 2024-02-27

- Restructured backend with new controller and service modules for improved organization and separation of concerns
- Fixed the use of *velero* as fixed namespace request with the env value **K8S_VELERO_NAMESPACE**
- Added the environment var **DOWNLOAD_TMP_FOLDER** for destination data when executing *velero backup download*
- Added the environment var **VELERO_CLI_PATH_CUSTOM** where the user can load manually the binary


## [v0.1.3] - 2024-02-17

- Added diagnostic feature
- Added environment variable validation feature
- Added velero client download feature based on environment variable
- Added arm64 support
- Some improvements
- Fix minor bug


## [v0.1.2] - 2024-02-12

- Added storage class mapping feature
- Minor fix


## [v0.1.1] - 2024-02-04

- Some improvements


## [v0.1.0] - 2024-01-29

- 🎉 first release!


***

[v0.1.10] : [https://github.com/seriohub/velero-api/releases/tag/v0.1.10](https://github.com/seriohub/velero-api/releases/tag/v0.1.11)

[v0.1.10] : [https://github.com/seriohub/velero-api/releases/tag/v0.1.10](https://github.com/seriohub/velero-api/releases/tag/v0.1.10)

[v0.1.9] : [https://github.com/seriohub/velero-api/releases/tag/v0.1.9](https://github.com/seriohub/velero-api/releases/tag/v0.1.9)

[v0.1.8] : [https://github.com/seriohub/velero-api/releases/tag/v0.1.8](https://github.com/seriohub/velero-api/releases/tag/v0.1.8)

[v0.1.7] : [https://github.com/seriohub/velero-api/releases/tag/v0.1.7](https://github.com/seriohub/velero-api/releases/tag/v0.1.5)

[v0.1.6] : [https://github.com/seriohub/velero-api/releases/tag/v0.1.6](https://github.com/seriohub/velero-api/releases/tag/v0.1.5)

[v0.1.5] : [https://github.com/seriohub/velero-api/releases/tag/v0.1.5](https://github.com/seriohub/velero-api/releases/tag/v0.1.5)

[v0.1.4] : [https://github.com/seriohub/velero-api/releases/tag/v0.1.4](https://github.com/seriohub/velero-api/releases/tag/v0.1.4)

[v0.1.3] : [https://github.com/seriohub/velero-api/releases/tag/v0.1.3](https://github.com/seriohub/velero-api/releases/tag/v0.1.3)

[v0.1.2] : [https://github.com/seriohub/velero-api/releases/tag/v0.1.2](https://github.com/seriohub/velero-api/releases/tag/v0.1.2)

[v0.1.1] : [https://github.com/seriohub/velero-api/releases/tag/v0.1.1](https://github.com/seriohub/velero-api/releases/tag/v0.1.1)

[v0.1.0] : [https://github.com/seriohub/velero-api/releases/tag/v0.1.0](https://github.com/seriohub/velero-api/releases/tag/v0.1.0)
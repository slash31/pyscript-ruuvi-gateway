# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 9/21/2021
### Changed
- Updated global decimal precision to be per-measurement
- Script now returns an integer if precision is 0
- Generalized battery min/max to range values in per-measurement configs
### Added
- support for RSSI
## [0.1.1] - 9/18/2021
### Changed
- Bug-fixes related to unicode in YAML, updated sample measurements config to include pressure and tx_power. 

## [0.1.0] - 9/18/2021
### Added
- The script now creates an "attributes" topic in MQTT for each ruuvitag

## [0.0.3] - 9/16/2021
### Changed
- All configuration has been moved to the main HA /config/configuration.yaml file (sample file added)
### Added
- Log output with MAC address for beaconing tags that aren't in RUUUVITAG (rudimentary discovery)
## [0.0.2] - 9/15/2021
### Changed
- Minor bug fixes
## [0.0.1] - 9/14/2021
### Added
- Initial commit


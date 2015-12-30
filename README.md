# Pira-FM-RDS-Decoder
Decodes the raw RDS stream from a Pira.CZ FM Analyser and sends it to a web server

See http://mediarealm.com.au/articles/2013/05/parsing-rds-group-data-with-pira-p175-and-python/ for the original information about this script.

See also: https://twitter.com/SydneyRDS

## Installation

1. Connect Pira FM Analyser to USB port
2. Install Python 2.7
3. Install PySerial
4. Rename config-sample.json to config.json
5. Change the serial port in config.json
 a. On Unix systems (Mac & Linux), use 'ls /dev/tty.*' to find the port name
6. In config.json, setup all your stations (frequency must be in six-digit format e.g. 103.2fm = 103200)
7. Run pira-rds.py

Pull requests welcome.

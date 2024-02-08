============
 Change Log
============

This file keeps track of all notable changes to charm-jobbergate-agent.

Unreleased
----------
- Improved dispatch file to correctly build and install python3.12 on ubuntu.
- Added github action to make edge releases.
- Removed Makefile.

1.0.2 - 2023-12-11
------------------ 
- Added trigger to install jobbergate-agent's addons on charm install
- Dropped support for CentOS 8
- Installed Python 3.12 to run the agent

1.0.1 - 2023-11-29
------------------ 
- Added configuration to control if the submission files should be written to the submit directory

1.0.0 - 2023-09-07
------------------ 
- Starting charm-jobbergate-agent

#!/usr/bin/env bash

nohup /users/cprobert/anaconda/bin/python \
    /users/cprobert/dev/system-monitor/gpu-monitor.py \
    --dbpath /srv/persistent/cprobert/sys-logging/ &

echo "Logging started"

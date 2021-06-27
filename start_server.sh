#!/bin/bash

pid=`pgrep -f "api.svc"`
kill -9 $pid
python -m api.svc.photos_dimensions_svc &
python -m api.svc.photos_resizing_svc &
python run.py

#!/bin/bash


sudo systemctl restart better_seconds_web.service
sudo systemctl restart better_seconds_server.service

source .venv/bin/activate

python capture.py
#!/bin/bash

sudo systemctl $1 better_seconds_record.service
sudo systemctl $1 better_seconds_web.service
sudo systemctl $1 better_seconds_server.service

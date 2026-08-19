#!/bin/sh
set -e

aerich upgrade

exec python -m app
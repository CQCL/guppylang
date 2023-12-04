#!/bin/bash

python -m tests.error.$1.$2 2> tests/error/$1/$2.err

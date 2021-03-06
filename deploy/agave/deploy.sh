#!/bin/bash

stickytape "src/icarus/parse/events/__main__.py" \
    --add-python-path "src/" \
    --output-file "deploy/agave/events_standalone.py"
stickytape "src/icarus/generate/population/__main__.py" \
    --add-python-path "src/" \
    --output-file "deploy/agave/population_standalone.py"
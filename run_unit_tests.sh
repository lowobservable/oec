#!/bin/bash

# Display verbose output in CI environment.
if [ -n "$CI" ]; then
    OPTS=-v
fi

python -m unittest discover $OPTS tests

#!/bin/bash
path_to_poetry=$(which poetry)
if [ -x "$path_to_poetry" ] ; then
	PYTHONHASHSEED=0 PYTHONSTARTUP=main.py poetry run ipython
else
	PYTHONHASHSEED=0 PYTHONSTARTUP=main.py ipython
fi

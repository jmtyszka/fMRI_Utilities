#!/bin/bash
#
# Build a midspace template with an initial affine pass then a defeomorphic pass
#
# AUTHOR : Mike Tyszka
# PLACE  : Caltech
# DATES  : 09/12/2013 JMT Build on ANTS_build_template.sh script

# Get command line args
image_list=$@

ANTS_buildmmtemplateparallel.sh -d 3 -k 2 -o MIDSPACE_ ${image_list}

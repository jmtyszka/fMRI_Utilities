#!/bin/bash
#
# Build a midspace template with an initial affine pass then a defeomorphic pass
#
# AUTHOR : Mike Tyszka
# PLACE  : Caltech
# DATES  : 09/12/2013 JMT Build on ANTS_build_template.sh script

# Get command line args
image_list=$@

# First pass affine
ANTS_buildtemplateparallel.sh -d 3 -m 1x0x0 -o AFFINE_ ${image_list}

# Second pass defeomorphic
ANTS_buildtemplateparallel.sh -d 3 -z AFFINE_template.nii.gz -o MIDSPACE_ ${image_list}

# Clean up
# rm -rf ants* tmp* AFFINE* GR*

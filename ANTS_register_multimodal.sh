#!/bin/bash
#
# Affine registration of different modalities from the same subject (eg T1 and T2) with
# slightly different geometry or head position (motion, etc)
#
# AUTHOR : Mike Tyszka
# PLACE  : Caltech
# DATES  : 08/23/2013 JMT Adapt from *.sh

# ITK thread count
ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=2
export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS

# Check args
if [ $# -lt 2 ]; then
  echo "USAGE: $0 <fixed>.nii.gz <moving>.nii.gz"
  exit
fi

# Assign arguments
fixed=`imglob -extension .nii.gz $1`
moving=`imglob -extension .nii.gz $2`

echo "Registering $moving to $fixed"

# Prefix for output transform files
outPrefix=${moving%%.nii.gz}

echo "Output prefix : $outPrefix"

# Registration dimensionality (always 3D)
dim=3

# Mattes metric parameters
metricWeight=1
numberOfBins=32

# Deformable
antsRegistration \
   --dimensionality $dim \
   --initial-moving-transform [ $fixed, $moving, 0 ] \
   --metric mattes[ $fixed, $moving, $metricWeight, $numberOfBins ] \
   --transform syn[ 20x10, 0.25, 3, 0.5 ] \
   --convergence [20x10, 1.e-8, 10]  \
   --smoothing-sigmas 1x0 \
   --shrink-factors 2x1 \
   --use-histogram-matching $uval \
   -o [ ${outPrefix}_xfm, ${outPrefix}_warped.nii.gz ]

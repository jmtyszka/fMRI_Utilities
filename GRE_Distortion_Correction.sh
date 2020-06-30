#!/bin/bash
#
# Simple GRE fieldmap unwarping of 4D EPI data
#
# AUTHOR: Mike Tyszka
# PLACE : Caltech
# DATES : 2020-03-09 JMT From scratch
#         2020-06-30 JMT Increase debugging output

echo ""
echo "----------------------------------------"
echo "Motion correction and fieldmap unwarping"
echo "----------------------------------------"
echo ""

# Force FSL to use uncompressed NIFTI outputs
# export FSLOUTPUTTYPE=NIFTI_GZ
export FSLOUTPUTTYPE=NIFTI

#
# Source files - PLEASE EDIT
#

# Phase difference image
c_fmap_phs=phasediff.nii
c_fmap_mag=magnitude.nii
d_func=func.nii

#
# Generated files
#

d_func_moco=d_func_moco.nii
d_func_mean=d_func_mean.nii
c_func=c_func.nii
c_func_mean=c_func_mean.nii

c_signal_mask=c_signal_mask.nii
c_fmap_mag_masked=c_fmap_mag_masked.nii
c_fmap_rads=c_fmap_rads.nii
d_fmap_mag=d_fmap_mag.nii
d_fmap_rads=d_fmap_rads.nii

tmp_brain=tmp_brain.nii
tmp_mask=tmp_signal_mask.nii

d_fmap_mag_to_d_func=d_fmap_mag_to_d_func.nii
d_fmap_rads_to_d_func=d_fmap_rads_to_d_func.nii
d_fmap_mag_to_d_func_tx=d_fmap_mag_to_d_func.mat

# Hardwired echo time difference for GRE fieldmap (ms)
dTE=2.54

# fMRI EPI effective echo spacing in seconds (from dcm2niix JSON sidecar)
# This must account for any in-plane acceleration used (GRAPPA R factor)
func_esp="0.00051394"

# Image phase encoding axis for unwarping
# Possible values: x, x-, y, y-, z, z-
# This should be confirmed by inspection of the distorted (d_) and corrected (c_) EPI images relative to an undistorted reference
d2c_unwarp_dir="x"
c2d_unwarp_dir="x-"

# Motion correct the distorted EPI timeseries as needed
if [ -s $d_func_moco ]
then
    echo "Temporal mean EPI already calculated - skipping"
else
    echo "Motion correcting distorted EPI timeseries"
    mcflirt -in ${d_func} -out ${d_func_moco} -meanvol -stats -plots -report
fi

# Generate temporal mean EPI from motion corrected timeseries
if [ -s ${d_func_mean} ]
then
    echo "Temporal mean EPI already calculated - skipping"
else
    echo "Computing distorted temporal mean EPI"
    fslmaths ${d_func_moco} -Tmean ${d_func_mean}
fi

# Preparing signal mask (75th percentile)
thr=`fslstats ${c_fmap_mag} -p 75`
echo "Preparing eroded brain mask for GRE fieldmap"
fslmaths ${c_fmap_mag} -thr ${thr} -bin ${c_signal_mask}

# Apply brain mask to GRE fieldmap mag
echo "Applying eroded brain mask to fieldmap magnitude"
fslmaths ${c_fmap_mag} -mas ${c_signal_mask} ${c_fmap_mag_masked}

# Prepare the rad/s fieldmap
echo "Preparing rad/s fieldmap"
fsl_prepare_fieldmap SIEMENS ${c_fmap_phs} ${c_fmap_mag_masked} ${c_fmap_rads} ${dTE}

# Warp the GRE mag and phs fieldmap to distorted EPI space
echo "Warping GRE fieldmap back to distorted EPI space"
fugue -i ${c_fmap_mag} --dwell=${func_esp} --loadfmap=${c_fmap_rads} --unwarpdir=${c2d_unwarp_dir} --nokspace -w ${d_fmap_mag}
fugue -i ${c_fmap_rads} --dwell=${func_esp} --loadfmap=${c_fmap_rads} --unwarpdir=${c2d_unwarp_dir} --nokspace -w ${d_fmap_rads}

# Find rigid body transform mapping distorted GRE fmap to distorted fMRI EPI space
echo "Computing rigid body transform from distorted GRE to distorted fMRI EPI space"
flirt -in ${d_fmap_mag} -ref ${d_func_mean} -dof 6 -cost normcorr -out ${d_fmap_mag_to_d_func} -omat ${d_fmap_mag_to_d_func_tx}

# Apply the same transform to the distorted fieldmap
echo "Resampling distorted fieldmap to fMRI EPI space"
flirt -in ${d_fmap_rads} -ref ${d_func_mean} -init ${d_fmap_mag_to_d_func_tx} -applyxfm -out ${d_fmap_rads_to_d_func}

#
# Distortion correct fMRI EPI dataset
#

# Apply distortion correction to 4D fMRI EPI data
echo "Applying distortion correction to fMRI EPI data"
fugue -i ${d_func} --dwell=${func_esp} --loadfmap=${d_fmap_rads_to_d_func} --unwarpdir=${c2d_unwarp_dir} -u ${c_func}

# Calculate temporal mean undistorted fMRI EPI image
echo "Calculating temporal mean corrected fMRI EPI"
fslmaths ${c_func} -Tmean ${c_func_mean}

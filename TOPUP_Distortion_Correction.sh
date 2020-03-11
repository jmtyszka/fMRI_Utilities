#!/bin/bash
#
# TOPUP-based EPI distortion correction
#
# AUTHOR : Mike Tyszka
# PLACE  : Caltech Brain Imaging Center
# DATES  : 2020-03-10 JMT Adapted and commented from Pinglei's code snippet

# Exit on error
set -e

# Force FSL to use uncompressed NIFTI outputs
# export FSLOUTPUTTYPE=NIFTI_GZ
export FSLOUTPUTTYPE=NIFTI

#
# Source images - *** PLEASE EDIT ***
#

# Distorted 4D EPI and temporal mean 3D EPI
d_func="bold.nii"

# Distorted phase encoding reversed SE-EPI pair
d_seepi_A="dir-LR_epi.nii"
d_seepi_B="dir-RL_epi.nii"

# SE-EPI imaging parameters for TOPUP recon
seepi_pars="seepi.pars"

# fMRI EPI effective echo spacing in seconds (from dcm2niix JSON sidecar)
func_esp="0.00048"

# Image phase encoding axis for warping and unwarping
# This should be confirmed by inspection of the distorted (d) and corrected (c) EPI images relative to an undistorted reference
d2c_unwarp_dir="x"

#
# Generated images
#

# Distorted EPI space images
d_func_mean="d_func_mean.nii"
d_seepi_both="d_seepi_both.nii"

# Geometrically correct images
c_seepi_both="c_seepi_both.nii"  # Corrected separate SE-EPI pair
c_seepi_mean="c_seepi_mean.nii"  # Corrected mean SE-EPI
c_fmap_Hz="c_fmap_Hz.nii"  # Corrected fieldmap in Hz
c_fmap_rads="c_fmap_rads.nii"  # Corrected fieldmap in rad/s
c_func="c_func.nii" # Corrected 4D fMRI EPI

# Distorted EPI space images
d_seepi_mean="d_seepi_mean.nii"  # Distorted mean SE-EPI
d_fmap_rads="d_fmap_rads"

# Rigid body transform mapping distorted SE-EPI to distorted fMRI EPI space
d_seepi_to_d_func_tx="d_seepi_to_d_func_tx.mat"
d_seepi_mean_to_d_func="d_seepi_mean_to_d_func.nii"
d_fmap_rads_to_d_func="d_fmap_rads_to_d_func.nii"

#
# Run TOPUP on SE-EPI pair
#

# Calculate temporal mean EPI - assumes prior alignment of all volumes
echo "Calculating distorted mean fMRI EPI"
fslmaths ${d_func} -Tmean ${d_func_mean}

# Stack SE-EPI fieldmap pair into a single 4D image
echo "Stacking SE-EPI image pair"
fslmerge -t ${d_seepi_both} ${d_seepi_A} ${d_seepi_B}

# Run TOPUP recon on SE-EPI pair
# Use standard B0-to-B0 configuration
if [ -s ${c_fmap_Hz} ]
then
    echo "TOPUP already run - skipping"
else
    echo "Running TOPUP reconstruction"
    topup --imain=${d_seepi_both} --datain=${seepi_pars} --config=b02b0.cnf --fout=${c_fmap_Hz} --iout=${c_seepi_both}
fi

# Convert B0 fieldmap output by TOPUP from Hz to rad/s
echo "Converting TOPUP fieldmap from Hz to rad/s"
fslmaths ${c_fmap_Hz} -mul 6.283185 ${c_fmap_rads}

# Average corrected SE-EPI pair
echo "Averaging corrected SE-EPI pair"
fslmaths ${c_seepi_both} -Tmean ${c_seepi_mean}

#
# Distort and register TOPUP magnitude and fieldmap back to distorted fMRI EPI space
#

# Warp both corrected SE-EPI images and TOPUP fieldmap back into distorted EPI space
echo "Warping TOPUP results back to distorted EPI space"
fugue -i ${c_seepi_mean} --dwell=${func_esp} --loadfmap=${c_fmap_rads} --unwarpdir=${d2c_unwarp_dir} --nokspace -w ${d_seepi_mean}
fugue -i ${c_fmap_rads} --dwell=${func_esp} --loadfmap=${c_fmap_rads} --unwarpdir=${d2c_unwarp_dir} --nokspace -w ${d_fmap_rads}

# Find rigid body transform mapping distorted SE-EPI to distorted fMRI EPI space
echo "Computing rigid body transform from distorted SE-EPI to distorted fMRI EPI space"
flirt -in ${d_seepi_mean} -ref ${d_func_mean} -dof 6 -cost normcorr -out ${d_seepi_mean_to_d_func} -omat ${d_seepi_to_d_func_tx}

# Apply the same transform to the distorted fieldmap
echo "Resampling distorted TOPUP fieldmap to fMRI EPI space"
flirt -in ${d_fmap_rads} -ref ${d_func_mean} -init ${d_seepi_to_d_func_tx} -applyxfm -out ${d_fmap_rads_to_d_func}

#
# Distortion correct fMRI EPI dataset
#

# Apply distortion correction to 4D fMRI EPI data
echo "Applying distortion correction to fMRI EPI data"
fugue -i ${d_func} --dwell=${func_esp} --loadfmap=${d_fmap_rads_to_d_func} --unwarpdir=${d2c_unwarp_dir} -u ${c_func}

# Calculate temporal mean undistorted fMRI EPI image
echo "Calculating temporal mean corrected fMRI EPI"

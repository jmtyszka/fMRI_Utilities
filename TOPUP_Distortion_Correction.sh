#!/bin/bash
#
# TOPUP-based EPI distortion correction
#
# AUTHOR : Mike Tyszka
# PLACE  : Caltech Brain Imaging Center
# DATES  : 2020-03-10 JMT Adapted and commented from Pinglei's code snippet
#          2020-07-18 JMT Switch to applytopup with Jacobian interpolation for correction
#                     JMT Modify topup configuration files for macaque length scale (macaque.cnf)

# Exit on error
set -e

# Force FSL to use uncompressed NIFTI outputs
# export FSLOUTPUTTYPE=NIFTI_GZ
export FSLOUTPUTTYPE=NIFTI

#
# Source images - *** PLEASE EDIT ***
#

# Distorted 4D BOLD or MION EPI
d_func_pos="func_LR.nii"

# Distorted phase encoding reversed SE-EPI pair
d_seepi_pos="seepi_LR.nii"
d_seepi_neg="seepi_RL.nii"

# SE-EPI imaging parameters for TOPUP recon
seepi_pars="seepi.pars"

# Image phase encoding axis for warping and unwarping
# This should be confirmed by inspection of the distorted (d) and corrected (c) EPI images relative to an undistorted reference
d2c_unwarp_dir="x"

#
# Generated images
#

# Distorted EPI space images
d_func_pos_mean="d_func_LR_mean.nii"
d_seepi_both="d_seepi_both.nii"

# TOPUP output parameters
topup_prefix=topup

# Geometrically correct images
c_seepi_both="c_seepi_both.nii"  # Corrected separate SE-EPI pair
c_seepi_mean="c_seepi_mean.nii"  # Corrected mean SE-EPI
c_fmap_Hz="c_fmap_Hz.nii"  # Corrected fieldmap in Hz
c_func="c_func.nii" # Corrected 4D fMRI EPI

# Rigid body transform mapping distorted SE-EPI to distorted fMRI EPI space
d_seepi_to_d_func_tx="d_seepi_to_d_func_tx.mat"
d_seepi_pos_to_d_func="d_seepi_pos_to_d_func.nii"
d_seepi_neg_to_d_func="d_seepi_neg_to_d_func.nii"

# Temporary volume prefix
vol_prefix=vol

#
# Run TOPUP on SE-EPI pair
#

# Calculate temporal mean EPI - assumes prior alignment of all volumes
echo "Calculating temporal mean of distorted fMRI EPI"
fslmaths ${d_func_pos} -Tmean ${d_func_pos_mean}

# Find rigid body transform mapping distorted SE-EPI to distorted fMRI EPI space
# Use positive PE SE-EPI image and temporal mean positive PE functional image
echo "Computing rigid body transform from distorted SE-EPI to distorted fMRI EPI space"
flirt -in ${d_seepi_pos} -ref ${d_func_pos_mean} -dof 6 -cost normcorr -out ${d_seepi_pos_to_d_func} -omat ${d_seepi_to_d_func_tx}

# Apply this same transform to the negative PE SE-EPI
echo "Resampling negative PE SE-EPI image to fMRI EPI space"
flirt -in ${d_seepi_neg} -ref ${d_func_pos_mean} -init ${d_seepi_to_d_func_tx} -applyxfm -out ${d_seepi_neg_to_d_func}

# Stack registered SE-EPI fieldmap pair into a single 4D image
echo "Stacking registered SE-EPI image pair"
fslmerge -t ${d_seepi_both} ${d_seepi_pos_to_d_func} ${d_seepi_neg_to_d_func}

# Run TOPUP recon on SE-EPI pair
# Use standard B0-to-B0 configuration
if [ -s ${c_fmap_Hz} ]
then
    echo "TOPUP already run - skipping"
else
    echo "Running TOPUP reconstruction"
    topup \
        --imain=${d_seepi_both} \
        --datain=${seepi_pars} \
        --config=./macaque.cnf \
        --out=${topup_prefix} \
        --fout=${c_fmap_Hz} \
        --iout=${c_seepi_both} \
        -v
fi

# Average corrected SE-EPI pair
echo "Averaging corrected SE-EPI pair"
fslmaths ${c_seepi_both} -Tmean ${c_seepi_mean}

#
# Distortion correct fMRI EPI dataset
#

# --- APPLYTOPUP ---

# Split into individual volumes
echo "Splitting functional timeseries into 3D volumes"
fslsplit ${d_func_pos} ${vol_prefix} -t

# Apply TOPUP correction to each volume separately
for vol in ${vol_prefix}*
do
    applytopup -i ${vol} -a ${seepi_pars} -x 1 -t ${topup_prefix} -m jac -o ${vol}_topup
done

# Recompose 4D timeseries
fslmerge -t ${c_func} ${vol_prefix}*_topup.*

# Clean up
rm -rf ${vol_prefix}*.nii

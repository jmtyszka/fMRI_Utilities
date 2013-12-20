#!/opt/local/bin/python
#
# Simulate long-TE dropout in a short-TE GRE image
# - designed to be run on the magnitude image of a fieldmap
# - requires numpy and nibabel
# - written under Python 2.7
#
# USAGE : dropout.py <fmap mag nifti> <fmap nifti> <TE>
#
# ARGS
# <fmap mag nifti> - Nifti-1 fieldmap magnitude image filename
# <fmap nifti>     - Nifti-1 fieldmap (in rad/s) image filename
# <TE>             - new effective TE in ms for dropout calculation [30 ms]
#
# AUTHOR : Mike Tyszka
# PLACE  : Caltech
# DATES  : 12/13/2013 JMT From scratch
#          12/16/2013 JMT Switch to spherical dephasing model, add command line args
#          12/17/2013 JMT Remove default image filenames
#          12/19/2013 JMT Switch to NiBabel
#
# This file is part of fMRI_Utilities.
#
#    fMRI_Utilities is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    fMRI_Utilities is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#   along with CBICQA.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2013 California Institute of Technology.

import sys
import os
import numpy as np
import nibabel as nib

USAGE = """
USAGE :
  dropout.py <fmap mag nifti> <fmap nifti> <TE>

ARGS :
  <fmap mag nifti> - Nifti-1 fieldmap magnitude image filename
  <fmap nifti>     - Nifti-1 fieldmap (in rad/s) image filename
  <TE>             - new effective TE in ms for dropout calculation [30 ms]
"""

# Main function
def main():

  # Command line args
  if len(sys.argv) < 3:
    print(USAGE)
    sys.exit()
  else:
    fmap_mag_file = sys.argv[1]
    fmap_file = sys.argv[2]

  # Simulated echo time in seconds
  if len(sys.argv) < 5:
    TE = 30.0
  else:
    TE = float(sys.argv[3]) / 1000.0

  # Isolate file stub in presence of .nii.gz or .nii extensions
  if '.nii.gz' in fmap_mag_file:
    dropout_file = fmap_mag_file[:-7]
  else:
    if '.nii' in fmap_mag_file:
      dropout_file = fmap_mag_file[:-4]
    else:
      dropout_file = fmap_mag_file

  # Complete output filename
  dropout_file = dropout_file + '_dropout.nii.gz'

  # Report arguments
  print('')
  print('Gradient Echo Dropout Simulator')
  print('-------------------------------')
  print('Fieldmap magnitude : ' + fmap_mag_file)
  print('Fieldmap phase     : ' + fmap_file)
  print('Simulated TE       : ' + str(TE) + ' ms')
  print('Adjusted mag image : ' + dropout_file)
  print('')
  print('Simulating intravoxel dephasing')

  # Load fmap_mag and fmap volumes
  # See http://niftilib.sourceforge.net/pynifti/examples.html for examples
  
  print('  Loading phase image from ' + fmap_file)
  try:
    nim_phi = nib.load(fmap_file)
  except:
    sys.exit()

  # Get phase data from Niftidd object
  phi = nim_phi.get_data()

  # Calculate grad(phi). Returns numpy array
  print('  Calculating grad(phi)')
  Gz, Gy, Gx = np.gradient(phi)
  
  # Calculate absolute gradient magnitude and scale to Hz/voxel
  print('  Calculating scaled absolute gradient')
  aG = np.sqrt(Gx*Gx + Gy*Gy + Gz*Gz) / (2 * np.pi)
  
  # Weighting function estimates additional signal loss from intravoxel
  # dephasing assuming spherical voxel and local linear gradient.
  # TODO: account for imaging x susceptibility gradient interactions
  print('  Calculating intravoxel dephasing weight')
  w = np.abs(np.sinc(TE / 1000.0 * aG))

  print('  Loading magnitude image from ' + fmap_mag_file)
  try:
    nim_M = nib.load(fmap_mag_file)
  except:
    sys.exit()

  # Get mag data from Nifti object
  M = nim_M.get_data()
    
  # Adjust TE of magnitude image
  print('  Applying weight to magnitude image')
  M_dropout = M * w

  # Construct output image - same affine transform as original mag image
  nim_M_dropout = nib.Nifti1Image(M_dropout, nim_M.get_affine())

  # Save long-TE mag image
  print('  Saving TE adjusted magnitude image to ' + dropout_file)
  nim_M_dropout.to_filename(dropout_file)

  print('Done')
  print('')
  

# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()

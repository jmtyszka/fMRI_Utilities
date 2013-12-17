#!/opt/local/bin/python
#
# Simulate long-TE dropout in a short-TE GRE image
# - designed to be run on the magnitude image of a fieldmap
# - requires numpy and pynifti
#
# USAGE : dropout.py <fmap mag nifti> <fmap nifti> <TE>
#
# ARGS :
# <fmap mag nifti> - Nifti-1 fieldmap magnitude image filename [fmap_mag.nii.gz]
# <fmap nifti>     - Nifti-1 fieldmap (in rad/s) image filename [fmap.nii.gz]
# <TE>             - new effective TE in ms for dropout calculation [30 ms]
#
# AUTHOR : Mike Tyszka
# PLACE  : Caltech
# DATES  : 12/13/2013 JMT From scratch
#          12/16/2013 JMT Switch to spherical dephasing model, add command line args
#
# Copyright 2013 California Institute of Technology.
# All rights reserved.

import sys
import os
import numpy as np
from nifti import *

USAGE = """
USAGE :
  dropout.py <fmap mag nifti> <fmap nifti> <TE>

ARGS :
  <fmap mag nifti> - Nifti-1 fieldmap magnitude image filename [fmap_mag.nii.gz]
  <fmap nifti>     - Nifti-1 fieldmap (in rad/s) image filename [fmap.nii.gz]
  <TE>             - new effective TE in seconds for dropout calculation [0.030 s]
"""

# Main function
def main():

  # Command line args
  if len(sys.argv) < 1:
    print(USAGE)
    
  if len(sys.argv) < 2:
    fmap_mag_file = 'fmap_mag.nii.gz'
  else:
    fmap_mag_file = sys.argv[1]

  if len(sys.argv) < 3:
    fmap_file = 'fmap.nii.gz'
  else:
    fmap_file = sys.argv[2]

  # Simulated echo time in seconds
  if len(sys.argv) < 4:
    TE = 30.0
  else:
    TE = float(sys.argv[3]) / 1000.0

  # Isolate file stub in presence of .nii.gz or .nii extensions
  if '.nii.gz' in fmap_mag_file:
    dropout_file = fmap_mag_file[:-7]
  else:
    if '.nii' in fmap_mag_file:
      dropout_file = fmap_mag_file[:-4]

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
    nim_phi = NiftiImage(fmap_file)
  except:
    sys.exit()

  # Get phase data from Nifti object
  phi = nim_phi.getScaledData()

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
    nim_M = NiftiImage(fmap_mag_file)
  except:
    sys.exit()

  # Get mag data from Nifti object
  M = nim_M.getScaledData()
    
  # Adjust TE of magnitude image
  print('  Applying weight to magnitude image')
  M_dropout = M * w

  # Calculate long-TE mag image
  nim_M_dropout = nim_M
  nim_M_dropout.setDataArray(M_dropout)

  # Save long-TE mag image
  print('  Saving TE adjusted magnitude image to ' + dropout_file)
  nim_M_dropout.save(dropout_file)

  print('Done')
  print('')
  

# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()

#!/opt/local/bin/python
"""
Calculate per-voxel ICC_c from TC-GICA dual regression results

Assumes intra-subject repeats are the inner loop in the 4D IC data

Usage
----
dr_icc.py -r <reps per participant> -o <output directory> <IC file list>
dr_icc.py -h

Example
----
>>> dr_icc.py -r 2 -o my_gica.icc dr_stage2_ic*.nii.gz

Authors
----
Mike Tyszka, Caltech Brain Imaging Center

Dates
----
2015-09-14 JMT From scratch

License
----
This file is part of atlaskit.

    fMRI_Utilities is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    fMRI_Utilities is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with fMRI_Utilities.  If not, see <http://www.gnu.org/licenses/>.

Copyright
----
2015 California Institute of Technology.
"""

__version__ = '0.1.0'

import os
import sys
import argparse
import nibabel as nib
import numpy as np
from scipy import stats


def main():
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Calculate ICC maps from dual regression results')
    parser.add_argument('-o', '--output', help='ICC output directory')
    parser.add_argument('-r', '--reps', help='Number of repetitions per participant')
    parser.add_argument('-m', '--mask', help='Binary mask image')
    parser.add_argument('ic_files', nargs='+', help='Space-separated list of stage 2 4D IC filenames')

    # Parse command line arguments
    args = parser.parse_args()

    # Output ICC directory
    icc_dir = args.output

    if args.mask:
        mask_nii = nib.load(args.mask)
        mask = mask_nii.get_data().astype(bool)
    
    d = int(args.reps)
    
    # Loop over all stage 2 4D IC files
    for ic, ic_fname in enumerate(args.ic_files):
        
        print('\nAnalyzing ' + ic_fname)
        
        # Load the 4D IC data
        ic_nii = nib.load(ic_fname)
        Y = ic_nii.get_data()
        
        [nx,ny,nz,nt] = ic_nii.header.get_data_shape()
        
        # Number of voxels in a volume
        nvox = nx * ny * nz
        n = nt / d

        print('  %d x %d x %d voxels for %d participants with %d repeats' % (nx,ny,nz,n,d))
        
        # Reshape to (nx*ny*nz, subject, rep)
        # Note the use of C-indexing, with the last index changing fastest
        # This means that rep should be last since the 4th-dimension of the original data
        # had rep within subject (rep changing faster than subject)
        print('  Reshaping data')
        Y = np.reshape(Y, (nvox, n, d))
    
        # Mean over repetitions (nvox x n)
        print('  Mean over repetitions')
        Mr = np.mean(Y, axis=2)
        
        # Mean over participants (nvox x d)
        print('  Mean over participants')
        Mp = np.mean(Y, axis=1)
        
        # Mean over repetitions and participants (nvox)
        # Collapse 3rd then 2nd dimensions in that order
        print('  Mean over repetitions and participants')
        Mrp = np.mean(np.mean(Y, axis=2), axis=1)

        # Sum of squares over participants (nvox)
        print('  Sum of squares over participants (SSp)')
        Mrp_i = np.tile(np.reshape(Mrp, [nvox, 1]), [1, n])
        SSp = d * np.sum((Mr - Mrp_i)**2.0, axis=1)
    
        # Reshape and tile the Y_bars to the same size as Y
        Mr_ij = np.tile(np.reshape(Mr, [nvox, n, 1]), [1, 1, d])
        Mp_ij = np.tile(np.reshape(Mp, [nvox, 1, d]), [1, n, 1])
        Mrp_ij = np.tile(np.reshape(Mrp, [nvox, 1, 1]), [1, n, d])

        # Sum of square errors (nvox)
        # Collapse 3rd then 2nd dimensions in that order
        print('  Sum of squares errors (SSe)')
        SSe = np.sum(np.sum((Y - Mr_ij - Mp_ij + Mrp_ij)**2.0, axis=2), axis=1)
        
        # Mean square over participants (nvox)
        MSp = SSp / (n - 1.0)
        
        # Mean square error (nvox)
        MSe = SSe / ((n - 1.0) * (d - 1.0))

        # ICC_c (nvox x 1)
        print('  Intraclass Correlation Coefficient (ICC_c)')
        ICC = (MSp - MSe) / (MSp + (d - 1.0) * MSe)
        
        # Write results to output directory
        suffix = '_%04d.nii.gz' % ic
        print('  Saving ICC'+suffix)
        
        ICC_nii = nib.Nifti1Image(np.reshape(ICC, [nx,ny,nz]), ic_nii.get_affine())
        ICC_nii.to_filename(os.path.join(icc_dir, 'ICC'+suffix))
        
        # Masked statistics
        if args.mask:
            
            ICC_mask = ICC[np.reshape(mask,[nvox])]

            icc_mode = stats.mode(ICC_mask).mode
            icc_mean = np.nanmean(ICC_mask)
            icc_med = np.nanmedian(ICC_mask)
            
            print('  Mode : %0.3f  Mean : %0.3f  Median %0.3f' % (icc_mode, icc_mean, icc_med))


    # Clean exit
    sys.exit(0)


# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()



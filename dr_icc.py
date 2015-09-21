#!/opt/local/bin/python
"""
Calculate per-voxel ICC from TC-GICA dual regression results
Implements ICC_c ie ICC(3,1) from Zhuo NIMG 2010

Assumes intra-subject repeats are the inner loop in the 4D IC data

References
----
Zuo, X.-N., Kelly, C., Adelstein, J.S., Klein, D.F., Castellanos, F.X., Milham, M.P., 2010.
Reliable intrinsic connectivity networks: Test-retest evaluation using ICA and dual regression approach.
NeuroImage 49, 2163–2177. doi:10.1016/j.neuroimage.2009.10.080

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
2015-09-19 JMT Export sample of masked ICC results for R plotting

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
import random


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
    ic_files = args.ic_files

    if args.mask:
        mask_nii = nib.load(args.mask)
        mask = mask_nii.get_data().astype(bool)
    
    # Number of repeats (from command line)
    d = int(args.reps)
    
    # Number of ICs (from command line file list)
    nic = np.shape(ic_files)[0]
    
    # Loop over all stage 2 4D IC files
    for ic, ic_fname in enumerate(ic_files):
        
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
        # Collapse 3rd (participant) then 2nd (rep) dimensions in that order
        print('  Mean over repetitions and participants')
        Mrp = np.mean(np.mean(Y, axis=2), axis=1)

        # Sum of squares over participants (nvox)
        print('  Sum of squares over participants (SSp)')
        SSp = np.zeros([nvox])
        for i in range(0,n):
            SSp[:] += (Mr[:,i] - Mrp)**2.0
        SSp *= float(d)
            
        # Sum of square errors (nvox)
        print('  Sum of squares errors (SSe)')
        SSe = np.zeros([nvox])
        for i in range(0,n):
            for j in range(0,d):
                SSe[:] += (Y[:,i,j] - Mr[:,i] - Mp[:,j] + Mrp)**2.0
        
        # Mean square over participants (nvox)
        MSp = SSp / (n - 1.0)
        
        # Mean square error (nvox)
        MSe = SSe / ((n - 1.0) * (d - 1.0))

        # ICC_c (nvox x 1)
        print('  Intraclass Correlation Coefficient (ICC_c)')
        ICC = (MSp - MSe) / (MSp + (d - 1.0) * MSe)
        
        # Replace NaNs and negative ICCs with 0.0
        ICC[np.where(np.isnan(ICC))] = 0.0
        ICC[np.where(ICC < 0.0)] = 0.0
        
        # Write results to output directory
        suffix = '_%04d.nii.gz' % ic
        print('  Saving ICC'+suffix)
        
        ICC_nii = nib.Nifti1Image(np.reshape(ICC, [nx,ny,nz]), ic_nii.get_affine())
        ICC_nii.to_filename(os.path.join(icc_dir, 'ICC'+suffix))
        
        # Masked statistics
        if args.mask:
            
            # Setup mask and masked ICC array on first pass
            if ic == 0:
                mask_vox = np.reshape(mask,[nvox])         
                nmask = mask_vox.sum()
                ICC_mask = np.zeros([nmask, nic])
            
            ICC_mask[:,ic] = ICC[mask_vox]

    # Sample 10% of voxels in ICC_mask and export
    if args.mask:
        
        # Random mask voxel indices
        nsamp = int(nmask/10.0)
        print('Sampling %d voxels from mask' % nsamp)
        mask_samp = random.sample(range(0, nmask), nsamp)
        
        # Extract sample from masked ICC array
        ICC_samp = ICC_mask[mask_samp,:]
        
        # Export array to CSV vile
        csv_fname = os.path.join(icc_dir,'ICC_mask_%d.csv' % nsamp)
        np.savetxt(csv_fname, ICC_samp, delimiter=',')

    # Clean exit
    sys.exit(0)


# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()



"""Extract possible insertions from alignments to fit logistic regression."""

import json
import os

import numpy as np
import pandas as pd
import scipy.ndimage as ndimage
import skbio
from src.ortho_MSA.trim import get_segments

# Load parameters
with open('../config/trim_params.json') as file:
    tp = json.load(file)
matrix = {}
with open('../config/BLOSUM62.txt') as file:
    file.readline()  # Skip header
    syms = file.readline().split()
    for i, line in enumerate(file):
        for j, value in enumerate(line.split()[1:]):
            matrix[(syms[i], syms[j])] = int(value)

OGids = ['4bb0', '13ff', '15e6', '39c2', '3f97', '1417', '1832', '06ef',
         '08a3', '0de5', '2cf5', '3ab1', '07cc', '4859', '4044', '423b',
         '2fdd', '146e', '455f', '4b3b', '3b4b', '0a5f', '1f35', '2fa4']

rows = []
for OGid in OGids:
    try:
        msa = skbio.read(f'../align_fastas1/out/{OGid}.mfa',
                         format='fasta', into=skbio.TabularMSA, constructor=skbio.Protein)
    except FileNotFoundError:
        msa = skbio.read(f'../align_fastas2-2/out/{OGid}.mfa',
                         format='fasta', into=skbio.TabularMSA, constructor=skbio.Protein)

    scores = np.zeros(msa.shape[1])
    for i, col in enumerate(msa.iter_positions()):
        scores[i] = col.count('-')

    mask = ndimage.label(len(msa) - scores <= tp['gap_num'])[0]
    regions = [region for region, in ndimage.find_objects(mask)]
    for region in regions:
        for segment in get_segments(msa, region, matrix):
            d = {'OGid': OGid, 'start': segment['region'].start, 'stop': segment['region'].stop, 'index': segment['index'],
                 'length': sum([s.stop-s.start for s in segment['slices']])}
            rows.append(d)

if not os.path.exists('out/'):
    os.mkdir('out/')

df = pd.DataFrame(rows).sort_values(by=['OGid', 'stop', 'length'], ascending=[True, True, False])
df.to_csv('out/segments.tsv', sep='\t', index=False)

"""
DEPENDENCIES
../config/BLOSUM62.txt
../config/trim_params.json
../align_fastas1/align_fastas1.py
    ../align_fastas1/out/*.mfa
../align_fastas2-2/align_fastas2-2.py
    ../align_fastas2-2/out/*.mfa
"""
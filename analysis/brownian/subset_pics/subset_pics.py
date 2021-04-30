"""Create list of segments and features corresponding to the PICs."""

import os
import pandas as pd

# Input variables
seg_path = '../segment_avg/out/segment_avg.tsv'
feature_path = '../feature_calc/out/features.tsv'
pic_path = '../pic_calc/out/pics.tsv'

# Read data
segs = pd.read_csv(seg_path, sep='\t', keep_default_na=False)
features = pd.read_csv(feature_path, sep='\t', index_col=list(range(5)))
pics = pd.read_csv(pic_path, sep='\t', index_col=list(range(3)))

if not os.path.exists('out/'):
    os.mkdir('out/')

# Filter segments
idx = segs['block_id'].isin(pics.index.unique('block_id'))
segs_pics = segs.loc[idx, :]
segs_pics.to_csv('out/segments.tsv', sep='\t')

# Filter features
idx = features.index.get_level_values('block_id').isin(pics.index.unique('block_id'))
features_pics = features.loc[idx, :]
features_pics.to_csv('out/features.tsv', sep='\t')

print('blocks in filtered segments:', len(segs_pics['block_id'].unique()))
print('blocks in filtered features:', len(features_pics.index.unique('block_id')))
print('blocks in pics:', len(pics.index.unique('block_id')))

"""
OUTPUT
blocks in filtered segments: 37016
blocks in filtered features: 37016
blocks in pics: 37016

NOTES
Some blocks do not have full sets of contrasts since one or more species may have an empty sequence within those bounds.
    This script creates a list of segments and features corresponding to the PICs for analysis of the original sequences.

DEPENDENCIES
../pic_calc/pic_calc.py
    ../pic_calc/out/pics.tsv
../segment_avg/segment_avg.py
    ../segment_avg/out/segment_avg.tsv
../feature_calc/feature_calc.py
    ../feature_calc/out/features.tsv
"""
"""Calculate gap contrasts between alignments."""

import os
import re

import numpy as np
import skbio
from src.utils import read_fasta


def get_contrasts(node):
    child1, child2 = node.children
    if child1.is_tip():
        contrasts1, val1, bl1 = [], child1.value, child1.length
    else:
        contrasts1, val1, bl1 = get_contrasts(child1)
    if child2.is_tip():
        contrasts2, val2, bl2 = [], child2.value, child2.length
    else:
        contrasts2, val2, bl2 = get_contrasts(child2)

    bl_sum = bl1 + bl2
    value = (val1 * bl2 + val2 * bl1) / bl_sum
    branch_length = node.length + bl1 * bl2 / bl_sum
    contrasts = contrasts1 + contrasts2
    contrasts.append((val1 - val2) / bl_sum)

    return contrasts, value, branch_length


ppid_regex = r'ppid=([A-Za-z0-9_]+)'
spid_regex = r'spid=([a-z]+)'

# Load tree
tree_template = skbio.read('../../ortho_tree/consensus_LG/out/100R_NI.nwk', 'newick', skbio.TreeNode)
spids = {tip.name for tip in tree_template.tips() if tip.name != 'sleb'}

# Load regions
regions = []
with open('../aucpred_filter/out/regions_30.tsv') as file:
    field_names = file.readline().rstrip('\n').split('\t')
    for line in file:
        fields = {key: value for key, value in zip(field_names, line.rstrip('\n').split('\t'))}
        regions.append((fields['OGid'], int(fields['start']), int(fields['stop']), set(fields['ppids'].split(','))))

# Calculate contrasts
total_records, sum_records = [], []
for OGid, start, stop, ppids in regions:
    msa = {}
    for header, seq in read_fasta(f'../../../data/alignments/fastas/{OGid}.afa'):
        ppid = re.search(ppid_regex, header).group(1)
        spid = re.search(spid_regex, header).group(1)
        if ppid in ppids:
            msa[spid] = seq[start:stop]

    tree = tree_template.deepcopy().shear(msa.keys())
    for tip in tree.tips():
        gap_vector = np.asarray([1 if sym == '-' else 0 for sym in msa[tip.name]])
        tip.value = gap_vector
    tree.length = 0  # Set root length to 0 for convenience

    contrasts, _, _ = get_contrasts(tree)
    gap_matrix = np.asarray([[0 if sym == '-' else 1 for sym in seq] for seq in msa.values()])
    len1 = gap_matrix.shape[1]  # Total length of alignment
    len2 = (gap_matrix / len(msa)).sum()  # Adjusted length of alignment
    total_records.append([OGid, start, stop, len(msa), len1, len2, np.abs(contrasts).sum()])
    if len(msa) == len(spids):
        row_sums = list(np.abs(contrasts).sum(axis=1))
        sum_records.append([OGid, start, stop, len1, len2, *row_sums])

# Write contrasts to file
if not os.path.exists('out/'):
    os.mkdir('out/')

with open('out/total_sums.tsv', 'w') as file:
    file.write('OGid\tstart\tstop\tgnidnum\tlen1\tlen2\ttotal\n')
    for total_record in total_records:
        file.write('\t'.join([str(field) for field in total_record]) + '\n')
with open('out/row_sums.tsv', 'w') as file:
    file.write('OGid\tstart\tstop\tlen1\tlen2\t' + '\t'.join([f'row{i}' for i in range(len(spids)-1)]) + '\n')
    for sum_record in sum_records:
        file.write('\t'.join([str(field) for field in sum_record]) + '\n')

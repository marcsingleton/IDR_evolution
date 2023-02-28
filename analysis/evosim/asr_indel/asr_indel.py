"""Infer ancestral indel states of IDRs."""

import os
import re
from collections import Counter
from subprocess import run

import scipy.ndimage as ndimage
import skbio
from src.utils import read_fasta


def is_nested(character, characters):
    """Return if character is nested in one of intervals in characters."""
    start1, stop1 = character
    for start2, stop2 in characters:
        if (start2 <= start1) and (stop2 >= stop1):
            return True
    return False


ppid_regex = r'ppid=([A-Za-z0-9_.]+)'
spid_regex = r'spid=([a-z]+)'
min_length = 30
min_seqs = 20
tree_template = skbio.read('../../../data/trees/consensus_LG/100R_NI.nwk', 'newick', skbio.TreeNode)

OGid2regions = {}
with open('../../IDRpred/get_regions/out/regions.tsv') as file:
    field_names = file.readline().rstrip('\n').split('\t')
    for line in file:
        fields = {key: value for key, value in zip(field_names, line.rstrip('\n').split('\t'))}
        OGid, start, stop, disorder = fields['OGid'], int(fields['start']), int(fields['stop']), fields['disorder'] == 'True'
        try:
            OGid2regions[OGid].append((start, stop, disorder))
        except KeyError:
            OGid2regions[OGid] = [(start, stop, disorder)]

if not os.path.exists('out/'):
    os.mkdir('out/')

for OGid, regions in OGid2regions.items():
    # Load MSA
    msa = []
    for header, seq in read_fasta(f'../../../data/alignments/fastas/{OGid}.afa'):
        ppid = re.search(ppid_regex, header).group(1)
        spid = re.search(spid_regex, header).group(1)
        msa.append({'ppid': ppid, 'spid': spid, 'seq': seq})

    # Check regions (continuing only if alignment is fit by asr_aa.py)
    disorder_lengths = []
    order_lengths = []
    for record in msa:
        seq = record['seq']
        disorder_seq = ''.join([seq[start:stop] for start, stop, disorder in regions if disorder])
        disorder_counts = Counter(disorder_seq)
        disorder_lengths.append(len(disorder_seq) - disorder_counts['-'] + disorder_counts['.'])

        seq = record['seq']
        order_seq = ''.join([seq[start:stop] for start, stop, disorder in regions if not disorder])
        order_counts = Counter(order_seq)
        order_lengths.append(len(order_seq) - order_counts['-'] + order_counts['.'])

    disorder_condition = sum([disorder_length >= min_length for disorder_length in disorder_lengths]) >= min_seqs
    order_condition = sum([order_length >= min_length for order_length in order_lengths]) >= min_seqs
    if not (disorder_condition or order_condition):
        continue

    # Make list of gaps for each sequence
    ids2characters = {}
    for record in msa:
        ppid, spid, seq = record['ppid'], record['spid'], record['seq']
        binary = [1 if sym in ['-', '.'] else 0 for sym in seq]
        slices = [(s.start, s.stop) for s, in ndimage.find_objects(ndimage.label(binary)[0])]
        ids2characters[(ppid, spid)] = slices
    character_set = set().union(*ids2characters.values())
    character_set = sorted(character_set, key=lambda x: (x[0], -x[1]))  # Fix order of characters

    # Skip region if no indels
    if not character_set:
        continue

    # Make character alignment
    mca = []
    for (ppid, spid), characters in ids2characters.items():
        charseq = []
        for character in character_set:
            if is_nested(character, characters):
                charseq.append('1')
            else:
                charseq.append('0')
        mca.append({'ppid': ppid, 'spid': spid, 'charseq': charseq})
    mca = sorted(mca, key=lambda x: x['spid'])

    # Identify invariant characters
    is_invariants = []
    for j in range(len(mca[0]['charseq'])):
        is_invariant = True
        for i in range(len(mca)):
            if mca[i]['charseq'][j] == '0':
                is_invariant = False
                break
        is_invariants.append(is_invariant)

    # Write character table to file
    character_id = 0
    with open(f'out/{OGid}.tsv', 'w') as file:
        file.write('character_id\tstart\tstop\n')
        for is_invariant, (start, stop) in zip(is_invariants, character_set):
            if is_invariant:
                file.write(f'-1\t{start}\t{stop}\n')
            else:
                file.write(f'{character_id}\t{start}\t{stop}\n')
                character_id += 1

    # Write alignment to file
    with open(f'out/{OGid}.afa', 'w') as file:
        for record in mca:
            ppid, spid, charseq = record['ppid'], record['spid'], record['charseq']
            charseq = [sym for is_invariant, sym in zip(is_invariants, charseq) if not is_invariant]  # Filter invariant characters
            seqstring = '\n'.join([''.join(charseq[i:i+80]) for i in range(0, len(charseq), 80)])
            file.write(f'>{spid} {ppid}\n{seqstring}\n')

    # Prune missing species from tree
    spids = {record['spid'] for record in msa}
    tree = tree_template.shear(spids)
    skbio.io.write(tree, format='newick', into=f'out/{OGid}.nwk')

    cmd = (f'../../../bin/iqtree -s out/{OGid}.afa '
           f'-m GTR2+FO+G+ASC -keep-ident '
           f'-t out/{OGid}.nwk -blscale '
           f'-pre out/{OGid}')
    run(cmd, shell=True, check=True)

"""
NOTES
Test reconstructions showed that treating every character as independent underestimates the probability of gaps. I
believe the issue is if a region with consistent gaps has "ragged" ends, each gap with a unique start or stop position
is coded as a separate character. In the most extreme case, a gap common to every sequence but one may differ by at
least one at each stop position, like a staircase. Thus, the nested structure of the gaps is not reflected in the
character codings.
"""
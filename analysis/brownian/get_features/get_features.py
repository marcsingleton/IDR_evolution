"""Calculate features of segments in regions."""

import multiprocessing as mp
import os
import re
from collections import namedtuple

import features
from src.utils import read_fasta


Record = namedtuple('Record', ['OGid', 'start', 'stop', 'ppid', 'disorder', 'segment'])


def get_features(record):
    d = {'OGid': record.OGid, 'start': record.start, 'stop': record.stop, 'ppid': record.ppid}
    if not (len(record.segment) == 0 or 'X' in record.segment or 'U' in record.segment):
        d.update(features.get_features(record.segment))
    return d


num_processes = int(os.environ['SLURM_CPUS_ON_NODE'])
ppid_regex = r'ppid=([A-Za-z0-9_]+)'

if __name__ == '__main__':
    # Load regions
    OGid2regions = {}
    with open('../aucpred_regions/out/regions.tsv') as file:
        field_names = file.readline().rstrip('\n').split('\t')
        for line in file:
            fields = {key: value for key, value in zip(field_names, line.rstrip('\n').split('\t'))}
            OGid, start, stop, disorder = fields['OGid'], int(fields['start']), int(fields['stop']), fields['disorder']
            try:
                OGid2regions[OGid].append((start, stop, disorder))
            except KeyError:
                OGid2regions[OGid] = [(start, stop, disorder)]

    # Extract segments
    args = []
    for OGid, regions in OGid2regions.items():
        msa = read_fasta(f'../../ortho_MSA/insertion_trim/out/{OGid}.afa')
        msa = {re.search(ppid_regex, header).group(1): seq for header, seq in msa}

        for start, stop, disorder in regions:
            for ppid, seq in msa.items():
                segment = seq[start:stop].translate({ord('-'): None, ord('.'): None}).upper()
                args.append(Record(OGid, start, stop, ppid, disorder, segment))

    # Calculate features
    with mp.Pool(processes=num_processes) as pool:
        records = pool.map(get_features, args, chunksize=50)

    # Write features to file
    if not os.path.exists('out/'):
        os.mkdir('out/')

    with open('out/features.tsv', 'w') as file:
        if records:
            header = records[0]
            file.write('\t'.join(header) + '\n')
        for record in records:
            file.write('\t'.join(str(record.get(field, 'nan')) for field in header) + '\n')

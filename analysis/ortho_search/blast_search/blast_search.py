"""BLAST all-against-all using annotated Drosophila protein sequences and databases."""

import os
from subprocess import run
from sys import argv
from time import asctime

num_threads = os.environ['SLURM_CPUS_ON_NODE']
query_spid = argv[1]
prot_path = argv[2]
blast_path = argv[3]

# Load genomes
spids = []
with open('../config/genomes.tsv') as file:
    file.readline()  # Skip header
    for line in file:
        spids.append(line.rstrip('\n').split('\t')[0])

if not os.path.exists(f'out/{query_spid}/'):
    os.makedirs(f'out/{query_spid}/')

# Execute BLASTs
for subject_spid in spids:
    if os.path.exists(f'out/{query_spid}/{subject_spid}.blast'):
        continue

    # Generate args
    input_args = [blast_path, '-query', prot_path]
    output_args = ['-out', f'out/{query_spid}/{subject_spid}.blast']
    search_args = ['-db', f'../blast_makedbs/out/{subject_spid}_blastdb', '-evalue', '1', '-num_threads', num_threads]
    format_args = ['-outfmt', '7 qacc sacc length nident gaps qlen qstart qend slen sstart send evalue bitscore']

    # Execute command
    t0 = asctime()
    run(input_args + output_args + search_args + format_args, check=True)
    t1 = asctime()

    # Manually write output to file since direction while in background does not immediately write to file
    with open('out/blast_search.out', 'a') as file:
        file.write(f'{query_spid}\t{subject_spid}\t{t0}\t{t1}\n')

"""
DEPENDENCIES
../config/genomes.tsv
../blast_makedbs/blast_makedbs.sh
    ../blast_makedbs/out/*
../remove_duplicates/remove_duplicates.py
    ../remove_duplicates.out/*.fa
"""
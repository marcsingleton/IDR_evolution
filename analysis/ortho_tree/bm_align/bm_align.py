"""Align BAliBase sequences."""

import multiprocessing as mp
import os
import re
from subprocess import run
from time import time_ns


def run_cmd(aligner, ref, file_id, cmd):
    t0 = time_ns()
    run(cmd, shell=True, check=True)
    t1 = time_ns()

    return aligner, ref, file_id, str(t1-t0)


num_processes = int(os.environ['SLURM_NTASKS'])
bin_path = '../../../bin/'
data_path = '../../../data/bb3_release/'

if __name__ == '__main__':
    # Make list of commands
    cmds = []
    for ref in ['11', '12', '20', '30', '40', '50']:
        regex = f'(BB{ref}' + r'[0-9]{3}).tfa'
        for file in os.listdir(f'../../../data/bb3_release/RV{ref}/'):
            match = re.match(regex, file)
            if match:
                file_id = match.group(1)

                aligners = {'mafft': f'{bin_path}mafft --genafpair --maxiterate 1000 --thread 1 '
                                     f'{data_path}RV{ref}/{file_id}.tfa '
                                     f'1> out/mafft/RV{ref}/{file_id}.mfa 2> out/mafft/RV{ref}/{file_id}.err',
                            'probalign': f'{bin_path}probalign {data_path}RV{ref}/{file_id}.tfa '
                                         f'1> out/probalign/RV{ref}/{file_id}.mfa 2> out/probalign/RV{ref}/{file_id}.err',
                            'probcons': f'{bin_path}probcons {data_path}RV{ref}/{file_id}.tfa '
                                        f'1> out/probcons/RV{ref}/{file_id}.mfa 2> out/probcons/RV{ref}/{file_id}.err',
                            't_coffee': f'{bin_path}t_coffee {data_path}RV{ref}/{file_id}.tfa '
                                        f'-thread=1 -newtree=out/t_coffee/RV{ref}/{file_id}.dnd '
                                        f'-output=fasta_aln -outfile=out/t_coffee/RV{ref}/{file_id}.mfa '
                                        f'&> out/t_coffee/RV{ref}/{file_id}.err',
                            **{f'clustalo{i}': f'{bin_path}clustalo -i {data_path}RV{ref}/{file_id}.tfa '
                                               f'--iterations {i} --threads=1 '
                                               f'-o out/clustalo{i}/RV{ref}/{file_id}.mfa' for i in range(1, 4)}}

                for aligner, cmd in aligners.items():
                    if not os.path.exists(f'out/{aligner}/RV{ref}/'):
                        os.makedirs(f'out/{aligner}/RV{ref}/')

                    cmds.append((aligner, ref, file_id, cmd))

    # Run commands
    with mp.Pool(processes=num_processes) as pool:
        rows = pool.starmap(run_cmd, cmds)

    # Save results
    with open('out/times.tsv', 'w') as file:
        file.write('aligner\tref\tfile_id\ttime_ns\n')
        for row in rows:
            file.write('\t'.join(row) + '\n')

"""
DEPENDENCIES
../../../data/bb3_release/
"""
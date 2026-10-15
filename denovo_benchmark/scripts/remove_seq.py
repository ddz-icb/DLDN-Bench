"""
Write the benchmark MGF without the SEQ field, as input for PepNovo+ (ported from De_novo_eval.ipynb).

Usage:
    python remove_seq.py input.mgf output.mgf
"""
import sys

from pyteomics import mgf


def change_spectra_seq(mgf_file):
    for spectrum in mgf_file:
        spectrum['params'].pop('seq')
        yield spectrum


if __name__ == '__main__':
    with open(sys.argv[2], 'w') as out_file:
        mgf.write(change_spectra_seq(mgf.IndexedMGF(sys.argv[1])), out_file)

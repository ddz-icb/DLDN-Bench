"""
Draw a random subset of N spectra from an MGF file (N = 0: all spectra), copying the spectra unchanged.

Writes two files:
- subset MGF: the selected spectra (in their original order), used by the de novo tools and the evaluation
- search MGF: the selected spectra followed by all other spectra, used for the MS-GF+ search. Percolator needs the
  complete dataset, and the evaluation matches the MS-GF+ PSMs by their position in the searched file, so the
  selected spectra have the same positions in both files.

Usage:
    python subset_mgf.py input.mgf subset.mgf search.mgf N SEED
"""
import random
import sys


def read_spectra(path):
    spectra, block = [], []
    with open(path) as f:
        for line in f:
            block.append(line)
            if line.startswith('END IONS'):
                spectra.append(''.join(block))
                block = []
    return spectra


if __name__ == '__main__':
    input_mgf, subset_mgf, search_mgf, n_spectra, seed = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
    spectra = read_spectra(input_mgf)
    if n_spectra and n_spectra < len(spectra):
        selected = sorted(random.Random(seed).sample(range(len(spectra)), n_spectra))
    else:
        selected = list(range(len(spectra)))
    selected_set = set(selected)
    with open(subset_mgf, 'w') as f:
        f.writelines(spectra[i] for i in selected)
    with open(search_mgf, 'w') as f:
        f.writelines(spectra[i] for i in selected)
        f.writelines(s for i, s in enumerate(spectra) if i not in selected_set)
    print(f'Selected {len(selected)} of {len(spectra)} spectra (seed {seed})')

"""
Create an annotated benchmark MGF from the Percolator results of Comet and MSFragger.

Keeps PSMs with q-value < 0.01 in both searches and only the spectra where both search engines identified the same
peptide (same file, scan and peptide sequence incl. modifications). The peptide is written to the SEQ field of the
spectrum in the format of the de novo tools (e.g. M+15.995, +42.011PEPTIDE).

Ported from Create_benchmark_datasets.ipynb, which was used to create the published benchmark datasets.

Usage:
    python create_benchmark_mgf.py --comet comet_perc_*.xml --msfragger msfragger_perc_*.xml \
        --mgf-dir /path/to/converted/mgfs --output PXD043425_benchmark_dataset.mgf [--venn venn.png]
"""
import argparse
import os
import re

import pandas as pd
from lxml import etree
from pyteomics import mgf

Q_VALUE_THRESHOLD = 0.01
NS = '{http://per-colator.com/percolator_out/15}'

# Modification masses as written by Comet/MSFragger -> unified names (used for matching both search engines)
search_engine_modification_dict = {'15.9949': 'Oxidation',
                                   '42.0106': 'Acetyl',
                                   '57.0215': 'Carbamidomethyl'}

# Unified names -> format of the de novo tools
de_novo_modification_dict = {'Oxidation': '+15.995',
                             'Acetyl': '+42.011',
                             'Carbamidomethyl': '+57.021',
                             'Met-loss': '',                 # Met-loss is considered by removing the M-residue of the peptide sequence
                             'Met-loss+Acetyl': '+42.011'}   # Same for this case


def parse_percolator_xml(xml_file):
    """Read the PSMs of a Percolator XML output file."""
    root = etree.parse(xml_file).getroot()
    data = []
    for psm in root.findall(f'.//{NS}psm'):
        peptide = psm.find(f'.//{NS}peptide_seq')
        n_term = peptide.get('n') or '-'
        c_term = peptide.get('c') or '-'
        data.append({'psm_id': psm.get(f'{NS}psm_id'),
                     'q_value': float(psm.findtext(f'{NS}q_value') or 0),
                     'peptide_seq': f"{n_term}.{peptide.get('seq')}.{c_term}"})
    return pd.DataFrame(data, columns=['psm_id', 'q_value', 'peptide_seq'])


def read_filtered_psms(xml_files):
    """Read and concatenate the PSMs with q-value < 0.01 of several Percolator XML files."""
    dfs = []
    for xml_file in xml_files:
        df = parse_percolator_xml(xml_file)
        df = df[df['psm_id'].notnull() & df['peptide_seq'].notnull() & (df['q_value'] < Q_VALUE_THRESHOLD)]
        print(f'{os.path.basename(xml_file)}: {len(df)} PSMs with q-value < {Q_VALUE_THRESHOLD}')
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


def extract_filename_and_scan(df, search_engine):
    """Add the spectrum file name and scan number encoded in the psm_id."""
    df = df.copy()
    if search_engine == 'comet':
        # e.g. /path/to/29052019_C18P_7856_AT18_basal_2h_DDA_1_39132_3_1 (file_scan_charge_rank)
        parts = df['psm_id'].str.extract(r'(?:.*/)?([^/]+?)_(\d+)_\d+_\d+$')
        df['filename'], df['extracted_scannr'] = parts[0], parts[1]
    else:
        # e.g. 29052019_C18P_7856_AT18_basal_2h_DDA_1.45973.45973.4_1 (file.scan.scan.charge_rank)
        df['filename'] = df['psm_id'].apply(lambda x: x.split('.')[0])
        df['extracted_scannr'] = df['psm_id'].apply(lambda x: x.split('.')[-3] if len(x.split('.')) >= 3 else None)
    return df


def unify_modifications(df, search_engine):
    """Write the peptides of both search engines in the same format, e.g. C[Carbamidomethyl], M[Oxidation]."""
    df = df.copy()
    modified_seqs = []
    for seq in df['peptide_seq']:
        seq = re.sub(r'[a-z]', '', seq)
        modified_seq = seq

        # Comet does not write the fixed carbamidomethylation into the peptide sequence
        if search_engine == 'comet':
            modified_seq = modified_seq.replace('C', 'C[Carbamidomethyl]')

        # Handle Met-loss and Met-loss+Acetyl cases
        if seq.startswith('M.'):
            next_char = seq.split('.', 1)[1][0] if '.' in seq else ''
            if next_char != 'M':
                if seq.startswith('M.[42.0106]'):
                    modified_seq = 'M.[Met-loss+Acetyl]' + seq[11:]
                else:
                    modified_seq = 'M.[Met-loss]' + seq[2:]

        for match in re.findall(r'\[(.*?)\]', modified_seq):
            if match in search_engine_modification_dict:
                modified_seq = modified_seq.replace(f'[{match}]', f'[{search_engine_modification_dict[match]}]')

        modified_seqs.append(modified_seq)

    # Keep only the peptide sequence (between the flanking residues)
    df['peptide_seq'] = [x.split('.', 1)[1].split('.')[0] if '.' in x else x for x in modified_seqs]
    return df


def to_de_novo_format(seq):
    for match in re.findall(r'\[(.*?)\]', seq):
        if match in de_novo_modification_dict:
            seq = seq.replace(f'[{match}]', de_novo_modification_dict[match])
    return seq


def intersect_search_engines(comet_df, msfragger_df):
    """Spectra identified with the same peptide by both search engines."""
    comet_df = unify_modifications(extract_filename_and_scan(comet_df, 'comet'), 'comet')
    msfragger_df = unify_modifications(extract_filename_and_scan(msfragger_df, 'msfragger'), 'msfragger')
    keys = ['filename', 'extracted_scannr', 'peptide_seq']
    intersection = pd.merge(comet_df, msfragger_df, on=keys, how='inner')
    return comet_df, msfragger_df, intersection


def select_spectra(intersection, mgf_dir):
    index = 1
    for filename, group in intersection.groupby('filename'):
        mgf_file = mgf.IndexedMGF(os.path.join(mgf_dir, f'{filename}.mgf'), use_header=True,
                                  label=r'TITLE=.*scan=(\d+)\s*')
        for _, row in group.iterrows():
            spectrum = mgf_file[row['extracted_scannr']]
            spectrum['params']['SEQ'] = to_de_novo_format(row['peptide_seq'])
            spectrum['params']['SCANS'] = index  # avoid duplicate scan numbers, so assign new ones
            index += 1
            yield spectrum


def plot_venn(n_comet, n_msfragger, n_both, output_file):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib_venn import venn2

    plt.figure(figsize=(8, 8))
    venn2(subsets=(n_comet - n_both, n_msfragger - n_both, n_both), set_labels=('Comet', 'MSFragger'))
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--comet', nargs='+', required=True, help='Percolator XML files of the Comet search')
    parser.add_argument('--msfragger', nargs='+', required=True, help='Percolator XML files of the MSFragger search')
    parser.add_argument('--mgf-dir', required=True, help='Directory with the converted MGF files')
    parser.add_argument('--output', required=True, help='Output benchmark MGF file')
    parser.add_argument('--venn', help='Optional output path of a Venn diagram of the PSM overlap')
    args = parser.parse_args()

    comet_df, msfragger_df, intersection = intersect_search_engines(read_filtered_psms(args.comet),
                                                                    read_filtered_psms(args.msfragger))
    print(f'PSMs: Comet {len(comet_df)}, MSFragger {len(msfragger_df)}, both {len(intersection)}')

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, 'w') as out_file:
        mgf.write(select_spectra(intersection, args.mgf_dir), out_file)
    print(f'Benchmark dataset with {len(intersection)} spectra written to {args.output}')

    if args.venn:
        plot_venn(len(comet_df), len(msfragger_df), len(intersection), args.venn)

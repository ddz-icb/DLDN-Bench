"""
Convert the Percolator XML output of the MS-GF+ search into the parquet file expected by create_result_csv.py.

Keeps all target PSMs (no q-value filter), as for the published datasets. Note: the parser originally used
(De_novo_eval.ipynb) read the PSMs on the start event of each XML element and therefore dropped ~1.4% of the
PSMs whose content was not yet parsed at that point; this parser reads complete elements.

Usage:
    python percolator_to_parquet.py percolator.xml output.parquet
"""
import sys

import pandas as pd
from lxml import etree

NS = '{http://per-colator.com/percolator_out/15}'


def parse_percolator_xml(xml_file):
    data = []
    for psm in etree.parse(xml_file).getroot().iter(f'{NS}psm'):
        peptide = psm.find(f'{NS}peptide_seq')
        peptide_seq = None
        if peptide is not None:
            peptide_seq = f"{peptide.get('n', '-')}.{peptide.get('seq')}.{peptide.get('c', '-')}"
        data.append({
            'psm_id': psm.get(f'{NS}psm_id'),
            'svm_score': float(psm.findtext(f'{NS}svm_score') or 0),
            'q_value': float(psm.findtext(f'{NS}q_value') or 0),
            'pep': float(psm.findtext(f'{NS}pep') or 0),
            'exp_mass': float(psm.findtext(f'{NS}exp_mass') or 0),
            'calc_mass': float(psm.findtext(f'{NS}calc_mass') or 0),
            'peptide_seq': peptide_seq,
            'protein_ids': [p.text for p in psm.findall(f'{NS}protein_id')],
            'p_value': float(psm.findtext(f'{NS}p_value') or 0),
        })
    return pd.DataFrame(data)


if __name__ == '__main__':
    df = parse_percolator_xml(sys.argv[1])
    df = df[df['psm_id'].notnull() & df['psm_id'].str.contains('target') & df['peptide_seq'].notnull()]
    df.to_parquet(sys.argv[2], compression='gzip')
    print(f'Wrote {len(df)} target PSMs to {sys.argv[2]}')

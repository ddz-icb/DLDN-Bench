# Benchmark dataset creation workflow

Snakemake workflow that creates an annotated benchmark dataset (MGF) from a PRIDE dataset, as used for the published benchmark datasets:

1. **Download** the raw files from PRIDE (via the PRIDE API, HTTPS)
2. **Convert** them to MGF with ProteoWizard msconvert (container, run with Apptainer)
3. **Search** them with Comet and MSFragger against the human reference proteome
4. **Rescore** each search with Percolator
5. **Intersect**: keep spectra identified with the same peptide by both search engines (q-value < 0.01) and write them with the peptide in the `SEQ` field

## Requirements

- Linux (or WSL2 on Windows) with [Apptainer](https://apptainer.org) (runs the Windows msconvert in a container; macOS is not supported)
- [conda](https://docs.conda.io)
- MSFragger 4.0 (`MSFragger-4.0.jar`), which has to be downloaded manually after accepting its academic license: https://msfragger.nesvilab.org
- ~5 GB disk space for the msconvert container plus ~3 GB per raw file

## Protein database

The protein database used for the published datasets is included in [`database/`](database/): the UniProt human reference proteome UP000005640 (all entries, downloaded 2024-01-10) from [UniProt](https://www.uniprot.org), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Comet generates its decoys internally; for MSFragger the workflow creates a target-decoy database (reversed proteins with prefix `XXX_`, in the format created by MS-GF+), which is identical to the one used for the published datasets.

## Usage

```bash
conda env create -f benchmark_creation/environment.yml
conda activate De_novo_benchmark_creation

# copy and edit the config: accession, raw files (empty = all), FASTA and MSFragger paths
cp benchmark_creation/config.yaml /path/to/run_dir/config.yaml

snakemake -s benchmark_creation/Snakefile --configfile /path/to/run_dir/config.yaml --directory /path/to/run_dir --cores 16
```

The result is written to `results/{accession}_benchmark_dataset.mgf` in the run directory, together with a Venn diagram of the search engine overlap. Finished steps are not rerun when the workflow is restarted.

The default `config.yaml` processes two raw files of PXD043425 (one basal, one insulin-stimulated), which takes about 15 minutes on a 16-core machine.

## Tool versions and parameters

| Step | Tool | Parameters |
|---|---|---|
| Conversion | ProteoWizard msconvert 3.0.25034 (container) | MGF, 64-bit, zlib, TPP compatible titles, vendor peak picking on all MS levels |
| Search | Comet 2023.01 rev. 2 | [`params/comet.params`](params/comet.params) |
| Search | MSFragger 4.0 | [`params/closed_fragger.params`](params/closed_fragger.params) |
| Rescoring | Percolator 3.06.5 | default settings, one run per raw file |

## Reproducibility

Running the workflow on the two default raw files of PXD043425 reproduced 33,227 of the 33,229 published benchmark spectra of these files, all with identical peptide annotation and peak lists. Small differences remain because:

- Comet reports, for peptides occurring in several proteins, the flanking residue of an arbitrary protein when running multi-threaded. This affects the detection of N-terminal methionine loss for a few PSMs (about 0.03%).
- MSFragger (`calibrate_mass = 2`) optimises some search parameters on all files searched together, so results can differ slightly depending on which raw files are processed.
- The published datasets were converted with msconvert 3.0.25011 (MSConvertGUI on Windows); no container exists for this version. Version 3.0.25034 produces identical spectra (m/z values differ by at most 10⁻⁶).

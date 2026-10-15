# De novo benchmark workflow

Snakemake workflow that runs all tools of the benchmark on an annotated benchmark dataset with the settings of the published benchmark, and evaluates their predictions with the evaluation scripts of this repository:

1. **Database search**: MS-GF+ (separate target and decoy search) and Percolator
2. **De novo sequencing**: PepNovo+, Novor, Casanovo, InstaNovo, ContraNovo and π-HelixNovo
3. **Evaluation**: alignment of all predictions (`create_result_csv.py`) and precision-coverage curves with AUCs (`calc_and_plot_precision_coverage.py`)

The input is an annotated benchmark dataset (MGF with `SEQ` field), e.g. created from a PRIDE dataset with the [`benchmark_creation`](../benchmark_creation/README.md) workflow or downloaded from [Zenodo](https://doi.org/10.5281/zenodo.18213582). Together, both workflows cover the complete benchmark from the raw data to the evaluation.

## Requirements

- Linux (or WSL2 on Windows) with [conda](https://docs.conda.io)
- An NVIDIA GPU for the deep learning models (4 GB of GPU memory are sufficient)
- ~40 GB disk space for the tool environments and models

All tools, model weights and the protein database are installed or downloaded automatically from their official sources and verified by MD5 checksums; no manual downloads are required.

## Usage

```bash
conda env create -f denovo_benchmark/environment.yml
conda activate De_novo_benchmark

# copy and edit the config: path to the benchmark MGF, dataset name and number of spectra
cp denovo_benchmark/config.yaml /path/to/run_dir/config.yaml

snakemake -s denovo_benchmark/Snakefile --configfile /path/to/run_dir/config.yaml --directory /path/to/run_dir \
    --sdm conda --cores 16 --resources gpu=1
```

`--sdm conda` lets Snakemake create the environments of the tools (`envs/`) on the first run; `--resources gpu=1` runs the GPU tools one after another.

The predictions of all tools are written to `predictions/` (in the formats of the prediction files on Zenodo), the evaluation to `results/`: the aligned predictions (`<dataset>_benchmark_predictions.csv`), the precision-coverage plots and tables and the AUCs (`<dataset>_auc.csv`).

By default, 3,000 randomly selected spectra of the benchmark dataset are evaluated (`n_spectra` and `seed` in the config; `n_spectra: 0` evaluates all spectra). A random selection is used because the spectra of a benchmark dataset are ordered by raw file and search engine confidence, so the first spectra are not representative. The de novo tools are only run on the selected spectra, while MS-GF+ searches the complete benchmark dataset: Percolator needs enough PSMs to train its model, and with only a few thousand benchmark spectra, which are all confidently identified, it stops with "too good separation between target and decoy PSMs".

### Runtime

On a laptop (16 CPU cores, NVIDIA RTX 500 Ada GPU with 4 GB), the default configuration (3,000 spectra of the two-file benchmark dataset of PXD043425) takes about 2.5 hours, plus ~30 minutes for creating the tool environments on the first run. π-HelixNovo and ContraNovo are the slowest tools (~9 and ~3 minutes per 1,000 spectra on this GPU); the complete two-file dataset (33,229 spectra) takes about 8 hours.

## Tools and settings

All tools are run with the versions, models and settings of the published benchmark:

| Tool | Version | Model / settings |
|---|---|---|
| MS-GF+ + Percolator | v2023.01.12 + 3.06 | see `Snakefile` and `params/msgfplus_mods.txt`; target and decoy (reversed proteins) searched separately |
| PepNovo+ | DeNovoGUI 1.16.8 (PepNovo+ build 20101117) | `params/pepnovoplus.par` |
| Novor | DeNovoGUI 1.16.8 (Novor v1.05.0573) | `params/novor.par` |
| Casanovo | 4.3.0 | weights v4.2.0, `params/casanovo.yaml` (default configuration) |
| InstaNovo | 1.1.1 | instanovo-v1.1.0, refinement with instanovoplus-v1.1.0-alpha, greedy search |
| ContraNovo | commit 503fdb3 + `patches/contranovo_503fdb3.patch` | official checkpoint; the patch sets `n_beams = 1` and writes the predictions with per-position scores |
| π-HelixNovo | commit 47983d7 | human-epoch-12-step-550000.ckpt (official weights, Zenodo 10405582), configuration of the repository |

The tool environments in `envs/` pin the package versions of the original runs, which matters for reproducibility: e.g. Casanovo 4.3.0 does not run with current Lightning versions.

## Reproducibility

Each tool was verified by running it on the 33,229 spectra of two raw files of PXD043425 (the default of the `benchmark_creation` workflow) and comparing its predictions with the published predictions of the same spectra:

| Tool | Identical predictions |
|---|---|
| Casanovo | 100% |
| PepNovo+ | 100% (incl. scores) |
| Novor | 100% (incl. scores) |
| π-HelixNovo | 99.98% (first 11,264 spectra) |
| MS-GF+ | 99.77% |
| InstaNovo | 99.64% |
| ContraNovo | 99.28% |

Running the complete workflow with the default configuration (3,000 random spectra of this dataset) reproduces the ranking of the tools of the published PXD043425 results (all 30 raw files), with peptide-level AUCs within ~0.03 of the published values:

| Tool | Peptide AUC (workflow, 3,000 spectra) | Published (PXD043425) |
|---|---|---|
| MS-GF+ with Percolator | 0.999 | 0.999 |
| ContraNovo | 0.907 | 0.882 |
| InstaNovo | 0.854 | 0.820 |
| Casanovo | 0.852 | 0.822 |
| π-HelixNovo | 0.738 | 0.720 |
| Novor | 0.271 | 0.256 |
| PepNovo+ | 0.124 | 0.134 |

In this run, the predictions for the 3,000 spectra were identical to the published predictions for Casanovo and PepNovo+ (100%), Novor (99.97%), MS-GF+ (99.69%), InstaNovo (99.57%), ContraNovo (99.17%) and π-HelixNovo (93.97%).

The remaining differences of the deep learning models are caused by numerical differences between GPUs (the published predictions were computed on NVIDIA L4 and A100 GPUs). The predictions of π-HelixNovo additionally depend on which spectra are processed together in a batch: on the 33,229 spectra in their original order, 99.98% of its predictions were identical, on the random subset 93.97%. These differences concern uncertain predictions and do not affect the evaluation (e.g. 1,101 vs. 1,106 correct π-HelixNovo and 18,263 vs. 18,258 correct ContraNovo peptides). The Percolator scores of MS-GF+ depend on the size of the searched dataset, as Percolator is trained on the dataset itself.

The published MS-GF+ results were read from the Percolator output with a parser that dropped ~1.4% of the PSMs (and thereby the corresponding spectra from the comparison of all tools); the workflow uses a corrected parser (`scripts/percolator_to_parquet.py`).

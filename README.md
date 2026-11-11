# cpu-engineering-samples

**Engineering-sample (ES) CPU catalog** for [GetTechAPI](https://github.com/GetTechAPI).

[![validate-data](https://github.com/GetTechAPI/cpu-engineering-samples/actions/workflows/validate-data.yml/badge.svg)](https://github.com/GetTechAPI/cpu-engineering-samples/actions/workflows/validate-data.yml)
&nbsp;Data: **CC-BY-SA 4.0** · Code: **MIT**

Retail / production CPUs live in [**TechAPI**](https://github.com/GetTechAPI/TechAPI) under `data/cpu/`; this repository holds engineering samples only and publishes its own `summary.json`, which TechAPI's site reads for the record count. Qualification samples (QS) are also out of scope. This repository is a **prototype** holding area for publicly documented ES parts so they never mix into the official catalog.

## Scope

| Belongs here | Belongs in TechAPI |
|---|---|
| Engineering samples (`sample_class: es`) | Retail / production SKUs |
| Intel Q-spec ES, AMD OPN ES | QS / qualification samples |
| Public third-party listings | Official product pages as source of truth |

ES processors are pre-production parts. They are not for sale, not warranted, and this dataset is **not** an Intel or AMD product. Records cite already-public sources only. No NDA material.

## Layout

```text
data/cpu/<manufacturer>/<year>/<segment>/<slug>.json   # one ES record per file
app/validate.py              # stdlib validator; rejects QS/retail
app/ingest/classify.py       # offline es / qs / retail / unknown classifier (python -m app.ingest)
app/ingest/from_table.py     # writes ES records from a local JSON/JSONL table
site/build.py                # writes site/catalog.json, summary.json and history.json
site/index.html              # static index (GitHub Pages)
tests/                       # pytest: validator, classifier, table ingest
.github/workflows/
  validate-data.yml          # validator + tests on PRs and pushes to develop/main
  final-check.yml            # label-triggered check with one TechEngineBot comment
  deploy-pages.yml           # builds site/ and deploys Pages from main
```

The three JSON files under `site/` are build output and are not committed.

Slugs identify the **sample** (`intel-qxlb`, `amd-100-000000665-21-n`), not the retail name. `retail_equivalent` is an optional TechAPI CPU slug string, not a foreign key.

## Self-check

```bash
python -m app.validate
python -m pytest -q
```

The validator uses the Python standard library. QS, retail, and production `sample_class` values fail the build.

## Collection

Intake is **classify-then-write**. A candidate is `es`, `qs`, `retail`, or `unknown`. Only `es` may become a JSON file. QS and retail stay out; `unknown` is for human review.

```bash
python -m app.ingest path/to/candidate.json
```

It prints the classification as JSON and writes nothing. No network. Identifier rules: Intel S-spec → retail, Q-spec + early stepping / low clocks / “Intel Confidential” → es, Q-spec labeled QS or mature stepping with retail clocks → qs. AMD `100-00000…` / Eng Sample → es, historical `Z…` OPN → qs.

To turn a local table into records, run the table ingest:

```bash
python -m app.ingest.from_table path/to/table.json --dry-run
python -m app.ingest.from_table path/to/table.json
```

The table is a JSON array or JSONL, one object per row. Each row is classified; `es` rows are written to `data/cpu/<manufacturer>/<year>/<segment>/<slug>.json` (`year` comes from the row's `year` or `first_seen_date`, `segment` defaults to `desktop`). Rows that classify as `qs`, `retail` or `unknown`, and slugs that already exist, are skipped and listed in the printed summary. `--dry-run` prints the same summary without writing. The exit code is 1 when a row has no usable slug. Run `python -m app.validate` afterwards.

Crawlers come later. This classifier is the gate.

## Branching (git-flow)

| Branch | Role |
|---|---|
| `main` | Released state. Pages deploys from here. |
| `develop` | Integration. Default branch. |
| `feat/*`, `data/*`, `fix/*`, `ci/*`, `docs/*`, `chore/*` | Short-lived branches cut from `develop`. |

A release is a PR from `develop` to `main`. Open work PRs **against `develop`**.

## Final check

A maintainer adds the `final-check` label to an important PR. The `final-check` workflow runs the validator, the tests and the static index build on the PR merged into its base. **TechEngineBot** then leaves one comment with the verdict and the records the PR changes, and adding the label again edits that comment. Only the comment job sees `TECHENGINEBOT_TOKEN`, a fine-grained TechEngineBot token with Pull requests: read and write. Without it, the verdict appears only in the job summary.

## Contributing

Open a PR against `develop` with a new/updated JSON file. `sample_class` must be `es`. Include `qspec` (Intel) and/or `opn` (AMD) and at least one public URL in `source_urls`.

## License

Data is [CC-BY-SA 4.0](DATA_LICENSE.md); attribute "Data from GetTechAPI / cpu-engineering-samples". Validator and site code are [MIT](LICENSE).

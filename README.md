# cpu-engineering-samples

**Engineering-sample (ES) CPU catalog** for [GetTechAPI](https://github.com/GetTechAPI).

[![validate-data](https://github.com/GetTechAPI/cpu-engineering-samples/actions/workflows/validate-data.yml/badge.svg)](https://github.com/GetTechAPI/cpu-engineering-samples/actions/workflows/validate-data.yml)
&nbsp;Data: **CC-BY-SA 4.0** · Code: **MIT**

Retail / production CPUs live in [**TechAPI**](https://github.com/GetTechAPI/TechAPI). Qualification samples (QS) are also out of scope. This repository is a **prototype** holding area for publicly documented ES parts so they never mix into the official catalog.

## Scope

| Belongs here | Belongs in TechAPI |
|---|---|
| Engineering samples (`sample_class: es`) | Retail / production SKUs |
| Intel Q-spec ES, AMD OPN ES | QS / qualification samples |
| Public third-party listings | Official product pages as source of truth |

ES processors are pre-production parts. They are not for sale, not warranted, and this dataset is **not** an Intel or AMD product. Records cite already-public sources only. No NDA material.

## Layout

```text
data/cpu/<manufacturer>/<year>/<segment>/<slug>.json
app/validate.py          # stdlib validator; rejects QS/retail
site/                    # static index (GitHub Pages)
```

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

No network. Identifier rules: Intel S-spec → retail, Q-spec + early stepping / low clocks / “Intel Confidential” → es, Q-spec labeled QS or mature stepping with retail clocks → qs. AMD `100-00000…` / Eng Sample → es, historical `Z…` OPN → qs.

Crawlers come later. This classifier is the gate.

## Branching (git-flow)

| Branch | Role |
|---|---|
| `main` | Released state. Pages deploys from here. |
| `develop` | Integration. Default branch. |
| `feat/*`, `data/*`, `fix/*`, `ci/*`, `docs/*`, `chore/*` | Short-lived branches cut from `develop`. |

A release is a PR from `develop` to `main`. Open work PRs **against `develop`**.

## Contributing

Open a PR against `develop` with a new/updated JSON file. `sample_class` must be `es`. Include `qspec` (Intel) and/or `opn` (AMD) and at least one public `source_url`.

## License

Data is [CC-BY-SA 4.0](DATA_LICENSE.md); attribute "Data from GetTechAPI / cpu-engineering-samples". Validator and site code are [MIT](LICENSE).

<!-- PR title must follow Conventional Commits, e.g. data(cpu): add Intel QXLB ES -->

## What & why

<!-- What does this change and why? Use "Closes #123" for scoped work issues. Do not close the long-running tracker (#1). -->

## Source

<!-- Public source URLs for ES identification (CPU-World, news, benchmark listings). No NDA material. -->

## Checklist

- [ ] `python -m app.validate` passes locally
- [ ] Record `sample_class` is `es` (QS / retail / production are rejected)
- [ ] Files live at `data/cpu/<manufacturer>/<year>/<segment>/<slug>.json`
- [ ] Slugs are kebab-case and unique
- [ ] `source_urls` cites at least one public reference
- [ ] `qspec` (Intel) and/or `opn` (AMD) is present

# Contributing to s1kit

Thanks for helping! Most contributions fit in one evening.

## Good first contributions

- **Provider recipes**: a tested suite snippet for a server we don't document yet.
- **Integrations**: LangChain, LlamaIndex, n8n, Vercel AI SDK.
- **Report formats**: Markdown, JUnit XML, HTML.
- **The GitHub Action** (`action.yml`): new inputs, nicer job summaries.
- **Datasets**: an example suite for a real task (moderation, intent routing, triage).
- **Translations** of the README.

Look for issues labelled `good first issue`.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Keep runtime dependencies to PyYAML only, and add a test with every change.
Open a pull request describing what changed and why.

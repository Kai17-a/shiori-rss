# Specs

This directory is organized by documentation responsibility, not by when a document was created.

## Reading Order

1. [LLM reading guide](./llm-reading-guide.md)
2. [Product requirements](./product/requirements.md)
3. [System design](./architecture/system-design.md)
4. [DB definition](./architecture/data-model.md)
5. Component specs:
   - [API](./components/api/README.md)
   - [Frontend](./components/frontend/README.md)
   - [Batch](./components/batch/README.md)
   - [Browser extension](./components/browser-extension/README.md)
6. [Quality observations](./quality/observations/README.md)

## Directory Roles

| Directory | Role |
| --- | --- |
| `product/` | Product requirements and user-facing behavior |
| `architecture/` | Cross-cutting system design and runtime boundaries |
| `components/` | Implementation-facing specs for each runtime area |
| `quality/` | Test strategy, coverage notes, and observations |

Keep implementation-specific route, schema, flow, and constraint details in the relevant `components/<area>/` directory.

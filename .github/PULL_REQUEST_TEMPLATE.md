## Summary

Briefly describe the change and its rationale.

## Related Issue

Closes #(issue number)

## Type of Change

- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Refactor / Performance improvement
- [ ] Documentation update

## Checklist

- [ ] My change complies with the [AGENTS.md](AGENTS.md) architectural rules.
- [ ] Entities and searchable objects foreign-key to `entity.id`.
- [ ] Mutations trigger `log_event()` when applicable.
- [ ] Alembic migrations have individual SQL statements per `op.execute()`.
- [ ] I have run `make test` locally and all tests pass.
- [ ] I have run `make verify` and code style/type checks pass.
- [ ] `git diff --check` shows no whitespace issues.

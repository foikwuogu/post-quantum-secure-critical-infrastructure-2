# Contributing

Thanks for contributing to this project.

## Local Development

1. Start the stack:

```bash
docker compose up --build
```

2. Validate key endpoints:

- Backend docs: `http://localhost:8100/docs`
- Frontend: `http://localhost:5174`
- Prometheus: `http://localhost:9091`
- Grafana: `http://localhost:3001`

3. Run tests:

```bash
python3 -m pytest tests -q
```

## Branch and Commit Workflow

1. Create a feature branch from `main`.
2. Keep commits focused and descriptive.
3. Open a pull request with:
- Problem summary
- What changed
- How it was tested

## Pull Request Checklist

- [ ] Tests pass locally
- [ ] No unrelated file changes
- [ ] README/docs updated if behavior changed
- [ ] Security-sensitive changes are clearly explained

## Recommended Branch Protection (GitHub)

For `main`, enable these settings in repository branch protection rules:

- Require pull request before merging
- Require at least 1 approval
- Require status checks to pass before merging
- Dismiss stale approvals when new commits are pushed
- Restrict direct pushes to `main`

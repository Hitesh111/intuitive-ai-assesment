# Contributing Guide

Thank you for your interest in contributing.

## Local Setup

```bash
git clone <repo-url>
cd essement
./setup.sh      # creates venv, installs deps, runs migrations, creates admin user
```

## Running the Server

```bash
./run.sh        # starts on http://localhost:8000
./run.sh 9000   # custom port
```

## Running Tests

```bash
# Unit tests (no server needed)
python manage.py test --verbosity=2

# Full API integration tests (server must be running)
./test.sh
```

## Code Style

- Follow existing patterns — thin views, business logic in `helpers.py`
- Use double quotes for strings (consistent with existing code)
- Add a docstring to every new function
- All new features must include tests

## Making a Change

1. Create a branch: `git checkout -b feat/your-feature`
2. Make your changes and add tests
3. Run `python manage.py test` — all tests must pass
4. Run `./test.sh` — all integration checks must pass
5. Commit with a clear message and open a PR

## Project Structure

```
vm_lifecycle/
├── models.py      # VMInstance + VMActionLog
├── serializers.py # DRF serializers
├── views.py       # HTTP layer only
├── helpers.py     # Business logic (state guards, audit log, etc.)
├── services.py    # OpenStack provider adapter
└── tests.py       # Test suite
docs/
├── architecture.md  # System design and diagrams
└── roadmap.md       # Backlog beyond the time box
```

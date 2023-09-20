# Infer Talents API
test

<p align="center">
<a href="https://github.com/softuvo/infer-talents/actions"><img alt="Actions Status" src="https://github.com/softuvo/infer-talents/workflows/Lint/badge.svg"></a>
<a href="https://github.com/softuvo/infer-talents/actions"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

### Requirements

- Postgres: [Postgres Mac App](http://postgresapp.com/) or [Postgres CLI](https://formulae.brew.sh/formula/postgresql#default)
- Python version 3.7.1 (use [Pyenv](https://github.com/pyenv/pyenvin) to manage your Python versions)
- [Poetry](https://python-poetry.org/) (Python package manager)
- [Pre-commit](https://pre-commit.com/#install)

### First Time Setup

1. Clone repo and cd into directory
1. Create virtual environment: `python -m venv venv` (you could also use Poetry for this step, but I think it's easier this way)
1. Run: `source venv/bin/activate`
1. Install packages: `poetry install`
1. Set up the pre-commit hook (to automatically auto-format): `pre-commit install`
1. Database setup from terminal (`psql postgres -U [username]`):
    1. Create the database: `CREATE DATABASE infer;`
    1. Create DB user: `CREATE USER admin;`
    1. Grant privilages to user for our database: `GRANT ALL PRIVILEGES ON DATABASE infer TO admin;`
1. Run migrations: `python manage.py migrate --settings=main.settings`
1. Create an admin user for logging into the Django admin interface: `python manage.py createsuperuser --settings=main.settings`

### Running the App

1. Make sure you are already in your virtual environment: `source venv/bin/activate`
1. Run the app: `python manage.py runserver --settings=main.settings`
1. View the API at http://localhost:8000 and the admin interface at http://localhost:8000/admin

## Poetry Instructions

**Add New Dependencies:**

- `poetry add [package-name]`
- Dev dependency: `poetry add -D [package-name]`

**Using the Black Auto-formatter**

You can run the auto-formatter at any time using the pre-commit hook manually: `pre-commit run --all-files`

See more Black options [here](https://github.com/psf/black).

**Skip Pre-commit Hooks**

`SKIP=flake8,black git commit -m "message"`

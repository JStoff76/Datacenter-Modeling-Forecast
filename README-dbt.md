# Quick start: dbt project (Snowflake)

This repository contains a minimal dbt project to get you started with Snowflake.

Files added
- `dbt_project.yml` — minimal project configuration using the `my_snowflake_profile` profile.
- `models/example_model.sql` — a tiny example model.
- `profiles-externalbrowser.yml` — example profile using SSO (copy to `%USERPROFILE%\\.dbt\\profiles.yml`).

Steps to test locally (PowerShell)

1) Activate the venv with Snowflake adapter:

```powershell
.\env-dbt311\Scripts\Activate.ps1
```

2) Copy the example profile to your user dbt directory and set environment variables (or use key-pair auth):

```powershell
mkdir $env:USERPROFILE\\.dbt -ErrorAction Ignore
cp .\\profiles-externalbrowser.yml $env:USERPROFILE\\.dbt\\profiles.yml

# Set required env vars (replace values). Because you use SSO, do NOT set a password; dbt will open your browser to authenticate.
$env:SNOWFLAKE_ACCOUNT = 'your_account'
$env:SNOWFLAKE_USER = 'your_user'
$env:SNOWFLAKE_ROLE = 'your_role'
$env:SNOWFLAKE_WAREHOUSE = 'your_wh'
$env:SNOWFLAKE_DATABASE = 'your_db'
$env:SNOWFLAKE_SCHEMA = 'your_schema'
```

3) Test the connection (this will open your browser for SSO):

```powershell
.\env-dbt311\Scripts\dbt debug --profile my_snowflake_profile
```

4) If debug succeeds, run the example model:

```powershell
.\env-dbt311\Scripts\dbt run --models example_model --profile my_snowflake_profile
```

Notes
- The example uses environment variables to avoid committing secrets. For automation, use key-pair auth and/or secret injection.
- If you prefer a different venv name, edit commands accordingly.

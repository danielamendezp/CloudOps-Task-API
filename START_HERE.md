# Getting started

## Update an existing checkout

1. Stop the previous application with `docker compose down`.
2. Copy this package's contents into the existing project. Keep your local `.git` and `data` directories: the public package deliberately excludes them. Never copy the private alias key into Git or a public ZIP.
3. Remove the old `START_HERE_ES.md` and `docs/AWS_CONNECTION_ES.md` after saving these English replacements.
4. Run `python -m unittest discover -s tests -v` and `python scripts/smoke_test.py`.
5. Run `docker compose up --build`. The API publishes port 8080 only on localhost. SQLite persists in a named Docker volume.
6. In another terminal at the repository root, use `.\scripts\try_real_asset.ps1` to register the public website manually, or follow `docs/AWS_CONNECTION.md` for real AWS metadata imports.
7. List assets with `Invoke-RestMethod http://localhost:8080/assets | ConvertTo-Json -Depth 5`; use `/tasks` for tasks.
8. Perform maintenance separately. Set a task to done only after completing the work it describes.
9. Save the returned IDs, run `docker compose down`, start again, and retrieve the records by ID to verify persistence. Do not use `down -v` on personal data: it deletes the volume.

## Publication

Read `PUBLICATION_REVIEW.md` and `VALIDATION.md`. Check `git status` and `git diff`. Stage intended changes, then run `python scripts/check_public_files.py` to inspect tracked filenames and common credential patterns before committing.

```bash
git add .
python scripts/check_public_files.py
git commit -m "Document AWS inventory integration and public release checks"
git push
```

A `.gitignore` does not remove previously tracked files or historical commits. If private data was committed, address that before publishing. This package does not rewrite the existing repository history.

## Images and evidence

Original screenshots containing the local Windows username/path were omitted from this public package. Existing local copies are unaffected. Use the consolidated sanitized TXT evidence, or add manually reviewed screenshots showing only sanitized API results.

## Scope

Assets may represent applications, S3 buckets, CloudFront distributions, DynamoDB tables, Lambda functions, or Lightsail instances. Discovery is a manual read-only import. It does not scan for vulnerabilities, execute maintenance, or provide CNAPP functionality. Running Docker or uploading code does not deploy the optional Terraform stack.

# Publication review — 2026-11-10

## Material excluded from this public package

- `data/inventory-alias.key`: private 32-byte HMAC alias key. It is not an AWS credential, but exposing it weakens the privacy of resource aliases. Keep the existing local copy private so current aliases remain stable.
- `.git/`: source-control internals, local repository metadata and original objects. This public package is a source snapshot and does not replace or rewrite the user's repository history.
- Python bytecode and cache directories.
- Original desktop screenshots: contain the local Windows username/path. They are personal metadata rather than AWS credentials; the public package uses TXT evidence instead.

The uploaded Git index listed 18 tracked paths, none under `data/` or ending in `.key`. That is encouraging but does not establish the state of a different checkout, staged changes made later, or all historical commits. Pattern checks of available loose Git objects found no recognized AWS access-key or private-key patterns. The archive did not include complete usable refs/history, so a full history review was not possible.

## Included evidence

The three original TXT snapshots and the consolidated TXT contain keyed asset aliases, local UUIDs, timestamps and selected configuration. They do not contain detected original resource ARNs, account numbers, bucket/table/function names, access keys or private-key blocks. Approved public Dani WebWorks domains are intentionally retained.

Configuration details (runtime, memory, timeout, deletion protection, service counts, region) are operational information. They are not credentials, but publishing them is still a disclosure. Remove individual fields if you prefer a smaller public footprint. Pseudonymization is not a guarantee of absolute anonymity.

Synthetic `123456789012` account numbers and example ARNs in tests and `terraform.tfvars.example` are fixtures/placeholders, not detected real account data. Do not replace those examples with private values.

## Prevent accidental publication

The strengthened `.gitignore` excludes the data folder, alias keys, common credential files, local databases, Terraform state/plans, and ZIP archives. `.dockerignore` also excludes credentials and private runtime material from the build context.

After copying this package into the existing checkout, stage intended changes and run:

```powershell
git status --short
git ls-files -- data/ .env .aws/
python scripts/check_public_files.py
```

The `git ls-files` check should print nothing for private paths. `.gitignore` does not remove a file already tracked. If the alias key is tracked, remove only its index entry, keeping the local file:

```powershell
git rm --cached -- data/inventory-alias.key
```

If the key was ever published, deleting the latest file alone is insufficient. Review/remove its public history and rotate the alias key as needed; rotation changes pseudonyms and can require re-importing records. Rotate AWS credentials if actual AWS credentials were exposed. This package did not detect such credentials, and no automatic rotation or history rewrite was performed.

## Pending before claiming all checks pass

1. Confirm GitHub Actions passes, including the new Docker volume-recreation test and Terraform validation.
2. Decide whether to resolve the S3 configuration AccessDenied results or publish the partial status as documented.
3. Confirm the actual checkout contains no old screenshots/private exports or untranslated duplicate guides you do not intend to publish. Copying a cleaned ZIP over a folder does not delete old files automatically.
4. Keep the optional Terraform deployment marked unverified until it is deployed and tested.

The basic scanner is a useful guardrail, not a complete secret-history scanner or security audit. Licensing is a separate owner decision; no license was chosen automatically.

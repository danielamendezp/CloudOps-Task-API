# Connect to existing AWS resources

## Deployment model

The application runs locally with Docker and SQLite. Host-side Python scripts use a local AWS profile to query existing resources. No `terraform apply` is needed and no additional Lambda, ECR, API Gateway, DynamoDB or CloudWatch resources are provisioned by the importers.

## Discovery and reports

| Service | API operations | Scope |
| --- | --- | --- |
| CloudFront | ListDistributions | Account/global distributions |
| Lightsail | GetInstances | Instances in the selected region; live verification pending |
| DynamoDB | ListTables, DescribeTable | Regional table metadata; no row reads |
| S3 | ListBuckets, GetBucketLocation, GetBucketVersioning, GetPublicAccessBlock | General-purpose bucket metadata; no object listing/download |
| Lambda | ListFunctions | Regional function metadata; no invocation or code download |

The SDK can receive additional metadata in memory. Scripts select only approved fields for storage/output. Full AWS responses and raw exception messages must not be logged or published.

## Authentication and permissions

Use an existing AWS CLI profile, preferably with temporary credentials. Credentials stay outside the repository and are not mounted into Docker. Do not use root credentials.

- `policies/inventory-readonly.json`: CloudFront, Lightsail and DynamoDB listing.
- `policies/inventory-s3-optional.json`: optional S3 bucket listing.
- `policies/inventory-lambda-readonly.json`: Lambda listing in us-east-1.
- `policies/inventory-storage-report-readonly.json`: DynamoDB description and S3 configuration reads needed by the storage report.

These files are examples; they are not automatically applied. Where possible, narrow resource-specific reads to the buckets and tables you own. Adding a limited policy to an administrator does not remove existing administrator rights. An explicit deny or a boundary can still block an allowed action.

## Cost model

No additional infrastructure is created by local discovery. Read-only APIs are not universally free. Review service request pricing, especially S3, and any existing auditing configuration. Imports are manual, not scheduled. `--limit` bounds returned resources per service, not necessarily the total number of API requests because of pagination and retries.

Deploying the optional Terraform roots is separate and can incur compute, API, registry storage, table storage/requests, recovery, and monitoring charges.

## Run a preview

```powershell
python -m pip install -r requirements-aws.txt
python scripts/import_aws.py --profile YOUR_PROFILE --region YOUR_REGION --services cloudfront dynamodb s3 lambda --limit 10
```

The preview queries AWS but does not save inventory rows. It creates a private local alias key in `data/` if needed. Sign in to the profile through its normal authentication mechanism first.

## Import into the running local API

Start Docker Desktop and `docker compose up --build`. In another terminal:

```powershell
python scripts/import_aws.py --profile YOUR_PROFILE --region YOUR_REGION --services cloudfront dynamodb s3 lambda --limit 10 --import-local
Invoke-RestMethod http://localhost:8080/assets | ConvertTo-Json -Depth 5
```

The importer only appends missing aliases. It does not reconcile deletions or update resource health. With the same profile and key, repeated imports skip existing references. If local insertion fails partway, repeating the import skips records already inserted.

## Export evidence

Approve only exact public custom domains you want to disclose:

```powershell
python scripts/export_aws_report.py --profile YOUR_PROFILE --region YOUR_REGION --public-domains daniwebworks.com www.daniwebworks.com daniwebworks-templates.com
python scripts/export_storage_report.py --profile YOUR_PROFILE --region YOUR_REGION --limit 10
python scripts/export_lambda_report.py --profile YOUR_PROFILE --region YOUR_REGION --limit 10
python scripts/combine_reports.py
```

The consolidated file is `docs/evidence/aws-inventory-report.txt`. Each section retains its own query timestamp. Combining files is a local operation and does not refresh AWS data. If any required report is missing or empty, combination stops without replacing the existing consolidated file.

## Privacy

HMAC-SHA256 aliases depend on `data/inventory-alias.key`, the profile and resource scope. Keep the key and local databases private; back them up separately. Losing or replacing the key changes aliases and can create duplicate inventory records. The key is not an AWS access key, but disclosing it weakens pseudonymization.

Public examples intentionally include approved Dani WebWorks domains and selected configuration settings. Local UUIDs and timestamps do not grant AWS access. This is pseudonymization, not absolute anonymity. Manually entered records are not sanitized automatically. Review every report/screenshot before publication.

## Observed limitations

The supplied evidence verifies CloudFront, DynamoDB and Lambda metadata queries. S3 listing succeeded, but bucket configuration reads returned AccessDenied. Missing S3 results are unknown, not failed security controls. The report correctly preserves these errors rather than inventing successful results.

## Pricing references

- https://aws.amazon.com/s3/pricing/
- https://aws.amazon.com/lambda/pricing/
- https://aws.amazon.com/api-gateway/pricing/
- https://aws.amazon.com/ecr/pricing/
- https://aws.amazon.com/dynamodb/pricing/
- https://aws.amazon.com/cloudwatch/pricing/

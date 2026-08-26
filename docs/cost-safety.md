# Cost Safety Strategy — Cloud Cost Lab

## Principle

Cloud Cost Lab must not itself become an expensive cloud project. Every GCP resource creation must be justified, bounded, and reversible.

## Rules

### Before Creating Any GCP Resource

Answer these questions:

1. Is it billable?
2. What is its purpose?
3. What is the smallest practical configuration?
4. How can it be shut down?
5. How can it be destroyed?
6. What IAM permissions does it need?
7. What is the rollback path?

### Before Running `terraform apply`

Always show:
- Resources to be created
- Why they are needed
- Potential billing impact
- Rollback/destroy method

Never silently create expensive infrastructure.

### BigQuery Cost Protection

- Never use `SELECT *` on billing tables
- Always filter by date partition
- Select only required columns
- Aggregate early in the query
- Avoid repeated full-table scans
- Use dry-run / bytes-estimate when available
- Document expensive vs optimized queries

### Default Preferences

| Preference | Choice |
|------------|--------|
| Default mode | Demo/mock (no GCP cost) |
| Resource size | Smallest practical |
| Data retention | Limited (not unlimited) |
| Queries | Bounded (partition, limit, column selection) |
| Shutdown | Scheduled where possible |
| Budget alerts | Configured before resource creation |
| Destroy procedure | Documented for every resource |

## BigQuery Specific

### Bad Query (avoid)

```sql
SELECT *
FROM `project.billing_dataset.gcp_billing_export_v1_*`
```

This scans entire billing history — potentially gigabytes and costs money per byte scanned.

### Good Query (optimized)

```sql
SELECT
  service.description,
  SUM(cost) as total_cost,
  SUM(credits.amount) as total_credits
FROM `project.billing_dataset.gcp_billing_export_v1_*`
WHERE _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND project.id = 'my-project'
GROUP BY service.description
ORDER BY total_cost DESC
LIMIT 20
```

This filters by partition, selects specific columns, aggregates, and limits results.

## Application Budget Awareness

The application itself tracks:
- Query costs (BigQuery bytes scanned)
- API call frequency
- Data retention age
- Resource count

## Emergency Procedures

### If unexpected costs appear:

1. Check GCP Billing console
2. Identify the source (which service, which project)
3. Determine if it's a runaway query or resource
4. Stop the source (disable schedule, stop VM, kill query)
5. Document in incident report
6. Fix root cause before re-enabling

### Terraform Destroy

Every Terraform-managed resource has a documented destroy path:

```bash
terraform plan -destroy
terraform destroy
```

Review the plan before destroying.

## Cost Monitoring

Set up budget alerts:
- 50% of monthly budget → notification
- 70% → warning
- 90% → critical alert
- 100% → exceeded alert

Do not auto-stop production resources on budget exceed — alert humans instead.

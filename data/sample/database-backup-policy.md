# Database Backup Policy

## Backup schedule

Production databases are backed up automatically once per day. Backups are retained for 30 days.
In addition to the daily snapshot, write-ahead log archiving is enabled so the database can be
restored to any point within the retention window, not just to a daily snapshot boundary.

## Restore procedure

Restoring a database is performed by provisioning a new database instance from the desired
backup or point-in-time target, verifying the restored data with the standard data-integrity
checklist, and then switching the application's connection string to the restored instance. The
old instance is kept, not deleted, until the restore has been verified in production traffic for
at least 24 hours.

## Who can restore

Only members of the platform team may perform a production restore. Any other engineer who
believes a restore is needed should open an incident and page the platform on-call rotation
rather than attempting the restore themselves.

## Backup testing

Backup restorability is tested quarterly by performing a full restore into a non-production
environment and validating row counts against a known baseline. A backup that has never been
tested for restorability should not be treated as a reliable backup.

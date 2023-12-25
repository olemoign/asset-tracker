3.2.0
---
- feat(datatables): add colresize and colreorder
- feat(db): do not start a db transaction on /health or serving static files
- feat(docker): use multistage to limit layers
- feat(global): remove datetime.utcnow
- fix(sentry): messages stack trace

3.1.15
---
- feat(notifications): update frequencies and grouping

3.1.14
---
- fix(asset): last calibration
- fix(labels): Marlink translations
- fix(logs): notifications count
- fix(site): test tenants management

3.1.13
---
- fix(extract): equipments columns order

3.1.12
---
- fix(software_update): intermediate versions

3.1.11
---
- fix(reminders): invalid dates

3.1.10
---
- feat(ci): use python build
- feat(sentry): add release

3.1.9
---
- feat(reports): add last event date

3.1.8
---
- feat(marlink): calibration frequency is now 4 years

3.1.7
---
- fix(assets): remove null configs

3.1.6
---
- feat(notifications): update emails

3.1.5
---
- feat(assets): update families
- fix(translations): asset type

3.1.4
---
- feat: add data in export
- fix: multiple domains

3.1.3
---
- fix: multiple events delete

3.1.2
---
- fix: decommissioned assets filter
- fix: extract
- feat: update dates calculation
- feat: empty equipments panel

3.1.1
---
- fix: autoflush bug

3.1.0
---
- Manage test tenants to not lose sites.
- Status + labels update.
- Asset RTA link.
- New equipments.
- Detenant app, allowing for multiple RTA.
- New asset type: consumables case.
- Improve decommissioned assets management.
  
2.8
---
- Excel extract.
- Calibration reminders.
- Improve site link.

Admin:
- conf: asset_tracker.client_specific => asset_tracker.specific
- conf: add celery block (include celerybeat for cron)

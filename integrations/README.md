# Integration setup

All exports contain **synthetic** telemetry. No live SIEM or CTFd environment was available for end-to-end verification. Local HTTP fixture tests verify request paths, payload transport, authentication header formats, success/error handling and importer resume. Those are adapter tests, not proof of real ingestion.

## Build and inspect

`python integrations/export.py`

Creates eight CSVs, a private CTFd REST manifest/ZIP, Splunk HEC events and Elasticsearch Bulk NDJSON under `integrations/package/`. The ZIP is an import package for the supplied script, **not** a native CTFd database backup. Keep the manifest/ZIP private: it contains answer keys.

## CTFd

Prepare an owned CTFd instance and create a short-lived admin access token in its settings. Run `python integrations/ctfd_import.py --url http://127.0.0.1:8000` to review the dry-run. Set `CTFD_TOKEN` in your environment and add `--send` only when authorized. HTTPS is required for remote hosts; TLS verification remains enabled. Redirects are not followed with credentials.

The importer creates 24 standard hidden challenges (one per finding), static case-insensitive flags, two hints and the corresponding CSV. It writes an operation receipt after each completed operation; reruns skip recorded steps. Same-name objects without a receipt cause a stop for reconciliation. An ambiguous network failure may have created an object before the receipt was saved; inspect CTFd before retrying. This is not a distributed transaction or an exactly-once guarantee. Do not share receipts across instances.

In CTFd admin, review every question, file, flag and hint, run a participant solve, then release only the intended challenges. A hint costs 10 points per finding in CTFd; native SunSOC charges per case. CTFd scoring semantics therefore differ. Native notes and facilitator analytics are not migrated. Set CTFd registration/visibility and team modes according to the event's consent policy.

## Splunk

Create a dedicated training index and a HEC token constrained to that index. Disable indexer acknowledgements for this simple adapter or extend it to poll ACK endpoints; current success means endpoint acceptance only. Configure the token's source/index defaults. `SIEM_TOKEN` is the HEC token.

`python integrations/siem.py splunk --url https://splunk.example:8088`

Add `--send` after authorization. The adapter posts NDJSON events with epoch times, host, sourcetype `sunsoc:synthetic` and case IDs to `/services/collector/event`. Verify results in search before claiming ingestion:

```spl
index=YOUR_TRAINING_INDEX sourcetype="sunsoc:synthetic"
| stats count by case_id
```

There should be 157 events on a clean first import. Repeated HEC sends can duplicate events; do not retry blindly after an ambiguous response. Search examples: `case_id=lateral event=7045`, or `case_id=mailroom user="nur.aisyah"`. Fields may require JSON extraction depending on the deployment.

## Elasticsearch

Create a dedicated index with `@timestamp` as date and the identifier fields as keyword, using the supplied `elastic-mapping.json`. Create an API key with only necessary privileges on `sunsoc-training`. Set `SIEM_TOKEN` to the encoded API key. The adapter posts `application/x-ndjson` to `/_bulk`, uses stable event IDs, and fails when `errors` is true. A repeated import overwrites matching fixture IDs rather than increasing the document count.

`python integrations/siem.py elastic --url https://elastic.example:9200`

Review the dry-run and add `--send` after authorization. Refresh/search the index separately and confirm 157 documents. A query such as `{"query":{"term":{"case_id":"lateral"}}}` should return the lateral-movement pack. Index creation, real server authentication, field mappings and searchability must be validated in the target environment. Credentials are read from environment variables and are never logged by these scripts.

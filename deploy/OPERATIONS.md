# SunSOC operations

## Local Python

Use Python 3.11–3.14. Create `.venv`, install `requirements.lock`, then run `.venv/bin/python app.py`. The server binds only to 127.0.0.1:4891; choose another port with `PORT`. Set `SUNSOC_FACILITATOR_TOKEN` to a long random value in your shell or local secret manager before startup. The application never provides a default facilitator credential. Without it, the instructor API is disabled. Participant accounts can still practise. Do not use the test token from automated tests for a real workshop.

The generated signing key and SQLite database are in `instance/`; protect the directory. A signing-key change invalidates existing sessions. Each account's progress is durable. No email, password recovery or identity verification is provided. Use pseudonyms. The scoreboard lists pseudonyms to signed-in participants. Keep a clean database for each workshop; archive the previous `instance/` directory after stopping the server instead of mixing cohorts. SQLite backups should use its backup API while the app is stopped or in a controlled maintenance period.

## Container

`docker build -t sunsoc-local .`

`docker run --rm --name sunsoc-local -p 127.0.0.1:4891:4891 --read-only --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp:size=16m -v sunsoc-data:/app/instance -e SUNSOC_FACILITATOR_TOKEN sunsoc-local`

The app listens on the container network interface; the published host port is loopback only. The image uses a non-root account, a persistent named volume, no host mounts and no command-execution puzzle. A `compose.yaml` provides the same settings when the Compose plugin is installed. Do not expose a bare HTTP port publicly. For an authorized shared deployment, add a reviewed TLS reverse proxy, set `SUNSOC_HTTPS=1`, restrict registration/network access and review backups, retention and incident response. This local range has not had a production penetration test or load test.

## Per-team AWS path (not applied)

`deploy/terraform/` defines an EC2 instance per team, each with an independent Docker volume, no public address and no inbound security-group rules. All access uses AWS Systems Manager port forwarding. Inputs deliberately require an approved AMI, existing VPC/private subnet and an immutable image digest. No resources have been provisioned.

1. Build, inspect and publish the container image only when separately authorized. For private ECR, configure the instance role and registry login in bootstrap before use; the supplied bootstrap expects an image it can pull without registry credentials.
2. Choose an AL2023 AMI containing a running SSM agent. The private subnet must reach SSM/ssmmessages, the OS package repository and the chosen registry over HTTPS through approved egress or endpoints. DNS must work. Validate these requirements with the platform owner.
3. Install Terraform 1.7+ and the AWS provider, then run `terraform init`, `terraform fmt -check`, `terraform validate`, and review `terraform plan -var-file=approved.tfvars`. These native Terraform commands have not been run yet. HCL parse checks are separate from provider validation.
4. Apply only after authorization and cost review. Restrict each team's IAM user/role to `ssm:StartSession` on its own instance and `AWS-StartPortForwardingSession`; avoid granting a shell session to participants. Operator permissions remain separate. The template's instance role only provides SSM managed-instance connectivity.
5. Use `aws ssm start-session --target INSTANCE_ID --document-name AWS-StartPortForwardingSession --parameters '{"portNumber":["4891"],"localPortNumber":["4891"]}'` and browse localhost. Requires AWS CLI and Session Manager plugin.
6. Retrieve the generated facilitator secret as the authorized operator through a protected SSM session from `/opt/sunsoc/runtime.env`. Never include it in workshop screenshots or reports.
7. Verify health, participant isolation, volume persistence and session permissions per team. Export participant progress and aggregate feedback with consent. Review/destroy the resources after the workshop according to approved retention. `terraform destroy` is destructive and was not run.

## Guest scenario intake

Use `workshop/GUEST-SCENARIO.md`. The source contract is `data/cases.json`; restart the process after changing reviewed content, and regenerate the CTFd/SIEM package. The importer is an instructor operation, never a participant upload route. Keep stable IDs once a workshop has begun. `tools/validate_cases.py` validates reviewed incoming content before use. The shipped app has exactly eight cases; adding/removing questions requires reviewing the fixed three-question scoring/analytics assumptions in `app.py` and UI. Guest contributions are a review workflow, not a claim that a sponsor supplied content.

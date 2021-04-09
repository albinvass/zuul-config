lgtm

sample secret

- secret:
    name: github_application_credentials
    data:
      application_id: xyz
      private_key: xyz

sample job config

- job:
    name: lgtm
    parent: null
    final: true
    timeout: 120
    run: playbooks/lgtm/run.yaml
    secrets:
    - github_application_credentials

sample pipeline

- pipeline:
    name: lgtm
    manager: independent
    precedence: low
    require:
      vexxhost:
        open: True
        current-patchset: True
    trigger:
      github:
        - event: pull_request
          action:
            - comment
            - opened
            - changed
            - reopened
        - event: pull_request_review
    start:
      github:
        check: 'in_progress'
        comment: false
    success:
      github:
        check: 'success'
        comment: false
    failure:
      github:
        check: 'failure'
        comment: false



only current issue is that it will not react to comments inside PRs, so
if you approve a PR and type /approve -- it won't work.. so that just needs
to be addressed and some writing of tests...

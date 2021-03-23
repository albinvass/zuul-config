#!/usr/bin/env python3

import os
from textwrap import dedent
import sys

from dateutil import parser as dateutil_parser
from codeowners import CodeOwners
from github3 import github


# EMOJI
REVIEW_COMMENT_PREFIX = ':sparkles: This pull request requires a code review.'

LGTM_ALIASES = [
    ':+1:',
    '/lgtm'
]

APPROVAL_ALIASES = [
    ':rocket:',
    '/approve'
]

def main():
    app_id = os.getenv('GITHUB_APP_ID')
    private_key = os.getenv('GITHUB_PRIVATE_KEY').encode('utf-8')
    organization_name, repository_name = os.getenv('PROJECT').split('/')
    pull_request_id = os.getenv('PULL_REQUEST_ID')

    github_app = github.GitHub()
    github_app.login_as_app(private_key, app_id)
    app_slug = github_app.authenticated_app().slug

    github_installation = github.GitHub()
    github_installation.login_as_app_installation(
        private_key,
        app_id,
        github_app.app_installation_for_repository(
            organization_name,
            repository_name
        ).id
    )

    organization = github_installation.organization(organization_name)
    repository = github_installation.repository(organization.login, repository_name)
    pull_request = github_installation.pull_request(
        organization.login,
        repository.name,
        pull_request_id
    )

    # Get reviewers
    reviewers = set()
    try:
        owner_file_contents = repository.file_contents('CODEOWNERS')
        data = owner_file_contents.decoded.decode('utf-8')
        code_owners = CodeOwners(data)

        for f in pull_request.files():
            file_reviewers = code_owners.of(f.filename)
            if file_reviewers is None:
                continue

            for reviewer_type, reviewer in file_reviewers:
                if reviewer_type == 'USERNAME':
                    reviewers.add(reviewer.replace('@', ''))
                    continue
                raise SystemError("Unknown reviewer_type: %s" % reviewer_type)
    except:
        return 0

    # Get last commit date
    commit_dates = []
    for c in pull_request.commits():
        date = dateutil_parser.parse(c.commit.committer['date'])
        commit_dates.append(date)
    last_commit_date = max(commit_dates) if commit_dates else None

    # Parse comments
    review_comment = None
    sign_offs = set()
    approvals = set()
    for comment in pull_request.issue_comments():
        # Find the application comment
        review_prefix = comment.body.startswith(REVIEW_COMMENT_PREFIX)
        is_bot_comment = comment.user.login == f"{app_slug}[bot]"
        if is_bot_comment and review_prefix:
            review_comment = comment

        # Find the signoffs
        if comment.created_at > last_commit_date:
            for line in comment.body.split("\n"):
                if line.strip() in LGTM_ALIASES:
                    sign_offs.add(comment.user.login)
                if line.strip() in APPROVAL_ALIASES:
                    sign_offs.add(comment.user.login)
                    approvals.add(comment.user.login)

    # Update comment
    message = dedent(f"""\
    {REVIEW_COMMENT_PREFIX}

    Reviewer | Sign-off
    -------- | --------
    """)

    for reviewer in reviewers:
        signed_off = ":v: Not reviewed"
        if reviewer in sign_offs:
            signed_off = ":ok_hand: Looks good to me"

        approval = ""
        if reviewer in approvals:
            approval = "<br>:rocket: Approved"

        message += f"@{reviewer} | {signed_off} {approval}"

    if review_comment is not None:
        review_comment.edit(message)
    else:
        review_comment = pull_request.create_comment(message)

    if any([(r in approvals) for r in reviewers]):
        return 0

    return 1


if __name__ == '__main__':
    sys.exit(main())

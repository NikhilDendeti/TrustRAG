# Attribution

The Markdown files in this directory (except `fixture_vendor_faq_injection.md`,
which is a TrustRAG-authored security test fixture) are cleaned copies of pages
from the GitLab Handbook.

- Source: https://gitlab.com/gitlab-com/content-sites/handbook
- Snapshot commit: `6f045e41f4c7e4e28cfb72271d01cf0b87dc5533` (2026-10-12T10:24:04Z)
- Licence: MIT, Copyright (c) GitLab B.V.
  https://gitlab.com/gitlab-com/content-sites/handbook/-/blob/main/LICENSE

Front matter, Hugo shortcodes, images, HTML tags and link targets were removed
by `scripts/fetch_handbook.py`; the wording is otherwise unchanged.

The handbook is public. The classifications and role restrictions in
`data/handbook_acl.json` are a demo access policy invented for TrustRAG and do
not reflect GitLab's own access rules.

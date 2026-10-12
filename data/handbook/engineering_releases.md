# GitLab Releases

Looking for product release information? See release posts, releases page, What's new, changelog, or feature and deprecations overview.

## Overview

GitLab has three different release types:

1. **Monthly release**: A GitLab version (XX.YY.0) published on the 3rd Thursday of every month, containing new features, bug fixes and performance improvements from successful deployments on GitLab.com.
1. **Patch release**: Bug fixes and security updates for maintained versions, published twice monthly.
1. **Internal release**: Private releases for delivering high-severity fixes to GitLab Dedicated within remediation SLAs.

## Release Policy

### Why Release Policies Matter

GitLab follows semantic versioning, which establishes a contract with our customers:

* **MAJOR** versions may contain breaking changes
* **MINOR** versions contain new features (backward compatible)
* **PATCH** versions contain bug fixes only (safe to auto-upgrade)

Customers rely on this contract to make upgrade decisions. Many customers auto-upgrade patch releases without extensive testing because they trust that patches contain only bug fixes. When we violate this contract, we:

* **Erode customer trust** in our entire release process
* **Put customer environments at risk** with unexpected changes
* **Undermine release predictability** that customers depend on for planning
* **Create cascading problems** when rushed releases introduce new bugs requiring additional patches

### What Each Release Type Contains

| Release Type | Contains | Does NOT Contain |
|--------------|----------|------------------|
| **Monthly** | New features, bug fixes, performance improvements | N/A - this is the vehicle for all new work |
| **Patch** | Bug fixes, security fixes, performance regressions | New features, feature flag enables, incomplete work |
| **Internal** | Critical bug fixes, security fixes for Dedicated instances | New features, feature flag enables, incomplete work |

For SLO/SLA commitments on bug and security fix timelines, see Patch release SLO/SLA Commitments.

### Ownership When Deadlines Are Missed

When a feature misses the monthly release deadline, the appropriate path is the **next monthly release**, not an exception to release policy.

| Team | Owns |
|------|------|
| Development | Shipping code in the next policy-compliant release |
| Product | Communicating the delay to stakeholders; adjusting roadmap expectations |
| Customer Success | Managing customer expectations; negotiating timeline changes |
| Release | Executing policy-compliant releases that maintain customer trust in GitLab releases |

Release Managers do not own accommodating missed deadlines.

### Exception Process

> [!IMPORTANT]
> Every approved exception **requires** a Feature Change Lock (FCL) and a post-release incident review. **These are not optional**.

Exceptions to release policy are rare and require explicit approval outside the Release team.

**Release Managers are authorized to decline requests that violate release policies.** Pressure from Customer Success, Sales, or other teams does not constitute approval for policy exceptions.

If an exception is believed necessary:

1. **Requestor** documents the business justification and customer impact assessment
2. **Requestor** starts a Feature Change Lock (FCL) to protect platform stability (**mandatory**)
3. **Requestor** escalates to VP of your organization for sponsorship. The approving leader provides written approval acknowledgment of policy violation
4. **Sponsor VP** requests exception from Software Delivery Engineering Leadership or Infrastructure VP Platform.
5. **Release Manager** executes only after receiving written approval
6. **Post-release:** Incident review to address the root cause of the exception request (**mandatory**)

Exceptions approved without this process set precedent that undermines all release policies.

### Escalation Path

| Situation | Contact |
|-----------|---------|
| Process questions | #releases Slack channel |
| Exception requests | Your Director/VP (not Release Managers) |
| Policy clarification | Delivery/Platforms leadership |

## Release Coordination

### Teams Involved

| Team | Responsibility |
|------|----------------|
| Release Team | Deployments, Process coordination; executing policy-compliant releases |
| Infrastructure | Environment updates |
| Security | Vulnerability fixes and disclosure coordination |
| Product | Feature readiness; owning delays when features miss deadlines |
| Marketing | Release communications |

### Communication

* **#releases** (Slack): Release status and questions
* **Release Post**: Public announcements

## Maintenance Policy

See the GitLab maintenance policy for details

## Terminology

* **Maintenance policy**: Describes the release pace of our major, minor and patch releases for self-managed users.
* **Upcoming version**: New GitLab release (XX.YY.0) being developed.
* **Maintained versions**: GitLab versions covered by the maintenance policy.
* **Backports**: Bug or security fixes from a recent version applied to an older version.
* **Stable branches**: Source of the GitLab release packages delivered to customers.
* **Auto-deploy**: GitLab process to deploy application changes to GitLab.com.
* **Release managers**: DRIs for GitLab releases and deployments to GitLab.com.

## Resources

### Monthly release

* Monthly release schedule and process
* When do I need to have my MR merged?
* How can I determine if my MR will be included?

### Patch release

* Patch release process and policy
* Patch release runbook for engineers
* Security runbook for engineers

### Internal release

* Internal release process
* Internal release runbook for engineers

### Links

* Release Manager schedule
* How to reach the Release and Deploy team

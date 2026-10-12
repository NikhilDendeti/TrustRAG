# Performance

## Performance Facets

We categorize performance into 3 facets

1. Backend
1. Frontend
1. Infrastructure

### Backend performance

Backend performance is scoped to response time of API, Controllers and command line interfaces (e.g. git).

**DRI**: Tim Zallman, VP of Engineering, Core Development.

Performance Indicators:

- Memory Utilization (backlog)

### Frontend performance

Frontend performance is scoped to response time of the visible pages and UI components of GitLab.

**DRI**: Tim Zallman, VP of Engineering, Core Development

Performance Indicators:

- Largest Contentful Paint (LCP)

### Infrastructure performance

Infrastructure performance is scoped to the performance of GitLab SaaS Infrastructure.

**DRI**: Marin Jankovski, Sr. Director of Infrastructure, SaaS Platforms.

Performance Indicators:

- GitLab.com known application scaling bottlenecks

## Other Related Pages

- GitLab.com (infra) Architecture
- Monitoring GitLab.com
- Application Architecture Documentation
- GitLab.com Settings
- GitLab Performance Monitoring Documentation
- Performance Testing Tools

**Meta issue** to track various issues listed here is at on the infrastructure tracker.

## GitLab's Application performance

## Measurement

### Target

Performance of GitLab and GitLab.com is ultimately about the user experience. As also described in the product management handbook, "faster applications are better applications".

Our current focus at the moment are two indicators:

- **Largest Contentful Paint** (LCP) to measure the complete loading performance. To provide a good user experience, LCP should occur within 2.5 seconds of when the page first starts loading.
- **Time to first Byte** (TTFB) so we have an understanding how long the backend takes to send the base page. Our target for a good backend rendering is below 500ms

On a mid term we target to focus on all of the Web Vitals with introducing also a bigger focus on **First Input delay** (FID) and **Cumulative Layout Shift** (CLS). So if routes are already performing well with our main indicators please extend optimisations on those.

There are many other performance metrics that can be useful in analyzing and prioritizing work, some of those are discussed in the sections below. But the user experienced LCP is the target for the site as a whole, and should be what everything ties back to in the end.

Groups should monitor closely the user experience in regards of performance to also improve the perceived performance also outside those measured performance indicators. For example if any action after loading is very slow and takes a lot of time.

### What we measure

Every end-user performance metric we can, through sitespeed.io by having automatic runs every 4 hours. Any data we collect can be helpful to provide us to analyze for improvements or bottle necks on specific routes. We are sending the data to an graphite instance for continous data storage which is used for all Grafana dashboards. On top of that we also save full reports (links are visible by activating the `Runs` toggle on a sitespeed dashboard) to have more insight data, slow motion data, HAR files and full Lighthouse reports.

### How we measure

We currently measure with an empty cache, the connection limited to `Cable` and a medium CPU based machine which is located in `us-central` every 4 hours.

### Past and Current Performance

The URLs from GitLab.com listed in the table below form the basis for measuring performance improvements - these are heavy use cases. The times indicate time passed from web request to "the average time at which visible parts of the page are displayed" (per the definition of Speed Index). Since the "user" of these URLs is a controlled entity in this case, it represents an _external_  measure of our previous performance metric "Speed Index".

| Type | 2018-04 | 2019-09 | 2020-02 | Now* |
| --- | --- | --- | --- | --- |
| Issue List: GitLab FOSS Issue List | 2872 | 1197 | - | N/A |
| Issue List: GitLab Issue List |  |  | 1581 |  |
| Issue: GitLab FOSS #4058 | 2414 | 1332 | 1954 |  |
| Issue Boards: GitLab FOSS repo boards | 3295 | 1773 | - | N/A |
| Issue Boards: GitLab repo boards | | | 2619 |  |
| Merge request: GitLab FOSS !9546 | 27644 | 2450 | 1937 |  |
| Pipelines: GitLab FOSS pipelines | 1965 | 4098 | - | N/A |
| Pipelines: GitLab pipelines | | | 4289 |  |
| Pipeline: GitLab FOSS pipeline 9360254 | 4131 | 2672 |  2546 |  |
| Project: GitLab FOSS project | 3909 | 1863 | - | N/A |
| Project: GitLab project | | | 1533 |  |
| Repository: GitLab FOSS Repository | 3149 | 1571 | - | N/A |
| Repository: GitLab Repository | | | 1867 |  |
| Single File: GitLab FOSS Single File Repository | 2000 | 1292 | - | N/A |
| Single File: GitLab Single File Repository | | | 2012 |  |
| Explore: GitLab explore | 2346 | 1354 | 1336 |  |
| Snippet: GitLab Snippet 1662597 | 1681 | 1082 | 1378 |  |

*To access the sitespeed grafana dashboards you need to be logged into your Google account

**Note:** Since this table spans time before and after single-codebase we kept GitLab FOSS pages close to GitLab ones to enable comparisons despite not being exactly the same project.

#### All Sitespeed Dashboards

Sitespeed - Site summary

Sitespeed - Page summary

Sitespeed - Page timing summaries

If you activate the `runs` toggle you will have annotations with links to all full reports. Currently we are running measurements every 2 hours.

---

## Steps

### Web Request {#flow-of-web-request}

All items that start with the tachometer () symbol represent a step in the flow that we _measure_. Wherever possible, the tachometer icon links to the relevant dashboard in our monitoring. Each step in the listing below links back to its corresponding entry in the goals table.

Consider the scenario of a user opening their browser, and surfing to their dashboard by typing `gitlab.com/dashboard`, here is what happens:

1.  **User request**
    1.  User enters gitlab.com/dashboard in their browser and hits enter
    1.  Lookup IP in DNS (not measured)
       - Browser looks up IP address in DNS server
       - DNS request goes out and comes
    back (typically ~10-20 ms, [data?]; often times it is already cached so
      then it would be faster).
       - For more details on the steps from browser to application, enjoy reading
    1.  Browser to Azure LB (not measured)
       - Now that the browser knows where to find the IP address, browser sends the web
    request (for gitlab.com/dashboard) to Azure's load balancer (LB).
1.  **Backend processes**
    1.  Azure LB to HAProxy (not measured)
       - Azure's load balancer determines where to route the packet (request), and
       sends the request to our Frontend Load Balancer(s) (also referred to as
         HAProxy).
    1.  HAProxy SSL with browser (not measured)
       - HAProxy (load balancer) does SSL negotiation with the browser
    1.  HAProxy to NGINX (not measured)
       - HAProxy forwards the request to NGINX in one of our front end workers.
       In this case, since we are tracking a web request, it would be the NGINX box in the
         "Web" box in the production-architecture diagram; but alternatively the request can come in via API or a git command
         from the command line, hence the API, and git "boxes" in that diagram.
       - Since all of our servers are in ONE Azure VNET, the overhead of SSL
          handshake and teardown between HAProxy and NGINX should be close to negligible.
    1.  NGINX buffers request (not measured)
       - NGINX gathers all network packets related to the request ("request
       buffering"). The request may be split into multiple packets by the intervening network,
       for more on that, read up on MTUs.
       - In other flows, this won't be true. Specifically, request buffering is
       switched off for LFS.
    1.  NGINX to Workhorse (not measured)
       - NGINX forwards the full request to Workhorse (in one combined request).
    1.  Workhorse distributes request
       - Workhorse splits the request into parts to forward to:
       -
       Unicorn.  Time spent waiting for Unicorn to pick up a request is `HTTP queue time`.
       -  Gitaly [not in this scenario, but not measured in any case]
       -  NFS (git clone through HTTP) [not in this scenario, but not measured in any case]
       -  Redis (long polling) [not in this scenario, but not measured in any case]
    1.   Unicorn calls services
       - Unicorn, (often just called "Rails", or "application server"),
       translates the request into a Rails controller request; in this case
       `RootController#index`. The round trip time it takes for a request to
       _start_  in Unicorn and _leave_ Unicorn is what we call `Transaction
       Timings`. RailsController requests are sent to (and data is received from):
       -   PostgreSQL (`SQL timings`),
       -   NFS (`git timings`),
       -   Redis (`cache timings`).
       - In this `gitlab.com/dashboard` example, the controller addresses all three .
       - There are usually _multiple_ SQL calls (or file, or cache, etc.) calls for a given
      controller request. These add to the overall timing, especially since they are
      sequential. For example, in
      this scenario, there are 29 SQL calls (search for `Load`)
      when this _particular user_ hits `gitlab.com/dashboard/issues`. The number of SQL calls
      will depend on how many projects the person has, how much may already be in cache, etc.
       - Rails tackles the steps within a controller request sequentially.
          In other words if it needs to make calls out to the database and to
          git, it is not set up to those in parallel but rather has to wait for
          the response to the first step before proceeding to the next step.
       - In the Rails stack, middleware typically adds to the number of round trips
       to Redis, NFS, and PostgreSQL, per controller call, in addition to the
       timings of Rails controllers.  Middleware is used for {session state, user
      identity, endpoint authorization, rate limiting, logging, etc} while the
      controllers typically have at least one round trip for each of {retrieve
      settings, cache check, build model views, cache store, etc.}. Each such
      roundtrip is _estimated_ to take < 10 ms.
    1.    Unicorn constructs Views
         - The construction of views can take a long time (`view timings`).
         In some controllers, data is gathered _first_ after which a view is
         constructed. In other controllers, data is gathered _from within_  a
         View, so that the `view timing` in those cases includes the time it
         took to call NFS, PostgreSQL, Redis, etc. And in many cases, both are done.
         - A particular view in Rails will often be constructed from multiple partial
        views. These will be used from a template file, specified by the controller
        action, that is, itself, generally included within a layout template.
        Partials can include other partials. This is done for good code
        organization and reuse. As an example, when the _particular user_  from the
        example above loads `gitlab.com/dashboard/issues`, there are 56 nested / partial views rendered (search for `View::`)
         - Partial views may be cached via various Rails techniques, such as Fragment Caching. In addition,
         GitLab has a Markdown cache stored in the database that is used to
         speed up the conversion of Markdown to HTML.
         - Perceived performance in the way of First Paint can be affected by
         how much of the content of a view is rendered by the backend vs.
         sending a "minimal" html blob to the user and relying on Javascript /
         AJAX / etc. to fetch additional elements that take the page from First
         Paint to "Fully Loaded". See the section about the frontend for more on this.
    1.  Unicorn makes HTML (not measured)
        - Once the Views are built, Unicorn completes making the "HTML blob" that
        is then returned to the browser.
        - Some of these blobs are expensive to compute, and are sometimes hard-coded
      to be sent from Unicorn to Redis (i.e. to cache) once rendered.
    1.  HTML to Browser (not measured)
       - The HTML blob is sent back to the Browser via the following path:
       -  Unicorn to Workhorse (not measured)
       -  Workhorse to NGINX (not measured)
       -  NGINX to HAProxy (not measured)
       -  HAProxy to Azure LB (not measured)
       -  Azure LB to Browser (not measured)
1.  **Render Page**
    1.   **First Byte**
      - The time when the browser receives the first byte.
      In addition to everything in the backend, this also depends on network speed.
      In the dashboard linked to by the tachometer above, First Byte is measured
      from a Digital Ocean box in the US with relatively little network lag thus
      representing an estimate of _internal_ First Byte. Past performance on
      first byte is recorded elsewhere on this page.
      - For any page, you can use your browser's "inspect" tool to look at "TTFB" (time to first byte).
      -
      `First Byte - External` is measured for a hand selected number of URLs using SiteSpeed
    1.   **Speed Index**
      - Browser parses the HTML blob and sends out further requests
      to GitLab.com to fetch assets such as javascript bundles, CSS, images, and
      webfonts.
      - The timing of this step depends (amongst other things) on the number and
      the size of assets, as well as network speed. For _each_ static asset, there is a
      round-trip of:
            - for cached assets: browser <i class="fas fa-long-arrow-alt-right fa-fw"
           aria-hidden="true"> nginx <i class="fas fa-long-arrow-alt-right fa-fw"
           aria-hidden="true"> nginx confirms cached asset is still valid <i
           class="fas fa-long-arrow-alt-right fa-fw" aria-hidden="true"> browser
            - for non-cached or expired cached assets: browser <i class="fa
           fa-long-arrow-right fa-fw" aria-hidden="true"> workhorse <i class="fa
           fa-long-arrow-right fa-fw" aria-hidden="true"> workhorse grabs asset
           from local cache <i class="fas fa-long-arrow-alt-right fa-fw"
         aria-hidden="true"> browser.
            - for a page that is served through GitLab Pages: browser <i class="fa
           fa-long-arrow-right fa-fw" aria-hidden="true"> pages daemon
           (independent service in the architecture) <i class="fas fa-long-arrow-alt-right
           fa-fw" aria-hidden="true"> browser.
      - Stylesheets can block page rendering by default, which can lead to
      unnecessary delays in page rendering.
      - Starting in 9.5, scripts won't block rendering anymore as they are
      loaded with `defer="true"`, so they are parsed and executed in the same
      order as they are called but only after html + css has been rendered.
      - Enough meaningful content is rendered on screen to calculated the "Speed Index".
    1.   Fully Loaded
      - When the scripts are loaded, Javascript compiles and evaluates them within the page.
      - On some pages, we use AJAX to allow for async loading. The AJAX call can
      be triggered by all kinds of things; for example a frontend element (button)
      or e.g. the `DOMContentLoaded` event. The new call is for a new URL, and such requests are routed either
      through the Web or API workers, invoke their respective Rails controllers
      on the backend, and return the requested files (HTML, JSON, etc).
      For example, the calendar and activity feeds on a username page `gitlab.com/username`
      are two separate AJAX calls, triggered by `DOMContentLoaded`. (The
      `DOMContentLoaded` event "marks the point when both the DOM
      is ready and there are no stylesheets that are blocking JavaScript
      execution" (taken from an article about the critical rendering path)).
      The alternative to using AJAX would be to include the full Rails code to
      generate the calendar and activity feed within the same controller that
      is called by the gitlab.com/username URL; which would lead to slower First
      Paint since it simply involves more calls to the database etc.

---

### Git Commit Push

First read about the steps in a web request above, then pick up the thread here.

After pushing to a repository, e.g. from the _web UI_:

1. In a web browser, make an edit to a repo file, type a commit message, and hit "Commit"
1. NGINX receives the git commit and passes it to Workhorse
1. Workhorse launches a `git-receive-pack` process (on the workhorse machine) to save the new commit to NFS
1. On the workhorse machine, `git-receive-pack` fires a git hook to trigger `GitLab Shell`.
   - GitLab Shell accepts Git payloads pushed over SSH and acts upon them (e.g. by checking if you're authorized to perform the push, scheduling the data for processing, etc).
   - In this case, GitLab Shell provides the `post-receive` hook, and the `git-receive-pack` process passes along details of what was pushed to the repo to the `post-receive` hook. More specifically, it passes a list of three items: old revision, new revision, and ref (e.g. tag or branch) name.
1. Workhorse then passes the `post-receive` hook to Redis, which is the Sidekiq queue.
   - Workhorse informed that the push succeeded or failed (could have failed due to the repo not available, Redis being down, etc.)
1. Sidekiq picks up the job from Redis and removes the job from the queue
1. Sidekiq updates PostgreSQL
1. Unicorn can now query PostgreSQL.

---

## Goals

### Web Request

Consider the scenario of a user opening their browser, and surfing to their favorite URL on `GitLab.com`. The steps are described in the section on "web request". In this table, the steps are measured and goals for improvement are set.

Guide to this table:

- All times are reported in milliseconds.
- `# per request` : average number of times this step occurs per request. For instance, an average "transaction" may require 0.2 SQL calls, 0.4 git calls, 1 call to cache, and 30 nested views to be built.
- `p99 Q2-17`: the p99 timing (in milliseconds) at the end of Q2, 2017
- `p99 Now`: link to the dashboard that displays the _current_ p99 timing
- `p99 Q3-17`: the target for the p99 timing by the end of Q3, 2017
- Numbers in _italics_ are _per event_  and/or _in parallel_  with other timings, and therefore do not sum to the (sub)totals. The non-italic numbers _do_ sum to the (sub)totals.

| Step                                                    | # per request | p99 Q2-17 | p99 Now | p99 Q3-17 goal | Issue links and impact |
|---------------------------------------------------------|--------------:|--------:|--------:|-------------:|------------------------|
| **USER REQUEST** |               |         |         |              |                        |
| Lookup IP in DNS                          |     1         |~10| ? |~10|  Use a second DNS provider  |
| Browser to Azure LB                    |     1         |~10| ? |~10|                        |
| **BACKEND PROCESSES** |    |         |         |              | Extend monitoring horizon |
|Azure LB to HAProxy                     |     1         |~2| ? |~2|                        |
|HAProxy SSL with Browser                 |     1         |~10| ? |~10| Speed up SSL |
|HAProxy to NGINX              |     1         |~2| ? |~2|                        |
|NGINX buffers request                   |     1         |~10| ? |~10|                        |
|[NGINX to Workhorse          |     1         |~2|  ? |~2|                        |
|Workhorse distributes request      |     1         |         |         |      | Adding monitoring to workhorse |
|&nbsp;&nbsp;&nbsp;&nbsp;_Workhorse to Unicorn_ | 1 | 18  |  | 10 | Adding Unicorns |
|&nbsp;&nbsp;&nbsp;&nbsp;_Workhorse to Gitaly_   | |     | ?  |     |   |
|&nbsp;&nbsp;&nbsp;&nbsp;_Workhorse to NFS_         | |     | ?  |     |   |
|&nbsp;&nbsp;&nbsp;&nbsp;_Workhorse to Redis_      | |     | ?  |     |   |
|Unicorn calls services          |  1  |  2500       |   |  1000 | Allow more GitLab internals monitoring    |
|&nbsp;&nbsp;&nbsp;&nbsp;_Unicorn_  _Postgres_      | | _250_ || _100_ | Speed up slow queries  |
|&nbsp;&nbsp;&nbsp;&nbsp;_Unicorn  NFS_          | | _460_ |   | _200_ | Move to Gitaly - sample result |
|&nbsp;&nbsp;&nbsp;&nbsp;_Unicorn  Redis_       | |  _18_ |  |     |   |
|Unicorn constructs Views |  | 1500   |   |  |       |
|Unicorn makes HTML |  |    |   |  |       |
|HTML to Browser |  |    |   |  |       |
|&nbsp;&nbsp;&nbsp;&nbsp;_Unicorn to Workhorse_ | 1 | ~2 | ?  | ~2  |  |
|&nbsp;&nbsp;&nbsp;&nbsp;_Workhorse to NGINX_             |      1        | ~2| ? |~2|                        |
|&nbsp;&nbsp;&nbsp;&nbsp;_NGINX to HAProxy_                 |      1        |~2| ? |~2| Compress HTML in NGINX  |
|&nbsp;&nbsp;&nbsp;&nbsp;_HAProxy to Azure LB_               |      1        |~2| ? |~2|                        |
|&nbsp;&nbsp;&nbsp;&nbsp;_Azure LB to Browser_               |      1        |~20| ? |~20|                        |
|**RENDER PAGE** |  |         |         |              |                        |
| **FIRST BYTE** (see [note 1][^1])]  |   | **1080 - 6347** |         | **1000**  |                        |
|**SPEED INDEX** (see [note 2][^2]) |  | **3230 - 14454** |   |   **2000**     | Remove inline scripts, Defer script loading when possible, Lazy load images, Set up a CDN for faster asset loading, Use image resizing in CDN |
|Fully Loaded (see [note][^3]) |  |   6093 - 14003   |    |  not specified  |   Enable webpack code splitting |
|---------------------------------------------------------|---------------|---------|---------|--------------|------------------------|

**Notes:**

[^1]: 1\.  The range here corresponds to the range in First Byte times of the 4 sample URLs provided in the First Byte table. However, based on all _non-staging_ URL's measured in this dashboard, between 2017-03-30 and 2017-06-28, the number would be 3,833 ms.
[^2]: 2\.  The range here corresponds to the range in Speed Indices of the 4 sample URLs provided in the Speed Index table.
[^3]: 3\.  The range here corresponds to the range in Fully Loaded times of the 4 sample URLs provided in the Speed Index table.

### Git Commit Push

_Table to be built; merge requests welcome!_

## Modifiers

For any performance metric, the following modifiers can be applied:

- **User**: how a _real_  GitLab user would experience and measure the time.
- **Internal**: the time as measured from _inside_  GitLab.com's infrastructure (the boundary is defined as being at the "network | Azure load balancer" interface).
- **External**: the time as measured from any specified point outside GitLab.com's infrastructure; for example a DO box with Prometheus monitoring or a browser in a specified geo-region on a specified network speed.

## First byte

### External

Timing history for First Byte are listed in the table below (click on the tachometer icons for _current_ timings). All times are in milliseconds.

| Type |  End of Q4-17 | Now |
|------|--------------:|-------------:|-------------:|-----|
| Issue: GitLab CE #4058 | 857 |  |
| Merge request: GitLab CE !9546 | 18673 |  |
| Pipeline: [GitLab CE pipeline 9360254] | 1529 |  |
| Repo: GitLab CE repo | 1076 |  |

### Internal {#first-byte-internal}

To go a little deeper and measure performance of the application & infrastructure without consideration for frontend and network aspects, we look at "transaction timings" as recorded by Unicorn. These timings can be seen on the
Rails Controller dashboard _per URL that is accessed_ .

## Availability and Performance labels {#availability-performance-labels}

### Availability

This section has been moved to Availability severity.

### Performance

To clarify the priority of issues that relate to GitLab.com's performance you should add the `~performance` label, as well as a "Severity"

label. There are two factors that influence which severity label you should
pick:

1. How frequently something is used.
2. How likely it is for something to cause an outage.

For strictly performance related work you can use the Controller Timings Overview
Grafana dashboard. This dashboard categorises data into three different
categories, each with their associated severity label:

1. Frequently Used: `~severity::2`
2. Commonly Used: `~severity::3`
3. Rarely Used: `~severity::4`

This means that if a controller (e.g. `UsersController#show`) is in the
"Frequently Used" category you assign it the `~severity::2` label.

For database related timings you can also use the
SQL Timings Overview.
This is the dashboard primarily used by the Database Team to determine the AP
label to use for database related performance work.

## Database Performance

Some general notes about parameters that affect database performance, at a very crude level.

- From whitebox monitoring,
  - Of time spent on/by Rails controllers, this much is spent in the database:  (for a specific Rails controller / page)
  - _Global_ SQL timings:
- A single HTTP request will execute a single controller. A controller in turn will usually only use one available database connection, though it may use 2 if first a read was performed, followed by a write.
  - pgbouncer allows up to 150 concurrent PostgreSQL connections. If this limit
is reached it will block pgbouncer connections until a PostgreSQL connection becomes available.
  - PostgreSQL allows up to 300 connections (connected, whether they're active or not doesn't matter). Once this limit is reached new connections will be rejected, resulting in an error in the application.
  - When the number of processes > number of cores available on the database servers, the CPU constantly switches cores to run the requested processes; this contention for cores can lead to degraded performance.
- As long as the database CPU load < 100% (), then in theory the database can handle more load without adding latency. In practice database specialists like to keep CPU load below 50%.
  - As an example of how load is determined by underlying application design:
       DB CPU percent used to be lower (20%, prior to 9.2, then up to 50-75% when 9.2 RC1 went live, then back down to 20% by the time 9.2 was released.
- pgbouncer
  - What it does: pgbouncer maps _N_ incoming connections to _M_ PostreSQL connections, with _N_ >= _M_ (_N_ < _M_ would make no sense). For example, you can map 1024 incoming connections to 10 PostgreSQL connections. This is mostly influenced by the number of concurrent queries you want to be able to handle. For example, for GitLab.com our primary rarely goes above 100 (usually it sits around 20-30), while secondaries rarely go above 20-30 concurrent queries. The more secondaries you add, the more you can spread load and thus require fewer connections (at the
  cost of having more servers).
  - Analogy: pgbouncer is a bartender serving drinks to many customers. Instead of making the drinks himself she instructs 1 out of 20 "backend" bartenders to do so. While one of these bartenders is working on a drink the other 19 (including the "main" one) are available for new orders. Once a drink is done one of the 20 "backend" bartenders gives it to the main bartender, which in turn gives it to the customer that requested the drink. In this analogy, the _N_ incoming connections are the patrons of the bar, and there are _M_ "backend"
   bartenders.
  - Pgbouncer frontend connections (= incoming ones) are very cheap, and you have lots of these (e.g. thousands). Typically you want _N_ >= _A_ with _N_ being the pgbouncer connection limit, and _A_ being the number of connections needed for your application.
  - PostgreSQL connections are much more expensive resource wise, and ideally you have no more than the number of CPU cores available per server (e.g. 32). Depending on your load this may not always be sufficient, e.g. a primary in our setup will need to allow 100-150 connections at peak.
  - Pgbouncer can be configured to terminate PostgreSQL connections when idle for a certain time period, conserving resources.

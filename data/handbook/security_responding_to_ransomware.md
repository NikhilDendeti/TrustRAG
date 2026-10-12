# Responding to Ransomware

Ransomware is a persistent threat to many organizations, including GitLab.  In the event of a ransomware attack involving GitLab assets, it's important to know the existing response procedures in place.  Given the variability of targets in such attacks, it's critical to adapt to existing circumstances and understand that disaster recovery processes are in place to avoid paying any ransom.  GitLab's red team has done extensive research to determine the most likely targets to be affected.  As a result, the following guidelines are intended to help bootstrap an efficient response to protect the organization.

***Critical First Steps:***

- Engage the SIRT team as soon as a ransomware attack is detected
- The SIRT team will then follow the incident response guide and incident communication plan and reference the relevant run book.
- Responders should leverage GitLab's established rapid engineering response plan during the mitigation phase.
- The Business Continuity & Disaster Recovery Controls handbook page should be referenced for relevant information.

***Relevant Teams:***

Depending on the impacted resources, the following teams should be engaged and made aware of the issue created for the rapid engineering response.  Note that this is not a comprehensive list depending on impacted assets.

- Database: Disaster Recovery Team - responsible for disaster recovery strategy for the PostgreSQL database.
- Infrastructure Team - availability, reliability, performance, and scalability of GitLab SaaS software
- Infrastructure Security Team - infrastructure teams stable counterpart focused on cloud infrastructure security, best practices, and vulnerability management
- Business Technology Engineering - endpoint and systems access management
- Support Team - responding to customer or employee inquiries regarding system outages
- Legal & Corporate Affairs
- Security Assurance - assuring the security of GitLab as an enterprise application
- Marketing - accurately represent GitLab and our products in our marketing, advertising, and sales materials.

***Communications:***

Once we've determined that we need to communicate externally about an incident, the SIMOC should kick off our Security incident communications plan and key stakeholders will be engaged for collaboration, review and approval on any external-facing communications.  *Note:* if customer data is exposed, external communications may be required by law.

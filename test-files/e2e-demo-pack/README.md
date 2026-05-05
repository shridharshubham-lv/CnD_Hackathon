# E2E Demo Pack

This folder contains realistic upload files for a full Campaign Intelligence demo.

Recommended demo path:
1. In Stage 1, upload `01_campaign_brief_enterprise_demo.pdf`.
2. In Stage 2, use Agent 1 suggested answers for high-priority questions when available.
3. In Stage 3, approve the execution plan.
4. In Stage 4, upload at least these assets:
   - `02_email_asset_aligned.docx`
   - `03_linkedin_asset_bad_cta.pdf`
   - `04_paid_search_asset_wrong_audience.docx`
   - `05_landing_page_asset_aligned.pdf`
   - `06_sales_outreach_asset_aligned.docx`
5. Run the consistency check and review the seeded errors in Stage 5.

Expected demo outcome:
- Email, landing page, and sales outreach should read as aligned.
- LinkedIn should trigger a CTA mismatch because it says `Start your free trial` instead of `Book a demo`.
- Paid Search should trigger audience and CTA problems because it targets startup founders and says `Start free`.

If you want to test alternate upload types, a DOCX copy of the brief is included as `01_campaign_brief_enterprise_demo.docx`.

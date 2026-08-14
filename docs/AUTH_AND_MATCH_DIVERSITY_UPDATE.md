# OTP lookup and match diversity update

- Unknown email/phone values receive `account_not_found` (HTTP 404), so the frontend stays on the OTP request form.
- Inactive accounts receive `account_inactive` (HTTP 403).
- Existing active accounts continue to receive OTP normally.
- The seed catalog now includes 68 matches, 62 teams, and 38 venues.
- A database assertion prevents a team from being scheduled twice on the same local calendar day.
- Existing match IDs 1..20 and ticket IDs 1..40 remain unchanged.

# corpus-irs-pubs

Text mirror of current U.S. Internal Revenue Service (IRS) publications, split per
chapter (or per major section for publications that have no chapters). Source
content is produced by the U.S. federal government and is **not subject to
copyright** (see Terms below). Intended as a reference corpus for consumer tax
questions: filing, deductions, credits, withholding, IRAs, education credits,
EITC, small business, basis, selling a home, and military/overseas filing.

## Scope

- Publications: 15 mirrored — 13 of the 15 requested plus the two
  successors to Pub 590 (see Skips)
- Files: 154 plain-text chapter files
- Total size: 4,251,265 bytes
- Downloaded: 2026-10-04 (UTC), from `https://www.irs.gov/publications/<slug>`
- Tax year as printed in each publication's own title (mostly 2025; Pub 15 is 2026)

| Directory | Publication | Revision | Files | Bytes |
|---|---|---|---|---|
| [`p15/`](p15/) | Publication 15 (2026), (Circular E), Employer’s Tax Guide | 2026 | 20 | 301,693 |
| [`p17/`](p17/) | Publication 17 (2025), Your Federal Income Tax | 2025 | 19 | 1,007,325 |
| [`p54/`](p54/) | Publication 54 (12/2025), Tax Guide for U.S. Citizens and Resident Aliens Abroad | 12/2025 | 10 | 294,369 |
| [`p334/`](p334/) | Publication 334 (2025), Tax Guide for Small Business | 2025 | 14 | 263,861 |
| [`p463/`](p463/) | Publication 463 (2025), Travel, Gift, and Car Expenses | 2025 | 8 | 284,329 |
| [`p501/`](p501/) | Publication 501 (2025), Dependents, Standard Deduction, and Filing Information | 2025 | 10 | 211,566 |
| [`p502/`](p502/) | Publication 502 (2025), Medical and Dental Expenses | 2025 | 13 | 128,015 |
| [`p503/`](p503/) | Publication 503 (2025), Child and Dependent Care Expenses | 2025 | 6 | 96,325 |
| [`p523/`](p523/) | Publication 523 (2025), Selling Your Home | 2025 | 6 | 120,851 |
| [`p525/`](p525/) | Publication 525 (2025), Taxable and Nontaxable Income | 2025 | 8 | 340,216 |
| [`p551/`](p551/) | Publication 551 (12/2025), Basis of Assets | 12/2025 | 5 | 106,712 |
| [`p590a/`](p590a/) | Publication 590-A (2025), Contributions to Individual Retirement Arrangements (IRAs) | 2025 | 6 | 249,031 |
| [`p590b/`](p590b/) | Publication 590-B (2025), Distributions from Individual Retirement Arrangements (IRAs) | 2025 | 5 | 262,491 |
| [`p596/`](p596/) | Publication 596 (2025), Earned Income Credit (EIC) | 2025 | 9 | 227,098 |
| [`p970/`](p970/) | Publication 970 (2025), Tax Benefits for Education | 2025 | 15 | 357,383 |

### Skips

- `p590` — HTTP 404 at https://www.irs.gov/publications/p590 (checked 2026-10-04).
  Publication 590 was split by the IRS into 590-A and 590-B; this mirror carries
  both (`p590a/`, `p590b/`) so IRA content is fully covered.
- `p963` — HTTP 404 at https://www.irs.gov/publications/p963 (checked 2026-10-04).
  No substitute fetched; not currently published as HTML.

## Source URLs

Index: https://www.irs.gov/publications

Per publication: `https://www.irs.gov/publications/<slug>` where `<slug>` is the
directory name:

p15 p17 p54 p334 p463 p501 p502 p503 p523 p525 p551 p590a p590b p596 p970

Each IRS publication page is a single long HTML document; chapters are detected
from the page's own heading structure (`role-chap` chapter headings, `role-part`
part dividers, `role-hd1` top-level sections for chapterless publications).

## Terms

Verified 2026-10-04 against
https://www.irs.gov/about-irs/use-of-content-from-irsgov ("Copyright notice"):

> "Content on this website that was created or maintained by federal employees in
> the course of their duties is not subject to copyright and may be freely
> copied. Credit is requested. If copyrighted material appears on the site, or is
> reached through a link on this site, the copyright holder must be consulted
> before the material may be reproduced."

The same page's "Official seal, names and symbols" notice (18 U.S.C. § 701,
31 U.S.C. § 333, 31 C.F.R. Part 37) prohibits use of IRS/Treasury seals, names,
and symbols in ways that imply endorsement. This mirror contains text only — no
IRS seal, logo, or branding — and gives credit by this notice:

> Content: Internal Revenue Service, https://www.irs.gov — works of the U.S.
> federal government, not subject to copyright (17 U.S.C. § 105).

Also reviewed: https://www.irs.gov/privacy-disclosure/irs-privacy-policy (fetched
2026-10-03) — the current privacy policy contains no copyright/reuse language;
the use-of-content page above is the operative statement.

## File format

- One directory per publication; one file per chapter (or major section), named
  `<NN>-<slug>.txt` in document order. Oversized chapters are split further as
  `<NN>-<slug>--pt<k>.txt`. No file exceeds 150 KB.
- Line 1 of every file is a header: `IRS Pub <number> (<revision>) | <title>`,
  e.g. `IRS Pub 17 (2025) | 1. Filing Information`.
- Body is the publication text, verbatim after tag stripping: paragraphs as
  lines, list items prefixed `- `, table rows rendered as pipe-separated cells.
  The chapter-anchor navigation block from the source page is removed.

## Regenerating

Requires `python3` and `curl`. The build script is included:

```sh
git clone https://github.com/xerj-org/corpus-irs-pubs
cd corpus-irs-pubs
python3 tools/build.py          # serial fetch (1s sleep, 30s timeout, 1 retry) + split
```

The script fetches each publication once into `raw/` and reuses cached files on
re-run, then writes the chapter files. Shape is enforced automatically
(150 KB per-file cap with re-splitting).

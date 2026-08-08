This is an UPDATE to the existing Aftershock build, not a rebuild. Keep the current
design tokens, palette, typography, homepage, and routing. Apply the changes below.

WRITING RULES:
- Title Case for headings, sentence case for body.
- Never use em dashes or en dashes anywhere in the copy.
- Confident, direct language.


═══════════ 1. NEW FIELDS NOW IN "data" ═══════════

  data.diagnostics                                  the measurement trust layer, see below
  data.important_notes.verdict                      one-sentence conclusion
  data.precedent_expectation.sector_averages[].avg_move_significant_only
  data.transmission_mechanism, data.companies_involved   (may already be rendered)

Hide any section whose field is missing or null. Never error on absent data.


═══════════ 2. KEY TAKEAWAY BLOCK ═══════════

Add as the FIRST content after the header, before "What Happened". A bordered panel,
signal blue left border, body text slightly larger than the page default, generous
vertical space. Reads as a briefing line, not another section. Readable in five seconds.
No chart here. Do not repeat this text elsewhere on the page.

IF recency is "breaking", build from data.precedent_expectation.sector_averages, using
the entry with the largest absolute avg_value:
  "Historically, events like this have most affected [sector], moving [avg_move] on
   average across [n_events] precedent(s), [n_significant] of which were statistically
   significant."
  If n_significant is 0 for that sector, soften instead of asserting:
  "Historically, events like this have shown a directional move in [sector]
   ([avg_move] average), though the pattern has not been statistically reliable across
   the precedents measured."
  If precedent_expectation is null or sector_averages is empty:
  "No validated historical precedent exists for this event yet. See below for what the
   system found and why it did not meet the validation bar."
  Beneath, one compact line listing tickers from data.companies_involved where exposure
  is "direct": "XOM, CVX (direct exposure)".

IF recency is "developing" or "settled", build from data.reaction, using the largest
absolute move:
  significant true:  "[Sector] moved [pct], a statistically significant reaction beyond
                      the overall market."
  significant false: "[Sector] moved [pct], the largest reaction measured, though not
                      statistically significant, meaning it may reflect normal market
                      noise rather than the event itself."
  If developing, append: " This is a provisional result; the full measurement window is
  not yet complete."
  Beneath, tickers from data.companies_affected filtered to that sector, with direction:
  "XOM, CVX, COP — up".


═══════════ 3. NEW SECTION: DIAGNOSTICS ═══════════

Render data.diagnostics. Place it AFTER "What Happened" and BEFORE any precedent
numbers or charts. This section tells the reader whether the figures below can be read
as caused by the event at all, so it must come before them.

Heading: "Can These Numbers Be Trusted"
Subheading: "Measurement quality checks on the precedents used below."

Contents, in order:
  1. data.diagnostics.summary as the section lead, set larger than body text.
  2. data.diagnostics.date_basis as a short supporting line in ash.
  3. CONCENTRATION FLAGS from data.diagnostics.concentration, an array of
     {precedent, sector, ticker, share, detail}. Render each as a compact flagged row
     with an amber left border. Use the pre-written "detail" text verbatim. Add a small
     monospace tag reading "[share] one name". If the array is empty, render a single
     quiet line: "No sector result was dominated by a single constituent."
  4. CONFOUNDING WINDOWS from data.diagnostics.confounding, an array of
     {precedent_id, clean, detail}. Resolve precedent_id to the precedent's name where
     possible. Entries where clean is false get an ember left border and a "Contaminated
     window" tag. Entries where clean is true render quietly in ash with a "Clean
     window" tag. Use the "detail" text verbatim.
  5. ANTICIPATION NOTES from data.diagnostics.anticipation, an array of
     {precedent, detail}. Render as short rows, precedent name then detail, in ash.
     If empty, omit this subsection entirely.

Hide the whole section if data.diagnostics is null. Hide any subsection whose array is
empty, except concentration, which shows the reassuring line above instead.

Link the section heading to /methodology#causal-reading. Link each concentration flag to
/methodology#concentration. Link each confounding entry to /methodology#confounding.


═══════════ 4. IMPORTANT NOTES, REVISED ═══════════

This section no longer discusses data reliability, that is now the Diagnostics section's
job. Its heading should reflect the narrower purpose.

Heading: "What Has Changed Since"
Subheading: "Substantive differences between the precedent conditions and today."

Render data.important_notes.verdict as a PROMINENT single line at the very top of the
section, above overall_applicability, styled by sentiment: if the sentence contains
"strong" use verdigris, "weak" use ember, otherwise ash. Larger than body text, one line.

Then overall_applicability as a lead paragraph in a bordered callout with a signal blue
left border.

Then each entry in notes as a card with the title in the display face, a category chip
in monospace uppercase ash reading Structural, Regime, Market Structure, Scale, or
Regional, a direction indicator (up arrow in ember labelled "Amplifies", down arrow in
verdigris labelled "Dampens", dash in ash labelled "Uncertain"), the detail text, and
"Affects: [precedent names]" where affects is non-empty.

IMPORTANT: this section now returns one to three notes, sometimes only one. Do not
assume a minimum count and do not pad the layout to fill space. Remove "Confounding"
from the category chip options, it is no longer emitted.


═══════════ 5. TIER STRUCTURE ═══════════

Introduce an explicit visual break so a reader knows where the summary ends and the
depth begins.

Above the break, in order: header, Key Takeaway, What Happened, Diagnostics, and the
verdict line pulled from Important Notes if it renders cleanly there.

Then a clear full-width divider with a heading: "Full Analysis". Below it, in order:
How This Reaches Markets, Companies Involved, the precedent charts and numbers, the
rest of Important Notes, the measured sections for developing and settled events, and
Historical Precedents.

The divider should read as a genuine boundary, not another section heading.


═══════════ 6. COLLAPSE REDUNDANT SECTOR VISUALS ═══════════

Three visuals currently show overlapping information. Restructure:

  - The DIVERGING BAR CHART of sector averages stays expanded as the primary view.
    Caption beneath it: "Average move across all validated precedents."
  - The DOT PLOT and the DETAILED CONSISTENCY TABLE both go behind a SINGLE toggle
    labelled "Show precedent-by-precedent spread". Collapsed by default.
    Dot plot caption: "Each dot is one precedent. Shows whether the average reflects a
    consistent pattern or a wide scatter."
    Table caption: "Per-sector significance counts across the precedent set."
  - Every other chart and table on the page also gets a one-line caption stating what
    it adds that the others do not.

In the sector averages table and the bar chart, rows where n_significant is 0 render
smaller and more muted than rows where it is above 0, so real findings surface without
the reader having to parse the consistency column.

Where sector_averages[].avg_move_significant_only is present and not null, show BOTH
figures with clear labels, for example "Average: +3.8%" and "Among significant results:
+5.2%". Where it is null, show only the raw average.


═══════════ 7. METHODOLOGY PAGE UPDATES ═══════════

Add these sections with anchor ids.

  #causal-reading  "Descriptive Versus Causal"
  An abnormal return is a descriptive figure. It says how prices moved relative to a
  statistical benchmark around a window. Reading it as something the event caused
  requires two things to be true: the event date is known precisely, and the event was
  not anticipated. If markets had already priced it in before the window opened, the
  measured reaction understates or misses the real one. This is why every report opens
  with measurement diagnostics before it shows any figures.

  #concentration  "When One Company Carries A Sector"
  Each sector figure is an average across a basket of named stocks. When one constituent
  dominates the movement, the figure describes that company rather than the sector. The
  system flags any significant sector result where a single ticker accounts for 60
  percent or more of the basket's total movement, so the figure is read for what it
  actually is.

  #confounding  "Contaminated Windows"  (revise the existing section)
  A measurement window runs from five days before an event to thirty days after. If
  another major development landed inside that window, the measured reaction cannot be
  attributed to the event alone. Every precedent's window is checked, and the result is
  stated per precedent rather than as a general caveat.

  #significance  (revise the existing section)
  Update to state the current validation rule: a precedent is only used when at least
  one sector's reaction is statistically significant, and when the significant reaction
  moves in the direction the event type would predict. A large move that fails the
  significance test is not evidence, and is not used.


═══════════ 8. BUILD NOTES PAGE UPDATES ═══════════

Revise the existing "Why Precedents Get Rejected" entry and add two new entries.

  REVISE "Why Precedents Get Rejected" to describe the current rule: a candidate
  precedent must be dated with high confidence, postdate 2005, have a complete
  post-event window, show at least one statistically significant sector reaction, and
  have that significant reaction move in the direction the event type predicts. Failing
  any of these, it is discarded rather than published.

  NEW: "Why The Validation Bar Was Raised"
  The original gate was too permissive. It required only that a precedent's reaction
  point in the expected direction, and that one sector move more than two percent. That
  let through precedents where every sector result was statistically insignificant,
  which meant the historical comparison was built on noise while looking substantive.
  Reports were showing sector averages where zero of three precedents cleared
  significance. The bar was raised to require at least one significant sector reaction,
  and to require the directional match to come from a significant sector rather than any
  sector. Validated precedent counts fell, which was the correct outcome. A shorter list
  that cleared a real bar is better evidence than a longer list that cleared a low one.

  NEW: "Why Diagnostics Are Separate From Interpretation"
  One section originally tried to do two jobs, assess whether the measurements could be
  trusted and interpret what they meant. Given a quota to fill and two jobs to do, it
  produced five notes on a single event that were all restatements of the same
  underlying point. The trust question moved into a computed diagnostics layer, checking
  date basis, single-constituent concentration, and confounding windows. With that
  handled, the interpretation section shrank to its actual job: what has materially
  changed between the precedent conditions and today. Fewer sections doing clearer jobs.


═══════════ 9. VERIFY THESE FROM PRIOR BUILDS ═══════════

Implement if missing, leave alone if already correct:
  - Standalone Companies Involved section, after the transmission mechanism, with
    ticker, name, full untruncated role text, and exposure styling (direct signal blue,
    indirect ash, beneficiary verdigris with a "Benefits" tag), ordered direct then
    beneficiary then indirect.
  - The "No Validated Precedents" empty state panel with its link to
    /methodology#precedents.
  - Refresh control on /events with spinner, "Updated" flash, and a relative
    "Last detection: N ago" timestamp from the newest event's created_at.
  - The wave wordmark in the nav and footer, the ring favicon at 16, 32, and 180px,
    per-route page titles, meta description, and the Open Graph preview image.
  - The watch list feed with regional map row backgrounds and recency-specific preview
    lines.
  - The four breaking-event charts from precedent_expectation.
  - Prose interpretation beneath every quantitative block.


Build all of this in one pass. Do not change the homepage.

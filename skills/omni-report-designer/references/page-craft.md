# Page and export craft

Choose composition from the actual task: fixed forms, flowing operational detail,
grouped management statements or parameterized evidence packs. These are options,
not mandatory templates. Preserve accepted reading order, density and branding.

- Use one explicit physical unit. Compute the printable body after margins and
  reserved header/footer space. Validate column widths before rendering, then
  inspect actual text growth. Never use an arbitrary tiny font as overflow repair.
- Distinguish fixed-page composition from flowing tables. Define group start/end,
  repeat headers, keep-with-next and continuation rules. Large groups must have a
  stated split behavior; an impossible keep-together rule cannot force truncation.
- Align numeric columns and units; use deliberate decimal precision, typography
  and whitespace. Preserve signs and distinguish missing, zero and source errors.
  Repeated headings and totals should remain understandable outside their first page.
- Preserve parameter context and data-as-of information in delivered output when
  needed. Put navigation or hover-only information into visible print equivalents.
- Verify chosen fonts and logo/image assets are approved and actually available
  in the native export runtime. Browser appearance does not prove PDF embedding.
- Define PDF pagination and Excel sheet structure separately. Do not equate a
  report section, rendered page and worksheet. Inspect long sheets and data types.

Useful learning sources, reviewed 2026-10-29:
[MESCIUS report layouts](https://developer.mescius.com/activereportsjs/docs/ReportAuthorGuide/report-configuration/Report-Layouts)
describes how fixed and growing content affect pagination;
[designer font configuration](https://developer.mescius.com/activereportsjs/docs/ReportAuthorGuide/QuickStart/Get-Started-With-Designer-App)
explains why consistent font configuration matters across outputs;
[export settings](https://developer.mescius.com/activereportsjs/docs/DeveloperGuide/ActiveReportsJSViewer/Export/Export-Settings)
documents format-specific choices. These are vendor capabilities, not promises
about an Omni deployment. No vendor code, runtime or font is installed by reading.

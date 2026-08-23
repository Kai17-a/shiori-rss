# Information and Content

> Part of the [Frontend skill](../../SKILL.md).

## Information Hierarchy

Every screen should have a clear visual hierarchy.

Classify information when useful as:

### Primary

Information or actions required to complete the current task.

Primary elements should receive the strongest visual emphasis.

### Secondary

Supporting information that helps the user make decisions.

It should remain visible without competing with primary information.

### Tertiary

Metadata such as:

- IDs
- timestamps
- internal names
- auxiliary descriptions
- low-priority status information

Keep tertiary information visually quiet.

Use these tools to establish hierarchy before adding decoration:

- position
- spacing
- typography
- font weight
- contrast
- grouping
- borders
- background differences

Do not rely on container boxes alone to establish hierarchy.

---

## Content Before Composition

Determine the shape of the content a screen will actually display before deciding layout or hierarchy: typical and maximum string lengths, typical and maximum item counts, and the range of states a value can take.

Layout decisions made against placeholder or idealized content tend to break once real content is substituted in.

---

## Prefer Realistic Content

Design against realistic content whenever possible.

Do not assume ideal short strings.

Test with:

- realistic names
- long names
- real statuses
- realistic timestamps
- long error messages
- zero values
- very large values
- missing values

Do not use Lorem Ipsum when representative product content is available.

The content should influence the layout.

---

## Scanning, Comparison, and Reading

Determine whether the user's primary mode on a screen is scanning, comparing, or reading, and let that mode drive the choice of structure.

- Scanning favors short lines, consistent alignment, and a stable left edge.
- Comparison favors tables and aligned lists over prose or scattered cards.
- Reading favors continuous prose, narrower measure, and fewer interruptions.

Do not default to card grids or tables without considering which mode the task actually requires.

---

## Progressive Disclosure

Do not surface every detail at once.

Show primary information by default. Move information that is needed occasionally, not constantly, behind an expansion, a detail view, or a tooltip.

Information the user needs on nearly every visit should stay visible. Information needed rarely, or only for edge cases, should be reachable rather than always rendered.

---

## Labels, Help Text, and Interface Copy

Keep labels concise and predictable. Use the same term for the same concept across every screen.

Button labels should describe the action clearly.

Prefer:

- Create project
- Save changes
- Restart service
- Delete account

over vague labels such as:

- Continue
- Submit
- Confirm

when a more precise label is possible.

Do not attach explanatory help text to inputs whose purpose is already obvious from their label.

Keep error and empty-state copy specific and actionable rather than generic.

---

## Missing, Long, and Localized Content

Design for missing values, unusually long values, and localized content from the start rather than retrofitting them later.

Consider:

- long names and long translated strings that may not fit the space a short English string implies
- right-to-left languages, where layout direction and icon mirroring matter
- pluralization, and date, time, and number formats that vary by locale

---

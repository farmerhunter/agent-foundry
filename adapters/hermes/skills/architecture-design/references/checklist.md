# Architecture Design Checklist

Ask before proposing an architecture:

- What domain state does the user actually care about?
- Which concepts are stable and which are implementation details?
- Which dimensions can vary independently?
- Are we forcing different business meanings into one field or model?
- What external failures are inevitable?
- Should those failures be modeled as status?
- What summary should UI consume?
- What is the MVP's main path?
- What design docs or user-facing runtime docs need to change so future agents understand the new boundary or flow?
- If a chosen technology is replaced, does the architecture still make sense?

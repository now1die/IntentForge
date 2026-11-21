# Index constraints

Every projected read and write checks `0 <= index < length`. The index expression uses the existing checked signed arithmetic and ordinary evaluation order. Index and extent findings label the observed input and source span. A missing initialization fact and a known outside-extent index are distinct observations.

The fixed-index edit family adjusts only a supported integer-offset access. The changed source must compile and agree with every supplied expected result under the checked projection. Reverse traversal that deliberately skips a metadata cell and a valid next-cell lookup both appear as controls.

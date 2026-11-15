# Archi import (S0 base model)

1. Archi: File > New > Empty Model. Save as `docs/architecture/archimate/vigilimen.archimate`.
2. File > Import > CSV Data Into Selected Model: choose `elements.csv`, then `relations.csv`, then `properties.csv` (this order; select the model first).
3. Nothing is drawn by the import. Create three views (right-click Views > New > ArchiMate View) and drag elements from the model tree:
   - View 1 "Plant layers": e*, a*, d01, t01-t10, with relations r01-r22.
   - View 2 "Safety separation": t01, t02, t11, t04, t05, m08 (plus a02 if you want the modelled contactor).
   - View 3 "Motivation": m01-m08, a03, a04, t02, relations r23-r31.
4. Colour a05 (edge) differently: it is planned, not built (property `status`).
5. Export each view: File > Export > View As Image (SVG) into `docs/architecture/diagrams/`.

IDs are only import keys; Archi assigns its own. If an import line is rejected as an invalid relationship, Archi names it: change the type to Association and tell Claude.

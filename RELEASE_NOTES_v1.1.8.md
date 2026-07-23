# v1.1.8 - standalone reproduction package fix

This release supersedes v1.1.7 as the journal-submission archive.

## Packaging fix

The v1.1.7 repository, complete archive, manuscript, figures, tables, and
automated checks were valid. An additional independent extraction test found
that the standalone final figure-code ZIP omitted `paper/tables/`, which the
current unified reconstruction command also validates and copies.

v1.1.8 includes the exact current Table 1--5 LaTeX assets in the standalone
package and adds a repository check that prevents this dependency from being
omitted again. The standalone ZIP is independently downloaded, extracted,
and executed as part of the final release audit.

## Scientific invariants

v1.1.8 does not change the data split, random seeds, six-architecture
candidate bank, seven initialized candidates, reference candidate, optimizer,
MSE loss, 50-update target adaptation, 10% selection threshold, complexity
limits, plotting implementation, figure data, or any reported numerical
value.

The main held-out evaluation remains 80 cases: 47 alternative selections,
including 44 beneficial and 3 harmful under the post-selection test-MSE
audit, plus 33 reference-retained cases. Mean paired MSE reduction relative
to PT+FT remains 14.60%, and complexity-limit satisfaction remains 100%.

## Release contents

The release contains the current manuscript source/PDF, Fig. 1--12,
plot-ready data, exact Table 1--5 assets, the single maintained Fig. 6--12
implementation, frozen Level-C/CUDA evidence, complete and standalone
reproduction packages, and SHA-256 manifests.

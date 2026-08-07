# Frontend Test Observations

| Area         | What it covers             | Main checks                                                      |
| ------------ | -------------------------- | ---------------------------------------------------------------- |
| Helpers      | `bookmarkApi` utilities    | URL trimming, base resolution, request headers, error formatting |
| Helpers      | `sidebarCatalog` utilities | Empty state creation and catalog result application              |
| Import paths | Nuxt alias resolution      | Utility imports resolve through `~`                              |

## Test Types

| Type       | Purpose                                        |
| ---------- | ---------------------------------------------- |
| Unit       | Pure helper and utility behavior               |
| Regression | Catch low-level logic breakage after refactors |

## Notes

- The current frontend test suite does not include page/component/smoke tests.
- Page-level behavior is covered by the separate E2E suite in `frontend/tests/e2e`.
- Add new unit tests here when logic can be verified without a browser.

# Native selection implementation plan

Goal/spec: the user-approved Obsidian design with native inactive icon brightness,
smooth sliding selection changes, responsive keys, VM-only validation, public GitHub versioning.
Architecture: preserve upstream boot logic, extend only graphical menu rendering and
configuration. Build GNU-EFI locally. Preserve upstream history and licenses.

Constraints: no host boot/ESP/NVRAM changes. Original artwork, no transparency trick.
Defaults: 32% inactive brightness, 120 ms transition; configurable, zero duration
disables animation. Input interrupts the transition without consuming the key.

- [x] Test channel brightness, alpha preservation, interpolation and easing boundaries.
- [x] Add configuration and offscreen icon composition; animate only OS-row selection.
- [x] Build and verify framebuffer endpoints/intermediate frames and both demo loaders.
- [ ] Review changes; publish source, tests, reproducible build/VM instructions and theme.

Review focus: allocation failure falls back to static rendering; repeated navigation
and Enter must remain queued; initial/scroll repaint must match endpoints; text mode
must remain untouched; disabled animation and invalid configuration need safe behavior.

Execution: directly in this session, in an isolated upstream clone on branch grubz.

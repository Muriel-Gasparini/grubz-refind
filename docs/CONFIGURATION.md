# Native UI configuration

## Native selection

Version `0.14.2-grubz.2` aligns SBAT on a separate 4 KiB page for shim memory
protection, fixes dark-pixel artifacts when scaling the background, and rebuilds
static archives without retaining stale object copies. The example uses
1920×1080; select a graphics mode supported by your firmware. Unsupported modes
fall back to the firmware default, which can crop oversized artwork and force
scrolling instead of animated adjacent selection. These fixes have also been exercised on the maintainer’s physical PC.

```ini
inactive_icon_brightness 32
selection_animation_ms 120
```

The selection artwork slides between adjacent OS entries with smoothstep easing;
icon brightness follows the motion. Original icon alpha is preserved. No special
transparency encoding, baked background patches, or fixed pixel coordinates are
required by the renderer. The Obsidian theme is provided separately in `grubz/theme`.

- Brightness: 0–100 percent; default 32. Out-of-range values revert to 100.
- Duration: 0–1000 ms; default 120. Zero disables motion. Out-of-range values revert
  to 120. Firmware rendering cost may exceed the nominal duration by a frame.
- UEFI timer milestones skip overdue frames instead of accumulating delay.
- Pending keyboard/pointer input interrupts motion and snaps to the target;
  the normal menu loop handles the pending input. Rapid changes prioritize input
  over completing the animation.
- Initial paint, scrolling, nonadjacent shortcuts, tool-row and pointer selection
  remain static. The text-mode menu is unchanged.
- Allocation/timer failures fall back to static rendering.


# Sector objects — the rules

Every sector gets one object that shows a stake leaving or arriving (the mine cart is object #1).
Objects are drawn by different hands on different days, but sit in the same slot of the same slide,
so they must be interchangeable. If an object breaks a rule here, fix the object, not the rule.

The reference object is `drawMineCart` in `objects.js`. When in doubt, match it.

---

## 1. The contract (code)

```js
function drawX(parent, { S, cx, cy, floorOn = true, keep = null, lift = "ghost" }) → g
```

| Param | Meaning |
|---|---|
| `S` | scale. The slide passes it; the object never picks its own size. |
| `cx, cy` | screen point where the object's **floor centre** lands. |
| `floorOn` | draw the floor grid under it (off when the object is a watermark). |
| `keep` | 0–1, fraction of the "load" that stays. `null` = whole load, no split. |
| `lift` | how the gone part is shown. Default and house style: `"ghost"`. |

Return the group, with `g.K` (the camera) and `g.anchor = { load, base }` — two model points that
slides use for leader lines (the load's top-centre and the base's front corner). Slides never reach
inside an object for coordinates; they use `anchor`.

Name: `draw<Thing>` in `objects.js`, registered in `SECTOR_OBJECTS` (sector name → function).
Unknown sector → the fallback stake bar, never a crash.

## 2. Model space (size)

All objects are modelled in the same unit box, so one `S` fits every object:

- **Footprint:** x within ±50, y within ±26. The longest side runs along x.
- **Height:** z from 0 (floor) to **max 56**, load included. The cart is 46 + heap ≈ 52.
- **Body vs load:** body (the container) takes the lower ~70% of height, load sits on/in the top ~30%,
  so the split is always visible from the hook's camera angle.
- Fit the camera with the same 4 bound points the cart uses:
  `camera(S, [[-50,-26,0],[50,26,0],[-32,-20,46],[32,20,46]], cx, cy)`.
  Do not tune bounds per object — that is how sizes drift.

## 3. Placement on the slide (position)

Slides are 360 × 450. The object lives in the **stage**, nothing else does.

| Slide | Stage box (x0,y0 → x1,y1) | `S` | `cx, cy` |
|---|---|---|---|
| Hook (slide 1) | 24,170 → 336,360 | 2.2 | 182, 266 |
| Small / side use | — | 1.25 | per slide |
| Watermark | full slide | 2.5–2.9, opacity ≤ 0.12 | behind the chart |

- Headline above the stage, stats strip below it (y ≥ 372). Object never overlaps type.
- Optical centre is slightly right of centre (cx 182) because the iso view leans left.
- Only these three sizes exist. No in-between scales.

## 4. Depth (z-order)

Painter's order, far to near, always in this sequence inside the object:

1. floor grid (`floor`, `lo`)
2. parts behind the body (far wheels, far rail, back legs)
3. the body silhouette (one `hull`/`slab` in `sil`)
4. details on visible faces (bands, rivets, seams)
5. the load, sorted by `x + y` then `z` (far first)
6. the ghost (gone part) — always last, on top, so dashes are never hidden
7. near parts (front wheels, handles)

Slide-level order: background mark → frame → object → leaders → type.
Never use SVG `z-index` tricks or re-append nodes later; order = draw order.

## 5. Detail budget

The hook is read at phone size in under a second. Detail is texture, not information.

- **Silhouette first:** the object must be recognisable as a filled black shape. Test: fill it solid — still obviously a cart / vault / bag?
- **Parts:** 3–6 named parts (body, load, 1–2 structural, 1–2 trim). No more.
- **Repeating detail** (rivets, bolts, slats): one rhythm, one spacing, ≤ 2 rows per face.
- **Load units:** 12–30 pieces. Fewer reads as a diagram, more reads as noise.
- **Smallest line** at hook scale: nothing shorter than ~4 px on the 1080 render; dots r ≥ 0.55.
- No text, numbers or logos on the object itself (logo lives in the header chip).

## 6. Strokes and tone

From `style.js`, no new colours:

| Use | Class / tone |
|---|---|
| outer silhouette | `sil` (edge) |
| creases, inner seams | `lo` / `nf lo` |
| near-side highlight, hub dots | `hi` |
| guides, ground | `lo thin` |
| the moving stake | **accent only** (`acc`) |

- Plates are filled with ground — a solid is its outline. No colour fills, no gradients on the object.
- Stroke width stays 1.5 (1 for `thin`). Never scale strokes with `S`.
- **One accent per slide, and it belongs to the stake.** On the object the accent may appear only on
  the part that moved (sold = rose, bought = teal). Body, wheels, floor never get the accent.

## 7. Showing the split (`keep`)

The one idea every object must express: *this much stayed, this much went*.

- **Kept part:** normal solid load, bright (`sil`/`hi`).
- **Gone part:** same shapes, `dash` outline in the accent, no fill — a ghost where it used to be.
- Split along one readable axis (back-to-front for loads, top-to-bottom for stacks), never random.
- The kept/gone ratio on screen must match `keep` within ±1 unit — count units, don't eyeball.
- For a **buy**, invert: existing load solid, the newly added part in solid accent outline on top.

## 8. Checklist before an object ships

- [ ] Signature matches §1, registered in `SECTOR_OBJECTS`
- [ ] Fits the model box (§2), camera bounds unchanged
- [ ] Renders at hook stage with `keep` = 0.25, 0.5, 0.75, 1 — all four readable
- [ ] Silhouette test passes (§5)
- [ ] Accent only on the moving part (§6)
- [ ] Side-by-side with the cart on one sheet: same visual weight, same baseline, same scale feel
- [ ] Sell and buy both render

## Sector → object map (planned)

| Sector | Object | Load unit |
|---|---|---|
| Energy | mine cart ✅ | coal lumps |
| Basic Materials | ingot pallet | ingots |
| Consumer Cyclicals | shopping bag | boxes |
| Consumer Non-Cyclicals | grocery crate | cans / sacks |
| Industrials | machine block | gears |
| Financials | vault | gold bars |
| Properties & Real Estate | tower block | floors |
| Infrastructures | telecom tower | antenna panels |
| Transportation & Logistic | container stack | containers |
| Technology | server rack | server blades |
| Healthcare | pill bottle | pills |

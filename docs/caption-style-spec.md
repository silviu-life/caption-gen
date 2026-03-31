# Caption Style Spec

Use this when prompting for background images — the captions will be overlaid on top.

## Video Format

- **Resolution:** 1080 x 1920 (9:16 vertical / TikTok / Reels)
- **Caption position:** Centered horizontally, 55% from the top (~1056px)

## Caption Text

- **Font:** Oswald Bold, uppercase
- **Size:** 48px (default)
- **Layout:** 3-5 words per page, auto-wrapping to 2 lines if too wide
- **Horizontal margin:** 40px on each side (text area = 1000px wide)
- **Line spacing:** 8px between lines

## Colors

| Element | Color | Hex | RGB |
|---|---|---|---|
| Active/spoken word | Gold | `#FFD700` | (255, 215, 0) |
| Inactive words | White | `#FFFFFF` | (255, 255, 255) |
| Text outline (stroke) | Black | `#000000` | (0, 0, 0) |
| Drop shadow | Black 50% opacity | `#000000` @ 50% | (0, 0, 0, 128) |

## Text Effects

1. **Black outline/stroke** — 2px solid black around every letter
2. **Drop shadow** — 4px offset (down-right), black at 50% opacity, rendered behind the stroke

Rendering order: shadow first (offset), then main text with stroke on top.

## Text Position & Layout Map

```
 0px ┌──────────────────────────┐
     │   TikTok status bar      │
150px│   (avoid)                 │
     │                          │
     │                          │
     │                          │
     │   SAFE ZONE for          │
     │   hero visuals / face    │
     │                          │
     │                          │
     │                          │
     │                          │
1000 │ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
     │                          │
1056 │  ▶ CAPTIONS RENDER HERE  │ ← 55% from top, centered
     │    (up to 2 lines)       │
     │    ~1000px wide          │
1140 │ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
     │                          │
     │                     ┌────┤
     │                     │ TT │ ← TikTok buttons
     │                     │btns│    (like, comment,
     │                     │    │     share, bookmark)
     │                     └────┤    ~100px from right
     │                          │
1650 │──────────────────────────│
     │  TikTok UI overlay       │ ← username, description,
     │  (username, sound, nav)  │    sound, navigation bar
1920 └──────────────────────────┘
      0px        540px       1080px
```

- **Caption Y origin:** 1056px (55% of 1920)
- **Caption width:** 1000px (1080 minus 40px margin each side)
- **Caption height:** ~60px single line, ~128px wrapped (2 lines)
- **Caption X:** centered (text block centered within 1080px)
- **TikTok safe zone for visuals/face:** y: 150–1000px (above captions)
- **TikTok dead zones:** top 150px (status bar), bottom 270px (UI), right 100px (buttons)

## Voice

- **Provider:** ElevenLabs
- **Voice ID:** `UmQN7jS1Ee8B1czsUtQh`
- **Usage:** `--voice UmQN7jS1Ee8B1czsUtQh`

## Image Prompting Guidelines

When generating background images for these videos:

- **Keep the lower-center area clean** — captions sit at 55% from top, so avoid busy detail or text in that zone (roughly y: 1000–1140px)
- **Dark or muted backgrounds work best** — the white text and gold highlight need contrast
- **Avoid bright whites/yellows in the caption zone** — gold highlight (#FFD700) disappears against these
- **Safe palette for backgrounds:** deep blues, dark gradients, moody photography, dark textures
- **Bottom 270px is covered by TikTok UI** — don't put important visual content there
- **Right 100px has TikTok buttons** — keep key elements left of center or centered

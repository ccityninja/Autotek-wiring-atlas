# Autotek wiring atlas — GUI improvements

Drop-in files for the live atlas on autotek.nz. This repo does not hold the Golf or Skyline wiring data.

## What was wrong

The live hub at `/atlas/` treated 16 empty Subaru “SOURCE WORKSPACE” cards as equal to Golf and Skyline. The Golf atlas already has a good **Select the job** screen, but boot hid it and opened the full-wire map.

## What this changes

| File | Use |
|---|---|
| `index.html` + `cars.json` | Replace `/atlas/` (hub). Ready cars first. Workspace cars stay collapsed. |
| `golf-wiring/gui-polish.css` + `golf-wiring/gui-polish.js` | Add to the Golf page after `ui18`. Jobs home first. Map opens on modules, not every wire. Privacy notice is compact. |
| `preview/golf-jobs.html` | Static mock of the quieter Golf home. |

## How to apply on the live site

**Hub:** copy `index.html` and `cars.json` over the Cloudflare Pages `/atlas/` files.

**Golf:** in `golf-wiring/index.html` add, after the last `ui18*.js` script:

```html
<link rel="stylesheet" href="gui-polish.css">
<script src="gui-polish.js"></script>
```

Copy the two `golf-wiring/` files next to the other Golf front-end files.

The polish script only calls public hooks (`u18.showHome`, `#componentType`, `#u18Skip`). It does not change atlas data.

## Local preview

```bash
python3 -m http.server 4173
```

Open `/` for the hub and `/preview/golf-jobs.html` for the Golf home mock.

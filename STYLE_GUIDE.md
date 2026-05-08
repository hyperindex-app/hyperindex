# HyperIndex Style Guide

## Fonts
- **UI:** Inter 400/500/600/700 → `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
- **Data/numbers:** system `monospace` — metrics, timestamps, chart axes, table values (`font-variant-numeric: tabular-nums`)

---

## Colors

### Backgrounds
| Use | Hex |
|---|---|
| Page bg | `#06090f` |
| Modal / secondary bg | `#0d1117` |
| Card surface | `#ffffff05` |
| Card border | `#ffffff0f` |
| Section divider | `#ffffff0d` |

### Text
| Use | Hex |
|---|---|
| Primary | `#ffffff` |
| Secondary | `#94a3b8` |
| Muted | `#64748b` |
| Dimmed | `#475569` |
| Very dimmed | `#334155` |

### Semantic
| Use | Hex |
|---|---|
| Long / positive | `#10b981` |
| Short / negative | `#ef4444` |
| Neutral / warning | `#f59e0b` |
| Live dot | `#34d399` |
| Stale warning | `#fbbf24` |

### Blue Scale
| Use | Hex |
|---|---|
| Primary button / active tab / "Popular" badge | `#2563eb` |
| Button hover | `#3b82f6` |
| Tint backgrounds (5–10% opacity) | `#3b82f60d` / `#3b82f61a` |
| Tint borders (15–40% opacity) | `#3b82f626` / `#3b82f666` |
| Accent text / lock icons / italic logo | `#60a5fa` |

### Asset Chart Colors
| Asset | Hex |
|---|---|
| BTC | `#f7931a` |
| ETH | `#627eea` |
| SOL | `#a855f7` |
| HYPE | `#22d3ee` |
| Equity | `#8b5cf6` |
| Exposure / yellow | `#eab308` |

---

## Key Components

### Cards
`background: #ffffff05 · border: #ffffff0f · border-radius: 12px · padding: 16px (24px desktop)`

### Buttons
| Variant | Bg | Hover | Border |
|---|---|---|---|
| Primary | `#2563eb` | `#3b82f6` | none |
| Ghost | `#ffffff0d` | `#ffffff1a` | `#ffffff1a` |

### Tilt Badges
| State | Text | Bg | Border |
|---|---|---|---|
| Strong Long | `#10b981` | `#10b98126` | `#10b98133` |
| Mild Long | `#6ee7b7` | `#10b98114` | `#10b9811a` |
| Neutral | `#fcd34d` | `#f59e0b14` | `#f59e0b1a` |
| Mild Short | `#fca5a5` | `#ef444414` | `#ef44441a` |
| Strong Short | `#ef4444` | `#ef444426` | `#ef444433` |

### Tabs
- Container: `#ffffff05`, border-radius 8px, padding 4px
- Active: bg `#2563eb`, text `#ffffff`
- Inactive: text `#64748b`, hover `#cbd5e1`

### Charts (Chart.js)
- Grid: `#ffffff08`
- Axis ticks: `#475569`, 10px monospace
- Tooltip bg: `#0d1117`, border: `#1e293b`, title: `#e2e8f0`, body: `#94a3b8`
- Line width: `1.5px`, no point radius

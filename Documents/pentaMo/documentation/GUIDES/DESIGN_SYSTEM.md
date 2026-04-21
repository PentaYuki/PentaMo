# 🎨 PentaMo Design System

## Visual Identity

### Logo: Pentagon Icon

**Concept**: A pentagon (5-sided polygon) represents **"Penta"**, combined with a motor bike icon inside, representing the bridge between buyers and sellers.

**SVG Icon** (`assets/icons/pentamo-pentagon.svg`):
```svg
Pentagon shape with:
├── Primary color: #88C0D0 (cyan/blue)
├── Secondary color: #81A1C1 (darker blue)
├── Stroke: #2E3440 (dark gray)
├── Inner glow effect
├── Motorcycle icon in center
└── "PentaMo" text below
```

**Dimensions**: 200x200px (scalable vector)

**Usage**:
- Favicon (16x16)
- UI header (40x40)
- Marketing materials (200+px)

### Color Palette

Based on **Nord Theme** (Arctic, cold, professional):

| Color | Hex | Usage | Purpose |
|-------|-----|-------|---------|
| **Primary** | #88C0D0 | Buttons, highlights | Action elements |
| **Secondary** | #81A1C1 | Accents, borders | Secondary actions |
| **Success** | #A3BE8C | Confirmations | Positive feedback |
| **Danger** | #BF616A | Errors, alerts | Negative feedback |
| **Foreground** | #ECEFF4 | Text | High contrast text |
| **Background** | #1E1E1E | Main background | Dark mode |
| **Surface 1** | #2E3440 | Cards, containers | Primary surface |
| **Surface 2** | #3B4252 | Nested containers | Secondary surface |

### Typography

```
Headings:
├── font-family: 'Syne' (sans-serif, geometric)
├── font-weight: 700
└── color: #ECEFF4

Body:
├── font-family: 'DM Sans' (sans-serif, clean)
├── font-weight: 400
└── color: #ECEFF4

Code:
├── font-family: 'DM Mono' (monospace)
├── font-weight: 400
└── color: #88C0D0
```

## UI Components

### Chat Message Styles

**User Message**:
```css
background-color: #3B4252;
color: #ECEFF4;
border-left: 4px solid #88C0D0;
border-radius: 8px;
padding: 12px 16px;
text-align: right;
```

**Agent Message**:
```css
background-color: #2E3440;
color: #ECEFF4;
border-left: 4px solid #A3BE8C;
border-radius: 8px;
padding: 12px 16px;
text-align: left;
```

### Pentagon Chat Icon

**HTML/CSS**:
```html
<div class="pentagon-icon">
  <svg viewBox="0 0 40 40">
    <polygon points="20,2 38,15.2 31,35.9 9,35.9 2,15.2"
      fill="#88C0D0" stroke="#ECEFF4" stroke-width="1.5"/>
    <text x="20" y="22">💬</text>
  </svg>
</div>
```

**Styling**:
```css
.pentagon-icon {
  width: 40px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-right: 10px;
}
```

### Buttons

**Primary Button**:
```css
background-color: #88C0D0;
color: #2E3440;
border: none;
font-weight: bold;
padding: 12px 24px;
border-radius: 8px;
cursor: pointer;
transition: all 0.3s ease;
```

**On Hover**:
```css
background-color: #81A1C1;
transform: translateY(-2px);
box-shadow: 0 4px 12px rgba(136, 192, 208, 0.3);
```

### Input Fields

**Text Input**:
```css
background-color: #3B4252;
color: #ECEFF4;
border: 2px solid #88C0D0;
border-radius: 8px;
padding: 12px;
font-family: 'DM Sans';
font-size: 14px;
```

**Focus State**:
```css
border-color: #81A1C1;
outline: none;
box-shadow: 0 0 8px rgba(136, 192, 208, 0.3);
```

### Cards & Containers

**Standard Card**:
```css
background: linear-gradient(135deg, #2E3440 0%, #3B4252 100%);
border-radius: 12px;
padding: 20px;
border-left: 4px solid #88C0D0;
box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
```

## Layout Grid

**Base Grid**: 12 columns
- **Gutter**: 20px
- **Margin**: 20px
- **Max Width**: 1200px

```
┌──────────────────────────────────────┐
│  Header (12 cols)                    │
├──────────────────────────────────────┤
│  Sidebar (2) │  Main (10)           │
├──────────────│──────────────────────│
│  Footer (12 cols)                    │
└──────────────────────────────────────┘
```

## Responsive Design

```css
/* Desktop (1200px+) */
body { font-size: 16px; }
.container { width: 1200px; }

/* Tablet (768px - 1199px) */
@media (max-width: 1199px) {
  body { font-size: 15px; }
  .container { width: 90%; }
}

/* Mobile (< 768px) */
@media (max-width: 767px) {
  body { font-size: 14px; }
  .sidebar { width: 100%; }
  .main { width: 100%; }
}
```

## Dark Mode Features

- **No harsh white**: Minimum background brightness #1E1E1E (94% darkness)
- **High contrast text**: #ECEFF4 on dark surfaces (contrast ratio 15:1)
- **Accent colors**: Cyan/Blue instead of bright primary colors
- **Reduced eye strain**: All text is off-white, not pure white (#FFFFFF)
- **Consistent theme**: All surfaces follow Nord color palette

## Icon System

### Icon Types

1. **Pentagon Chat Icon**: Action element
   - Used for: Chat, messages, communication
   - Color: #88C0D0

2. **Standard Icons**: UI elements
   - Settings ⚙️
   - Search 🔍
   - Plus ➕
   - Status indicators

3. **Emoji Icons**: Visual feedback
   - Success ✅
   - Error ❌
   - Warning ⚠️
   - Info ℹ️

## Animation & Transitions

**Smooth transitions**:
```css
transition: all 0.3s ease;
transition: background-color 0.2s ease-in-out;
transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
```

**Hover effects**:
- Buttons: Lift up, color shift, shadow expand
- Cards: Subtle shadow increase
- Links: Color shift to secondary

**Loading states**:
- Spinner animation (SVG or CSS)
- Fade-in for content

## Accessibility

### Color Contrast
- Text on background: 15:1 (WCAG AAA)
- Buttons on background: 10:1+ (WCAG AA)
- Focus indicators: Clear, visible blue

### Focus States
```css
:focus {
  outline: 2px solid #88C0D0;
  outline-offset: 2px;
}
```

### Semantic HTML
- Proper heading hierarchy (h1 → h6)
- Form labels associated with inputs
- Alt text for images
- ARIA labels where needed

## Theme Switches (Future)

While Phase 1 uses dark-only theme, Phase 2+ can support:

```css
/* Light Mode Palette */
--primary: #0891B2 (cyan)
--background: #F8FAFC (light gray)
--surface: #F1F5F9
--text: #1E293B (dark gray)
```

## Implementation in Code

### Streamlit Custom CSS
```python
st.markdown("""
<style>
  :root {
    --primary-color: #88C0D0;
    --background-color: #1E1E1E;
  }
  
  .stApp {
    background-color: var(--background-color);
    color: #ECEFF4;
  }
</style>
""", unsafe_allow_html=True)
```

### CSS Variables (Web)
```css
:root {
  --color-primary: #88C0D0;
  --color-secondary: #81A1C1;
  --color-background: #1E1E1E;
  --color-surface: #2E3440;
  --color-text: #ECEFF4;
  --color-success: #A3BE8C;
  --color-danger: #BF616A;
}
```

## Design Files

- **Icon**: `assets/icons/pentamo-pentagon.svg`
- **Color Reference**: This file
- **Figma** (future): PentaMo Design System

## Brand Voice

- **Professional**: Reliable, trustworthy
- **Friendly**: Approachable, helpful
- **Vietnamese**: Respectful of culture & language
- **Technical**: Clear, precise, no jargon

---

**Design Direction**: Modern, minimal, professional, accessibility-first, dark-themed

**Reference**: Nord Theme (https://www.nordtheme.com)

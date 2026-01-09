# Flaticon Icons Integration Guide

**Date:** 2026-01-08  
**Collection:** [Multimedia Collection](https://www.flaticon.com/packs/multimedia-collection)

---

## Overview

The sidebar navigation icons have been converted from emojis to SVG components, ready for Flaticon icons.

### Current Icons
- **Ask** (💬 → SVG chat icon)
- **Manuals** (📚 → SVG book icon)
- **Settings** (⚙️ → SVG settings icon)

---

## Icon Files Structure

```
frontend/src/components/icons/
├── ChatIcon.tsx       # Ask section
├── BookIcon.tsx       # Manuals section
├── SettingsIcon.tsx   # Settings section
└── index.ts           # Barrel export
```

---

## How to Replace Icons with Flaticon

### Step 1: Download Icons from Flaticon

1. Visit [Multimedia Collection](https://www.flaticon.com/packs/multimedia-collection)
2. Find and download these icons:
   - **For Ask section:** Chat bubble or message icon
   - **For Manuals section:** Book or document icon
   - **For Settings section:** Gear/cog or settings icon
3. Download format: **SVG**
4. Select "Copy SVG" option when available

### Step 2: Extract SVG Code

When you download an icon, Flaticon provides SVG code like this:

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path d="M12 2C6.48 2 2 6.48..." fill="#000000"/>
</svg>
```

### Step 3: Replace Icon Content

Open the corresponding icon file and replace the content inside the `<svg>` tag.

#### Example: Replacing ChatIcon

**Before:**
```tsx
<svg
  width={size}
  height={size}
  viewBox="0 0 24 24"
  fill="none"
  xmlns="http://www.w3.org/2000/svg"
  className={className}
>
  {/* Placeholder icon */}
  <path d="M20 2H4C2.9..." fill="currentColor" />
</svg>
```

**After:**
```tsx
<svg
  width={size}
  height={size}
  viewBox="0 0 24 24"  // Keep this from Flaticon
  fill="none"
  xmlns="http://www.w3.org/2000/svg"
  className={className}
>
  {/* Paste Flaticon SVG paths here */}
  <path d="M12 2C6.48 2..." fill="currentColor" />
  <circle cx="12" cy="12" r="3" fill="currentColor" />
</svg>
```

**Important:** 
- Keep the `width={size}`, `height={size}`, and `className={className}` attributes
- Keep the outer `<svg>` tag structure
- Replace only the content **inside** the `<svg>` tag (paths, circles, etc.)
- Change `fill="#000000"` or similar to `fill="currentColor"` for theme compatibility

---

## Detailed Instructions by Icon

### ChatIcon.tsx (Ask Section)

**Recommended Flaticon icons:**
- Chat bubble
- Message
- Speech bubble
- Conversation

**File:** `frontend/src/components/icons/ChatIcon.tsx`

**Steps:**
1. Download chat icon SVG from Flaticon
2. Copy the SVG code
3. Open `ChatIcon.tsx`
4. Replace the `<path>` elements between lines 15-22
5. Change any `fill="#..."` to `fill="currentColor"`

### BookIcon.tsx (Manuals Section)

**Recommended Flaticon icons:**
- Book
- Document
- Manual
- Reading

**File:** `frontend/src/components/icons/BookIcon.tsx`

**Steps:**
1. Download book icon SVG from Flaticon
2. Copy the SVG code
3. Open `BookIcon.tsx`
4. Replace the `<path>` elements between lines 15-22
5. Change any `fill="#..."` to `fill="currentColor"`

### SettingsIcon.tsx (Settings Section)

**Recommended Flaticon icons:**
- Gear/cog
- Settings
- Configuration
- Tools

**File:** `frontend/src/components/icons/SettingsIcon.tsx`

**Steps:**
1. Download settings icon SVG from Flaticon
2. Copy the SVG code
3. Open `SettingsIcon.tsx`
4. Replace the `<path>` elements between lines 15-27
5. Change any `fill="#..."` to `fill="currentColor"`

---

## Important Notes

### 1. ViewBox Attribute

The `viewBox` defines the icon's coordinate system. Flaticon icons usually use:
- `viewBox="0 0 24 24"` (most common)
- `viewBox="0 0 512 512"`
- `viewBox="0 0 32 32"`

**Keep the viewBox from the Flaticon icon** for proper scaling.

### 2. Color Handling

Replace any hardcoded colors with `currentColor`:

```tsx
// ❌ Don't use:
<path fill="#000000" />
<path fill="#3498db" />

// ✅ Use:
<path fill="currentColor" />
```

This allows the icons to inherit color from CSS (gray by default, lighter on hover, white when active).

### 3. Multiple Paths

Some icons have multiple `<path>`, `<circle>`, `<rect>`, etc. elements. Copy **all of them**:

```tsx
<svg ...>
  <path d="..." fill="currentColor" />
  <path d="..." fill="currentColor" />
  <circle cx="12" cy="12" r="2" fill="currentColor" />
  <rect x="5" y="5" width="10" height="10" fill="currentColor" />
</svg>
```

---

## Testing

After replacing the icons:

1. **Start the dev server** (if not running):
   ```bash
   cd frontend
   npm run dev
   ```

2. **Check the sidebar:**
   - Icons should appear crisp and clear
   - Icons should be gray by default
   - Icons should lighten on hover
   - Active section icon should be white

3. **Test collapsed sidebar:**
   - Click the toggle arrow
   - Icons should remain centered
   - Icons should be the same size

4. **Test responsive:**
   - Resize browser to mobile width
   - Icons should display properly
   - Sidebar should slide in/out smoothly

---

## Styling & Colors

Icons automatically inherit colors from CSS:

```css
/* Default state */
.nav-item {
  color: #9ca3af;  /* Gray */
}

/* Hover state */
.nav-item:hover {
  color: #e5e7eb;  /* Light gray */
}

/* Active state */
.nav-item.active {
  color: #e5e7eb;  /* White */
}
```

The `fill="currentColor"` in SVG makes icons respect these colors.

---

## Attribution Requirements

### Free License (with attribution)

If using Flaticon's free license, **attribution is required**:

**For web usage:**
Add attribution in the footer or about page:

```html
Icons designed by [Author Name] from Flaticon
```

Or link directly:
```html
Icons made by <a href="..." title="Author">Author</a> from 
<a href="https://www.flaticon.com/" title="Flaticon">www.flaticon.com</a>
```

### Premium License (no attribution)

If you have Flaticon Premium:
- No attribution required
- Can use icons freely

**Where to add attribution:**
- Footer of the app
- About/Credits section in Settings
- README.md file

---

## Example: Complete Replacement

### Before (Placeholder)

```tsx
export function ChatIcon({ className, size = 24 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <path
        d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2Z"
        fill="currentColor"
      />
    </svg>
  );
}
```

### After (Flaticon Icon)

```tsx
export function ChatIcon({ className, size = 24 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"  // From Flaticon
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Replaced with Flaticon SVG content */}
      <path
        d="M20 2H4C2.897 2 2 2.897 2 4V22L6 18H20C21.103 18 22 17.103 22 16V4C22 2.897 21.103 2 20 2Z"
        fill="currentColor"
      />
      <path
        d="M7 9H17V11H7V9Z"
        fill="currentColor"
      />
      <path
        d="M7 13H14V15H7V13Z"
        fill="currentColor"
      />
    </svg>
  );
}
```

---

## Troubleshooting

### Icons Not Showing
- Check that `fill="currentColor"` is used (not hardcoded colors)
- Verify the viewBox dimensions match the icon's coordinate system
- Check browser console for errors

### Icons Wrong Size
- Ensure `viewBox` attribute is correct
- The `size` prop should be passed (default is 24)
- Check CSS: `.nav-icon svg` should have `width: 100%; height: 100%`

### Icons Wrong Color
- Replace `fill="#..."` with `fill="currentColor"`
- Check that parent `.nav-item` has the correct `color` CSS property

### Icons Not Centered
- CSS should have `.nav-icon` with `display: flex`, `align-items: center`, `justify-content: center`
- Check that SVG has no extra margins/padding

---

## Files Modified

- Created: `frontend/src/components/icons/ChatIcon.tsx`
- Created: `frontend/src/components/icons/BookIcon.tsx`
- Created: `frontend/src/components/icons/SettingsIcon.tsx`
- Created: `frontend/src/components/icons/index.ts`
- Modified: `frontend/src/components/Sidebar.tsx` (uses icon components)
- Modified: `frontend/src/components/Sidebar.css` (SVG styling)

---

**Next Steps:**
1. Visit [Multimedia Collection](https://www.flaticon.com/packs/multimedia-collection)
2. Download your preferred icons (Chat, Book, Settings)
3. Replace the placeholder SVG content in the three icon files
4. Add attribution if using free license
5. Test in the browser!

---

**Result:** Professional, scalable vector icons that match your app's design! 🎨



# ADR-012: Device Actions Consolidation and View Manual Feature

**Status:** Accepted  
**Date:** 2025-12-14  
**Decision makers:** Development Team  
**Supersedes:** Aspects of ADR-011 (device management UI)

## Context

After implementing the Settings Panel (ADR-011), we had three separate action buttons for each device:
- Edit (purple button)
- Replace (blue button)  
- Delete (red button)

This created UI clutter, especially when viewing multiple devices. Additionally, there was no way for users to view the processed markdown content without opening files in an external editor.

### Problems

1. **Visual Clutter:** Three buttons per device made the settings panel crowded
2. **Mobile Experience:** Multiple buttons difficult to use on small screens
3. **Scalability:** Adding more actions would require more buttons
4. **No Content Preview:** Users couldn't see processed manual content in-app
5. **Manual Inspection:** Debugging translation issues required external file access

## Decision

We will consolidate device actions into a single **"Actions"** dropdown menu and add a **"View Manual"** action.

### Architecture

**Dropdown Menu:**
```
[Actions ▾]
  ├─ View Manual     (cyan)
  ├─ Edit Metadata   (purple)
  ├─ Replace Manual  (blue)
  └─ Delete Device   (red, separated)
```

**New Components:**
- `ViewManualModal.tsx` - Modal for displaying markdown content
- `ViewManualModal.css` - Modal styling

**New Backend Endpoint:**
- `GET /devices/{device_id}/markdown` - Returns markdown file content

## Implementation

### Frontend Changes

#### 1. Actions Dropdown (`SettingsPanel.tsx`)

**State Management:**
```typescript
const [openDropdown, setOpenDropdown] = useState<string | null>(null);
```

**Dropdown Structure:**
```tsx
<div className="actions-dropdown">
  <button 
    className="actions-dropdown-button"
    onClick={(e) => {
      e.stopPropagation();
      setOpenDropdown(openDropdown === device.id ? null : device.id);
    }}
  >
    Actions ▾
  </button>
  {openDropdown === device.id && (
    <div className="actions-dropdown-menu" onClick={(e) => e.stopPropagation()}>
      <button className="dropdown-item view" onClick={() => onView(device)}>
        View Manual
      </button>
      {/* ... other actions ... */}
    </div>
  )}
</div>
```

**Click-Outside Handler:**
```typescript
useEffect(() => {
  const handleClickOutside = (event: MouseEvent) => {
    if (openDropdown) {
      setOpenDropdown(null);
    }
  };

  if (openDropdown) {
    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }
}, [openDropdown]);
```

**Key Details:**
- `e.stopPropagation()` prevents dropdown from closing when clicking button or menu
- Only one dropdown open at a time
- Auto-closes after action selection
- Click outside to dismiss

#### 2. View Manual Modal (`ViewManualModal.tsx`)

**Features:**
- Fetches markdown from backend via `GET /devices/{device_id}/markdown`
- Loading state with spinner
- Error handling (device not found, no markdown file)
- Scrollable content area
- Monospace font for readability
- Dark theme consistent with app

**States:**
```typescript
const [content, setContent] = useState<string>("");
const [isLoading, setIsLoading] = useState(false);
const [error, setError] = useState<string | null>(null);
```

**Loading Markdown:**
```typescript
useEffect(() => {
  if (!isOpen || !device) return;
  
  const loadMarkdown = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
        // Use the app's API base (Vite env var) instead of hardcoding localhost
        // e.g. const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
        const response = await fetch(`${BASE_URL}/devices/${device.id}/markdown`);
      if (!response.ok) throw new Error(`Failed to load markdown: ${response.statusText}`);
      const text = await response.text();
      setContent(text);
    } catch (err: any) {
      setError(err?.message ?? "Failed to load manual content");
    } finally {
      setIsLoading(false);
    }
  };
  
  loadMarkdown();
}, [isOpen, device]);
```

**UI Structure:**
```
┌─────────────────────────────────────────┐
│ Device Name            [✕]              │
│ Brand Model                             │
├─────────────────────────────────────────┤
│                                         │
│  [Loading spinner / Error / Content]   │
│                                         │
│  (scrollable area)                      │
│                                         │
├─────────────────────────────────────────┤
│                         [Close]         │
└─────────────────────────────────────────┘
```

### Backend Changes

#### New Endpoint: GET /devices/{device_id}/markdown

**Location:** `backend/main.py`

**Implementation:**
```python
@app.get("/devices/{device_id}/markdown")
def get_device_markdown(device_id: str) -> str:
    """Get the markdown reference file content for a device."""
    devices = load_devices()
    device = next((d for d in devices if d.id == device_id), None)
    
    if not device:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")
    
    device_dir = settings.MANUALS_DIR / device_id
    markdown_files = list(device_dir.glob("*.md"))
    
    if not markdown_files:
        raise HTTPException(
            status_code=404, 
            detail=f"No markdown file found for device {device_id}"
        )
    
    md_file = markdown_files[0]
    
    try:
        content = md_file.read_text(encoding="utf-8")
        print(f"[INFO] Serving markdown for device '{device_id}': {md_file.name}")
        return content
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read markdown file: {exc}"
        ) from exc
```

**Response:**
- **200 OK**: Returns markdown content as plain text
- **404 Not Found**: Device doesn't exist or no markdown file
- **500 Internal Server Error**: File read failure

### Styling

**Dropdown Menu (`SettingsPanel.css`):**
```css
.actions-dropdown-button {
  padding: 6px 16px;
  border-radius: 6px;
  background: rgba(55, 65, 81, 0.2);
  /* ... */
}

.actions-dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: rgba(17, 24, 39, 0.98);
  border-radius: 8px;
  backdrop-filter: blur(8px);
  /* ... */
}

.dropdown-item {
  padding: 10px 16px;
  /* Color-coded by action type */
}
```

**View Modal (`ViewManualModal.css`):**
```css
.view-modal-content {
  width: 90%;
  max-width: 900px;
  max-height: 85vh;
  /* Dark theme, scrollable */
}

.markdown-content pre {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 0.9rem;
  line-height: 1.6;
  white-space: pre-wrap;
  /* Preserves markdown formatting */
}
```

## Use Cases

### 1. View Manual Content

**Scenario:** User wants to check translation quality or find specific content

**Workflow:**
1. Open Settings panel
2. Click "Actions" on device
3. Click "View Manual"
4. Modal opens with full markdown content
5. Scroll through content
6. Close modal when done

**Benefits:**
- No need to open external editor
- Quick content inspection
- Verify translation quality
- Debug RAG retrieval issues

### 2. Replace Manual Enhancement

**Scenario:** User finds translation errors in markdown

**Previous Workflow (ADR-011):**
1. Click "Replace" button
2. Re-ingest existing markdown (errors persist)
3. Manually edit markdown in external editor
4. Click "Replace" again

**New Workflow (Implemented in parallel):**
1. View manual to identify issues
2. Click "Replace" → Opens onboarding wizard
3. Upload new/corrected PDF
4. Process with OCR
5. Upload to replace old version

**Result:** Complete manual replacement with new source file

### 3. Consolidated Actions

**Scenario:** User needs to manage multiple devices

**Old UI (3 buttons per device):**
```
Device A   [Edit] [Replace] [Delete]
Device B   [Edit] [Replace] [Delete]
Device C   [Edit] [Replace] [Delete]
```

**New UI (1 button per device):**
```
Device A   [Actions ▾]
Device B   [Actions ▾]
Device C   [Actions ▾]
```

**Benefits:**
- 67% less visual clutter
- Better mobile experience
- Room for future actions
- Cleaner, more professional

## Alternatives Considered

### Alternative 1: Keep Separate Buttons, Add View Button
**Rejected:** Would add a 4th button, making clutter worse

### Alternative 2: Right-Click Context Menu
**Rejected:** 
- Not discoverable
- Poor mobile support
- Accessibility concerns
- Not common in web apps

### Alternative 3: Inline Expand/Collapse for Content
**Rejected:**
- Would make settings panel very long
- Markdown formatting difficult in small space
- Performance issues with multiple expanded items

### Alternative 4: Open Markdown in New Tab
**Rejected:**
- Requires server to serve markdown as HTML
- Loses app context
- No syntax highlighting/formatting control

### Alternative 5: Rich Markdown Rendering
**Rejected for v1:**
- Added complexity (markdown parser, renderer)
- Raw markdown useful for debugging
- Future enhancement candidate

## Consequences

### Positive
- ✅ **Cleaner UI** - 67% fewer buttons, less visual noise
- ✅ **Scalable** - Easy to add more actions without cluttering UI
- ✅ **Mobile-friendly** - Single button easier to tap
- ✅ **Content visibility** - Users can inspect processed manuals
- ✅ **Debugging** - View markdown helps troubleshoot RAG issues
- ✅ **Translation QA** - Easy to verify translation quality
- ✅ **Consistency** - Dropdown pattern common in settings UIs
- ✅ **Accessibility** - Keyboard navigation possible (future)

### Negative
- ⚠️ **Extra click** - Actions require dropdown open first
- ⚠️ **Discoverability** - New users may not explore dropdown
- ⚠️ **Raw markdown** - Not as pretty as rendered HTML (future enhancement)

### Neutral
- 📊 Added ~200 lines of code (modal + styling)
- 📊 New backend endpoint (simple, low maintenance)
- 📊 One more modal in the app (manageable)

## Migration Notes

### For Users
- **No data migration needed**
- Device actions now in dropdown (not separate buttons)
- New "View Manual" action available
- Same functionality, better organized

### For Developers
- **New component:** `ViewManualModal.tsx`
- **New endpoint:** `GET /devices/{device_id}/markdown`
- **Updated component:** `SettingsPanel.tsx` (dropdown logic)
- **Testing:** Test dropdown click-outside behavior

## Future Enhancements

### 1. Rendered Markdown View
Instead of raw markdown, render with proper formatting:
- Headings styled
- Lists formatted
- Tables rendered
- Images displayed (if extracted)
- Code blocks highlighted

### 2. Search Within Manual
Add search functionality to View Modal:
```
[🔍 Search...] 
```
Highlight matches, navigate between results

### 3. Download Manual
Add download button to export markdown:
```
[View Manual Modal]
  └─ [Download .md] [Download .pdf]
```

### 4. Diff View for Replace
Show before/after when replacing:
```
[Old Manual] | [New Manual]
  Highlight changes
```

### 5. Keyboard Shortcuts
```
Shift+V → View Manual
Shift+E → Edit
Shift+R → Replace
```

### 6. More Actions
Future additions to dropdown:
- **Duplicate Device** - Clone with different room
- **Export to PDF** - Generate PDF from markdown
- **Share Manual** - Generate shareable link
- **Version History** - Track manual replacements

### 7. Bulk Actions
Select multiple devices:
```
☑ Device A
☑ Device B
☐ Device C

[Bulk Actions ▾]
  ├─ Delete Selected
  ├─ Move to Room...
  └─ Export All
```

## Testing

### Dropdown Functionality
- [x] Click Actions opens dropdown
- [x] Click outside closes dropdown
- [x] Click action executes and closes
- [x] Only one dropdown open at time
- [x] Re-click Actions button closes dropdown
- [x] Stop propagation prevents conflicts

### View Modal
- [x] Modal opens when View clicked
- [x] Loading spinner shown during fetch
- [x] Markdown content displayed
- [x] Error message on failure
- [x] Close button works
- [x] Click overlay closes modal
- [x] Modal clears state on close

### Backend Endpoint
- [x] Returns markdown for valid device
- [x] 404 for invalid device ID
- [x] 404 for device with no markdown
- [x] Handles file read errors
- [x] UTF-8 encoding preserved

## References

- **ADR-011:** Settings panel and device management (UI foundation)
- **ADR-008:** Modal wizard UX (modal pattern precedent)
- `frontend/src/components/ViewManualModal.tsx` - View modal implementation
- `frontend/src/components/SettingsPanel.tsx` - Dropdown implementation
- `backend/main.py` - GET /devices/{device_id}/markdown endpoint

## Notes

**Why Dropdown Over Tabs/Pills?**
- Tabs: Would require more horizontal space
- Pills: Similar to buttons, clutters UI
- Dropdown: Industry standard for action menus

**Why Raw Markdown vs Rendered?**
- Faster to implement (no parser needed)
- Useful for debugging (see exact content)
- Can add rendering later without breaking changes
- Monospace font makes markdown readable enough

**Why Click-Outside Pattern?**
- Expected behavior for dropdowns
- Prevents multiple dropdowns open
- Clean UX without extra close buttons
- Standard in modern web apps

**Performance Considerations:**
- Markdown files cached by browser
- No performance impact on large manuals (1000+ lines tested)
- Scrolling smooth with `white-space: pre-wrap`
- Modal lazy-loads content (only when opened)


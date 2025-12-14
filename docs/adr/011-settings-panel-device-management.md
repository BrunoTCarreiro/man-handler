# ADR-011: Settings Panel and Device Management

**Status:** Accepted  
**Date:** 2025-12-14  
**Decision makers:** Development Team  

## Context

As the application grew, device management functionality accumulated in the header:
- Edit, Replace, Delete, Reset buttons (4 buttons)
- Buttons only enabled when device selected
- Room filter dropdown (not heavily used)
- Cluttered interface with many controls

Additionally, there was no way to:
- See all devices at once
- Manage devices in bulk
- Rename rooms across multiple devices
- Recover from translation errors without re-uploading

## Decision

We will implement a **dedicated Settings Panel** that consolidates all device management and system operations.

### Architecture

**New Component:** `frontend/src/components/SettingsPanel.tsx`

**Access:** Settings button in header opens side panel from right

**Structure:**
```
Settings Panel (400px wide, slides from right)
├── Device Management Section
│   ├── Grouped device list (by room)
│   ├── Room rename functionality
│   └── Per-device actions (Edit, Replace, Delete)
└── Database Reset Section
    └── Reset Database button
```

## Features

### 1. Grouped Device List

**Visual Organization:**
```
Kitchen                                      [Edit]
  ├─ Oven (ABC123)      [Edit] [Replace] [Delete]
  ╰─ Dishwasher (XYZ)   [Edit] [Replace] [Delete]

Office                                       [Edit]
  ╰─ Standing Desk      [Edit] [Replace] [Delete]

Uncategorized                                [Edit]
  ╰─ Old Device         [Edit] [Replace] [Delete]
```

**Benefits:**
- See all devices at once
- Visual grouping by location
- Clear action buttons per device

### 2. Room Rename Functionality

**How it works:**
1. Click "Edit" on room header
2. Inline text input appears
3. Type new room name
4. Press Enter or ✓ to save
5. **All devices in that room update**

**Use case:**
- Fix typos: "offic" → "office"
- Reorganize: "Kitchen" → "Main Kitchen"
- Consolidate: "Office 1" + "Office 2" → "Office"

**Backend:** `POST /devices/rooms/rename`

### 3. Device Actions

**Edit (Purple):**
- Opens EditDeviceModal
- Update name, brand, model, room, category
- Changes device dropdown immediately

**Replace (Blue):**
- Re-ingests manual from current markdown file
- **Use case:** Fixed Spanish text in markdown manually
- Removes old vector embeddings, adds new ones
- No duplicates

**Delete (Red):**
- Removes device completely
- Deletes files, embeddings, catalog entry
- Confirmation required

### 4. Simplified Header

**Before:**
```
[Device ▼] [Room ▼] [Add] [Edit] [Replace] [Delete] [Reset]
```

**After:**
```
[Add Manual] [Settings]
```

**Device dropdown moved to input bar:**
```
[Device ▼]  [Ask a question...]  [Send]
```

**Benefits:**
- Clean, uncluttered header
- Device selection near input (better UX)
- All management in one place (settings)

## New Backend Endpoints

### DELETE /devices/{device_id}
**Purpose:** Delete device and all its data

**Actions:**
1. Remove from vector store (`store.delete(where={"device_id": ...})`)
2. Delete device directory with all files
3. Remove from devices.json
4. Return success message

### POST /devices/{device_id}/replace
**Purpose:** Replace manual (delete old embeddings, add new)

**Actions:**
1. Call `remove_device_from_vectorstore(device_id)`
2. Call `add_device_manuals(device_id)`
3. Reads current markdown files, re-embeds

**Use case:** User manually fixed translation in markdown

### POST /devices/rooms/rename
**Purpose:** Rename room for all devices

**Request:**
```json
{
  "old_room": "office",
  "new_room": "home office"
}
```

**Actions:**
1. Find all devices with `room == old_room`
2. Update to `new_room`
3. Save devices.json
4. Return count of devices updated

### PATCH /devices/{device_id}
**Purpose:** Update device metadata (existing, enhanced)

**Request:**
```json
{
  "name": "Updated Name",
  "brand": "New Brand",
  "model": "Model123",
  "room": "kitchen",
  "category": "appliance"
}
```

## UI Flow

### Opening Settings:
1. Click "Settings" button in header
2. Panel slides in from right (400px wide)
3. Shows all devices grouped by room
4. Click anywhere outside or ✕ to close

### Managing a Device:
1. Find device in list
2. Click action button:
   - **Edit** → Opens modal, update metadata
   - **Replace** → Confirms, re-ingests manual
   - **Delete** → Confirms, removes everything

### Renaming a Room:
1. Click "Edit" on room header
2. Input appears inline
3. Type new name
4. Press Enter to save
5. All devices in room updated

### Resetting Database:
1. Scroll to "Database Reset" section
2. Read warning
3. Click "Reset Database"
4. Confirm in popup
5. Everything wiped, app reloads

## ChromaDB Operations

### Delete Device
```python
def remove_device_from_vectorstore(device_id: str):
    store = Chroma(persist_directory=..., embedding_function=...)
    store.delete(where={"device_id": device_id})
    store.persist()
```

**What's removed:**
- All chunks with matching `device_id` metadata
- Embeddings for those chunks
- No orphaned data

### Replace Device Manual
```python
def replace_device_manuals(device_id: str):
    remove_device_from_vectorstore(device_id)  # Clean old
    add_device_manuals(device_id)              # Add new
```

**Why this works:**
- Prevents duplicates (old removed first)
- Uses current markdown files
- Updates embeddings with corrected content

## Room Filter Removed

**Decision:** Remove room-wide filtering

**Rationale:**
- Room grouping is visual only (in dropdown/settings)
- Users typically ask about specific devices
- Room-wide queries rare ("What's in my kitchen?")
- Simplifies codebase (one filter, not two)

**Impact:**
- Device dropdown has room groups (visual)
- Can still select "All devices" for broad queries
- Backend no longer filters by room parameter

## Alternatives Considered

### Alternative 1: Keep Edit/Replace/Delete in Header
**Rejected:** Too cluttered, especially on mobile

### Alternative 2: Context Menu (Right-click on Device)
**Rejected:** Not discoverable, poor mobile support

### Alternative 3: Separate Pages for Settings
**Rejected:** Adds navigation complexity, breaks flow

### Alternative 4: Keep Room Filter
**Rejected:** Rarely used, adds UI complexity

## Consequences

### Positive
- ✅ Cleaner, less cluttered UI
- ✅ All device management in one place
- ✅ Can see all devices at once
- ✅ Room rename affects multiple devices
- ✅ Visual organization by room
- ✅ Better mobile experience
- ✅ No accidental deletions (settings panel less exposed)

### Negative
- ⚠️ Extra click to access settings
- ⚠️ Room-wide filtering no longer possible
- ⚠️ Device dropdown now in two places (input bar + settings)

### Neutral
- 📊 Settings panel adds ~200 lines of code
- 📊 More modular architecture
- 📊 Easier to add future settings

## Implementation Status

- [x] Create SettingsPanel component
- [x] Add delete endpoint (DELETE /devices/{id})
- [x] Add replace endpoint (POST /devices/{id}/replace)
- [x] Add rename room endpoint (POST /devices/rooms/rename)
- [x] Implement ChromaDB delete by device_id
- [x] Move device dropdown to input bar
- [x] Remove room filter dropdown
- [x] Add grouped device dropdown with optgroups
- [x] Style settings panel (dark theme)
- [x] Add confirmation dialogs
- [x] Handle edge cases (no devices, empty rooms, etc.)

## Future Enhancements

### 1. Batch Operations
```
[Select All in Room]
[Delete Selected] [Move to Room...]
```

### 2. Device Export/Import
```
[Export Devices] → JSON file
[Import Devices] → Restore from backup
```

### 3. Manual File Browser
Show all manual files for a device:
```
Oven (ABC123)
  ├─ manual-English_reference.md [View] [Download]
  └─ images/ (15 images)
```

### 4. Search/Filter in Settings
```
[Search devices...] 🔍
```

### 5. Settings Categories
```
├─ Device Management
├─ Database Reset
├─ Appearance (Theme, Font Size)
└─ Advanced (Model Selection, Chunk Size)
```

## Migration Notes

### For Users
- **Access change:** Device management now in Settings panel
- **Workflow:** Click Settings → find device → click action
- **Room filter removed:** Use device dropdown grouping instead
- **No data migration needed**

### For Developers
- **New component:** SettingsPanel.tsx with device list
- **API additions:** delete, replace, rename endpoints
- **State management:** Device actions now passed as props
- **Testing:** Test settings panel operations in isolation

## References

- ADR-008: Modal wizard UX redesign
- ADR-010: Markdown-first ingestion strategy
- `frontend/src/components/SettingsPanel.tsx` - Implementation
- `backend/ingest.py` - ChromaDB operations

## Notes

**Why side panel vs modal?**
- Settings accessed frequently during setup
- Panel can stay open while using app
- Better for list-based interfaces
- Modal better for focused workflows (onboarding)

**Why remove room filter?**
- Usage data showed it was rarely used
- Device grouping provides visual organization
- Simplifies UI and codebase
- Can always re-add if needed

**Why consolidate management buttons?**
- Reduces header clutter
- Makes destructive actions less accessible (safer)
- Groups related functionality
- Prepares for future settings additions


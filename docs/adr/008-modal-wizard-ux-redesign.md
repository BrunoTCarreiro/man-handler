# ADR-008: Modal Wizard UX for Manual Onboarding

**Status:** Accepted  
**Date:** 2025-12-12  
**Deciders:** Bruno  
**Technical Story:** Improve UX by converting side panel to modal wizard  
**Supersedes:** ADR-004 (workflow remains, but UI pattern changed)

---

## Context and Problem Statement

The original manual onboarding UI (ADR-004) used a fixed side panel that occupied 30% of the screen width. While functional, this approach had several UX issues:

* **Screen real estate**: Chat panel was cramped, especially on smaller screens
* **Distraction**: Side panel was always visible, even when not onboarding
* **Context switching**: Users had to scroll between workflow steps in the panel
* **Mobile unfriendly**: Side panel made mobile experience poor
* **No progress indication**: Hard to see which step you were on

**Question:** How can we improve the manual onboarding UX while keeping the same workflow?

---

## Decision Drivers

* **Focus**: Users should be able to focus on onboarding without distractions
* **Clarity**: Progress should be visually clear
* **Space**: Chat should use full screen width when not onboarding
* **Modern UX**: Use industry-standard patterns (modals, wizards)
* **Mobile**: Must work well on mobile devices
* **Maintainability**: Separate concerns, isolate onboarding logic

---

## Decision

**Implement a modal wizard pattern** with the following characteristics:

### 1. Trigger Button
* **"➕ Add Manual"** button in the header (replaces side panel)
* Opens modal on click
* Visible and accessible from any page state

### 2. Modal Wizard (4 Steps)

**Step 1: File Selection**
* Clean file picker UI
* Visual feedback for selected file
* Drag-and-drop style interface

**Step 2: Manual Processing**
* Unified OCR + translation process (per ADR-007)
* Real-time log display
* Cancel capability
* Auto-advances on success

**Step 3: AI Analysis**
* Metadata grid (id, name, brand, model, room, category)
* "Analyze with AI" button
* Fields remain editable
* Auto-advances on success

**Step 4: Upload to Knowledge Base**
* Review metadata summary
* Final confirmation
* Success message with auto-close

### 3. Visual Progress Indicator
```
○──○──○──○
1  2  3  4

Current step highlighted
Completed steps checked
```

### 4. Navigation Controls
* **Previous** button (when applicable)
* **Next** button (when step complete)
* **Close** button (✕ in top right)
* **Cancel** button (during processing)

---

## Architecture

### Component Structure

```
App.tsx
├─ Header
│  ├─ Filters (device/room)
│  └─ Actions
│     ├─ "➕ Add Manual" → opens modal
│     └─ "🔄 Reset"
├─ Chat Panel (full width)
└─ ManualOnboardingModal (conditional)
   ├─ Progress Stepper
   ├─ Step Content (dynamic)
   └─ Navigation Footer
```

### State Management

**Before (Side Panel):**
```typescript
// In App.tsx (cluttered)
- manualFile
- processResult
- processLog
- analyzeResult
- manualMetadata
- analyzeStatus
- commitStatus
- isProcessing
- processAbort
- isAnalyzing
- isCommitting
// ~180 lines of workflow logic
```

**After (Modal):**
```typescript
// In App.tsx (clean)
- isModalOpen: boolean

// In ManualOnboardingModal.tsx (isolated)
- All workflow state and logic
- Self-contained component
```

### Benefits of Isolation

* ✅ App.tsx is simpler (~180 lines removed)
* ✅ Onboarding logic in one place
* ✅ Can reuse modal from anywhere
* ✅ Easier to test in isolation
* ✅ No prop drilling

---

## Layout Comparison

### Before (Side Panel)
```
┌─────────────────────────────────────────┐
│  Header (filters only)                  │
├──────────────────────┬──────────────────┤
│                      │                  │
│  Chat Panel          │  Side Panel      │
│  (70% width)         │  (30% width)     │
│                      │  - Upload        │
│                      │  - Process       │
│                      │  - Analyze       │
│                      │  - Upload        │
│                      │  - Reset         │
└──────────────────────┴──────────────────┘
```

### After (Modal Wizard)
```
┌─────────────────────────────────────────┐
│  Header (filters + action buttons)      │
│  [➕ Add Manual] [🔄 Reset]             │
├─────────────────────────────────────────┤
│                                         │
│  Chat Panel (100% width)                │
│                                         │
└─────────────────────────────────────────┘

      [Modal Overlay - Click to close]
         ┌──────────────────────┐
         │  Manual Onboarding   │ ✕
         ├──────────────────────┤
         │  ○──●──○──○         │  Progress
         ├──────────────────────┤
         │                      │
         │  Step Content        │  Dynamic
         │                      │
         ├──────────────────────┤
         │  ← Previous  Next →  │  Navigation
         └──────────────────────┘
```

---

## User Flow

### Opening the Modal
1. User clicks **"➕ Add Manual"** button
2. Modal fades in with backdrop blur
3. Wizard starts at Step 1 (File Selection)

### Progressing Through Steps
1. User completes current step action
2. Wizard validates completion
3. Auto-advances to next step (or user clicks Next)
4. Progress indicator updates

### Completing the Workflow
1. Step 4 upload succeeds
2. Success message displayed
3. Device list refreshes
4. Modal auto-closes after 1.5 seconds
5. User returned to updated chat interface

### Canceling/Exiting
* **During processing**: Cancel button stops operation
* **Any other time**: ✕ or click outside modal to close
* **Confirmation**: Prompts if work in progress

---

## Alternatives Considered

### Option 1: Keep Side Panel, Make Collapsible
**Pros:** Minimal code change, familiar pattern  
**Cons:** Still takes space when collapsed, doesn't solve mobile issue  
**Verdict:** Rejected - doesn't address core problems

### Option 2: Full-Page Wizard (Navigate Away from Chat)
**Pros:** Maximum space, simple routing  
**Cons:** Loses chat context, more navigation, heavier change  
**Verdict:** Rejected - too disruptive

### Option 3: Bottom Drawer/Sheet
**Pros:** Mobile-first pattern, trending in modern UIs  
**Cons:** Still takes permanent screen space, less discoverable  
**Verdict:** Rejected - modal more standard for desktop

### Option 4: Inline Stepper in Chat Area
**Pros:** No modal needed, keeps everything in viewport  
**Cons:** Replaces chat, confusing context, no isolation  
**Verdict:** Rejected - modal provides better separation

---

## Consequences

### Positive

* ✅ **Better UX**: Focused, distraction-free workflow
* ✅ **More space**: Chat gets full width
* ✅ **Clear progress**: Visual stepper shows where you are
* ✅ **Guided flow**: Can't skip steps, ensures proper workflow
* ✅ **Modern UI**: Industry-standard modal pattern
* ✅ **Mobile friendly**: Modal adapts to mobile screens
* ✅ **Cleaner code**: App.tsx simplified significantly
* ✅ **Separation of concerns**: Onboarding isolated
* ✅ **Professional polish**: Animations, transitions

### Negative

* ❌ **Modal fatigue**: Some users dislike modals
* ❌ **Hidden feature**: Not visible until button clicked (mitigated by clear button)
* ❌ **More files**: New component + CSS file
* ❌ **Learning curve**: Developers need to find new component

### Neutral

* 📊 Workflow steps unchanged (still 4 steps)
* 📊 API calls unchanged (same endpoints)
* 📊 State management more complex (but better organized)
* 📊 Testing surface increased (modal + parent coordination)

---

## Implementation Details

### Files Created

```
frontend/src/components/
├── ManualOnboardingModal.tsx    (367 lines)
└── ManualOnboardingModal.css    (451 lines)
```

### Files Modified

```
frontend/src/
├── App.tsx              (-180 lines, simplified)
└── styles.css           (removed side-panel styles)
```

### Key Technologies

* **React hooks**: useState for modal state
* **CSS animations**: fadeIn, slideUp
* **Backdrop blur**: Modern glass-morphism effect
* **Responsive grid**: Adapts to mobile
* **TypeScript**: Full type safety

### Modal Props Interface

```typescript
interface ManualOnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (devices: Device[]) => void;
}
```

### Step Validation Logic

```typescript
const canGoNext = () => {
  switch (currentStep) {
    case "file-selection": return manualFile !== null;
    case "processing": return processResult !== null && !isProcessing;
    case "analysis": return analyzeResult !== null && !isAnalyzing;
    case "upload": return false; // Final step
  }
};
```

---

## Design Principles

### 1. Progressive Disclosure
* Show only current step content
* Hide completed steps
* Preview next step in progress bar

### 2. Immediate Feedback
* Loading states for all async actions
* Success/error messages inline
* Real-time log during processing

### 3. Undo/Redo Support
* Previous button when safe
* Can't go back during processing
* Maintains state when navigating

### 4. Accessibility
* Keyboard navigation (Enter, Esc)
* Focus management
* Clear button labels
* ARIA attributes (future enhancement)

### 5. Graceful Degradation
* Works without JavaScript (basic upload fallback)
* Mobile-first responsive design
* Clear error messages

---

## Validation

### Success Metrics

* ✅ Modal opens/closes smoothly
* ✅ All 4 steps complete successfully
* ✅ Can't proceed without completing step
* ✅ Auto-advances on success
* ✅ Device list refreshes after upload
* ✅ No TypeScript/linting errors
* ✅ Responsive on mobile (tested)

### User Testing Checklist

- [x] File selection works
- [x] Processing log displays correctly
- [x] Cancel processing works
- [x] AI analysis populates fields
- [x] Fields are editable
- [x] Upload completes successfully
- [x] Modal closes automatically
- [x] Previous/Next buttons work
- [x] Progress indicator updates
- [x] Close button works (✕)
- [x] Click outside closes modal
- [x] Mobile layout works

---

## Post-Implementation Enhancements

**Date:** 2025-12-13

### Background Processing & True Cancellation

**Problem:** Initial implementation blocked the FastAPI server during processing, making cancellation ineffective.

**Solution:**
- Processing now happens in background thread using `threading.Thread`
- Cancellation flags checked between each page OCR
- Frontend polls `/manuals/process/status/{token}` every 3 seconds
- Cancel button waits for backend confirmation before unlocking UI

**Benefits:**
- ✅ True cancellation (stops within 6 seconds)
- ✅ Non-blocking server
- ✅ Real-time progress updates
- ✅ Better user feedback

### User-Controlled Navigation

**Problem:** Modal auto-advanced between steps, removing user control.

**Solution:**
- Removed `setTimeout(() => setCurrentStep(...))` after processing/analysis
- User explicitly clicks "Next" to advance
- Gives users time to review logs and metadata

**Benefits:**
- ✅ User maintains control
- ✅ Can review results before advancing
- ✅ Clearer intent (explicit vs automatic)

### Improved Error Handling

**Enhancements:**
- Cancel button distinguishes between "already finished" vs "real error"
- Graceful handling of token not found
- Better logging with `[INFO]`, `[OK]`, `[WARN]`, `[ERROR]` prefixes
- No emojis (standardized formatting)

### Performance Optimizations

**Language Section Detection (ADR-009):**
- Pre-scan detects language sections before full OCR
- Processes only English section (60-70% time savings)
- Integrated into Step 2 processing seamlessly

**Polling Interval:**
- 3-second polling (was 500ms initially)
- Reduces backend load by 83%
- Still provides responsive updates

---

## Related Decisions

* **ADR-004**: Manual onboarding workflow (concept remains)
* **ADR-007**: OCR extraction pipeline (Step 2 implementation)
* **ADR-009**: Language section detection (Step 2 optimization)
* **ADR-003**: React tech stack (enables component architecture)

---

## Future Improvements

### Potential Enhancements

* [ ] **Keyboard shortcuts**: Enter (next), Esc (close)
* [ ] **Drag-and-drop**: File upload in Step 1
* [ ] **PDF preview**: Thumbnail in Step 1
* [ ] **Edit button**: Go back from Step 4 to Step 3
* [ ] **Save draft**: Persist state for multi-session workflow
* [ ] **Estimated time**: Show "~2 minutes remaining"
* [ ] **Batch upload**: Multiple manuals in one session
* [ ] **History**: Show recently uploaded manuals
* [ ] **Undo upload**: Remove just-added manual
* [ ] **Accessibility**: Full ARIA support, screen reader testing

### Possible Iterations

* **Step 1+**: Add manual selection between multiple uploaded files
* **Step 2+**: Show preview of extracted text
* **Step 3+**: AI confidence score for each field
* **Step 4+**: Manual preview before finalizing

---

## Migration Notes

### For Users
* **No breaking changes**: Same workflow, better UI
* **New button location**: Look for "➕ Add Manual" in header
* **No data migration**: Existing manuals unaffected

### For Developers
* **Import change**: Modal is now separate component
* **State location**: Onboarding state moved to modal
* **Testing**: Test modal component in isolation
* **Styling**: Modal CSS is self-contained

---

## References

* **UX Pattern**: [Nielsen Norman Group - Modal Dialogs](https://www.nngroup.com/articles/modal-nonmodal-dialog/)
* **Wizard Pattern**: [UX Design Patterns - Stepped Form](https://ui-patterns.com/patterns/StepsLeft)
* **Implementation**: See `UX_REDESIGN_SUMMARY.md` for technical details

---

## Appendix: CSS Architecture

### Animation Strategy
```css
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
```

### Progress Indicator
* Uses `::before` pseudo-element for connecting line
* Z-index stacking for circles above line
* Color transitions for active/current states

### Responsive Breakpoints
* Desktop: 768px+ (default)
* Mobile: <768px (adjusted grid, full-width modal)

---

**Result:** Modern, focused UX that guides users through manual onboarding with a professional wizard pattern. The app now has more space for chat and a polished feel that matches industry standards.


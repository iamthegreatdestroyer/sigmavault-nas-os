# Phase 2.2 Sprint Plan - Week 2 (Feb 10-14, 2026)

**Phase:** Desktop App Shell (GTK4 + libadwaita)  
**Status:** 🟢 LIVE  
**Team:** @CANVAS (UI/UX), @ARCHITECT (Architecture)  
**Goal:** Functional desktop app shell (7 pages, API-connected, no real data yet)

---

## Daily Breakdown

### 📅 Monday, Feb 10 - DAY 1: Foundation & API Connection

**Goal:** App launches, connects to API, navigates between pages

**Tasks:**

1. Verify environment (Python 3.14.3, GTK4, libadwaita)
2. Start Go API on :12080
3. Test SigmaVaultAPIClient → GET /health
4. Launch `python main.py` from desktop-ui/
5. Verify all 7 pages clickable

**Deliverables (EOD):**

- ✅ App window displays (1100x700)
- ✅ Status bar shows "Connected" (green indicator)
- ✅ Navigation between all 7 pages works
- ✅ No GTK/Adwaita import errors

**Success Criteria:**

```
MUST:
[ ] App launches
[ ] API health check = 200
[ ] All pages navigate
[ ] Clean quit (⌘Q)

SHOULD:
[ ] Status bar shows connection icon
[ ] No console warnings

NICE:
[ ] Desktop icon in Activities
[ ] App icon visible in taskbar
```

**Primary Owner:** @CANVAS  
**Blocker Risk:** CRITICAL (if app doesn't launch, entire phase blocked)

---

### 📅 Tuesday, Feb 11 - DAY 2: Dashboard Page

**Goal:** Dashboard page displays mock system status

**Tasks:**

1. Create `DashboardPage` widget showing:
   - System uptime
   - Total storage capacity
   - Active compression jobs count
   - Running agents count
   - Network status
2. Mock data source (hardcoded for now)
3. Add small charts/graphs (mock data)
4. Test navigation IN→OUT of Dashboard

**Deliverables (EOD):**

- ✅ Dashboard page shows 5+ status cards
- ✅ Data refreshes when page clicked
- ✅ Responsive layout

**Success Criteria:**

```
[ ] Dashboard displays without errors
[ ] Shows: uptime, storage, jobs, agents, network
[ ] Returns to Dashboard after visiting other pages
[ ] Numbers format correctly (e.g., "2.5 TB")
```

**Primary Owner:** @CANVAS  
**Blocker Risk:** LOW (other pages can continue in parallel)

---

### 📅 Wednesday, Feb 12 - DAY 3: Storage & Compression Pages

**Goal:** Storage and Compression pages have placeholder UI

**Tasks:**

**Storage Page:**

1. Create `StoragePage` widget showing:
   - Pool list (mock: 2-3 pools)
   - Each pool card: Name, status, capacity, usage %
   - Create/destroy buttons (wired to stubs for now)
2. Dataset list expandable under each pool
3. Mock error handling (show "Connection lost" briefly)

**Compression Page:**

1. Create `CompressionPage` widget showing:
   - Job queue (mock: 0-5 jobs)
   - Job progress bars
   - Compression ratio display
   - Start/stop buttons

**Tasks:** 2. Ensure both pages load without errors 3. Test UI responsiveness

**Deliverables (EOD):**

- ✅ Storage page shows pool/dataset hierarchy
- ✅ Compression page shows job queue
- ✅ No API calls yet (all mock data)

**Success Criteria:**

```
[ ] Storage page displays ≥2 pools
[ ] Compression page displays job queue
[ ] Both pages return to Dashboard correctly
[ ] No errors on rapid page switching
```

**Primary Owner:** @CANVAS + @ARCHITECT  
**Blocker Risk:** LOW

---

### 📅 Thursday, Feb 13 - DAY 4: Agents, Shares, Network Pages

**Goal:** Remaining 3 pages have placeholder UI

**Tasks:**

**Agents Page:**

1. Create `AgentsPage` widget showing:
   - Agent status grid (4x10 grid = 40 agents)
   - Color-coded: Running (green), Idle (gray), Error (red)
   - Click to show agent details popup
2. Mock data: 38 idle, 2 running

**Shares Page:**

1. Create `SharesPage` widget showing:
   - SMB/NFS shares list
   - Share properties (name, path, permissions)
   - Enable/disable toggles

**Network Page:**

1. Create `NetworkPage` widget showing:
   - Network interfaces (mock: eth0, eth1)
   - IP addresses, MAC, status
   - Gateway, DNS settings

**Tasks:** 2. Polish typography and spacing

**Deliverables (EOD):**

- ✅ Agents page shows 40-agent grid
- ✅ Shares page shows mock shares
- ✅ Network page shows interfaces

**Success Criteria:**

```
[ ] Agents page displays 40-agent grid
[ ] Shares page shows ≥2 mock shares
[ ] Network page shows ≥2 interfaces
[ ] All pages accessible from sidebar
```

**Primary Owner:** @CANVAS  
**Blocker Risk:** LOW

---

### 📅 Friday, Feb 14 - DAY 5: Settings, Polish & Integration

**Goal:** Settings page complete, entire app polished, ready for Phase 2.3

**Tasks:**

**Settings Page:**

1. Create `SettingsPage` widget showing:
   - App settings (theme, language, update behavior)
   - System settings (hostname, timezone)
   - About section (version, licenses)
   - Checkboxes and toggles (wired to no-ops for now)

**Polish & Integration:**

1. Review all pages for UI consistency
   - Font sizes
   - Colors (use Adwaita palette)
   - Spacing/padding
   - Icon consistency
2. Test full app flow: Launch → Dashboard → all 7 pages → Quit
3. Create `.desktop` file for GNOME Activities
4. Verify app appears in Activities overview
5. Test keyboard shortcuts (⌘+Q to quit)

**Deliverables (EOD):**

- ✅ Settings page functional
- ✅ All 7 pages polished
- ✅ App integrated with GNOME (Activities, launcher)
- ✅ No visual inconsistencies

**Success Criteria:**

```
MUST:
[ ] Settings page displays
[ ] All 7 pages navigate correctly
[ ] App quits cleanly
[ ] No console errors

SHOULD:
[ ] App appears in Activities
[ ] Consistent styling across pages
[ ] Responsive at 1100x700+ resolution

NICE:
[ ] Keyboard shortcuts work
[ ] App remembers window size/position
[ ] Status bar updates on page change
```

**Primary Owner:** @CANVAS  
**Blocker Risk:** MEDIUM (UI polish issues could delay Phase 2.3)

---

## Integration Points

### Input from Phase 2.1 ✅

- ✅ API contract (swagger/OpenAPI)
- ✅ Agent framework skeleton
- ✅ Storage backend stubs

### Output to Phase 2.3 (Storage Management)

- ✅ Storage page interface (needs API wiring)
- ✅ API client (needs real method implementations)
- ✅ Error handling patterns

---

## Testing Strategy

### Unit Tests (Daily)

- Component rendering tests
- Page navigation tests
- API client mock tests

### Integration Tests (EOD Day 5)

- Full app flow: Launch → all pages → quit
- API connection → pages update
- Error states (API down, timeout)

### Manual Testing (Daily EOD)

- Click all buttons
- Navigate all pages
- No crashes
- Clean quit

---

## Repository Updates Required

### After Day 1 ✅

- [ ] Push desktop-ui code to main branch
- [ ] Document environment setup in README
- [ ] Add "Phase 2.2 In Progress" to EXECUTIVE_STATUS

### After Day 5 ✅

- [ ] Tag commit as "phase-2.2-complete"
- [ ] Push .desktop file
- [ ] Update README with usage instructions
- [ ] Prepare Phase 2.3 kickoff document

---

## Risk Register

| Risk                            | Severity   | Mitigation                                                     |
| ------------------------------- | ---------- | -------------------------------------------------------------- |
| GTK4/Adwaita dependency issues  | **HIGH**   | Pre-verify on Day 1; have fallback system fonts                |
| Go API instability              | **MEDIUM** | Mock API responses for Page work; run API in separate terminal |
| Page navigation bugs            | **MEDIUM** | Test navigation after each page is added                       |
| Performance on low-res displays | **LOW**    | Responsive design using Adw widgets                            |
| Time overrun on polish (Day 5)  | **MEDIUM** | Ship Day 4 "feature-complete", Day 5 = polish only             |

---

## Success Metrics (EOD Friday, Feb 14)

| Metric                     | Target    | Current     |
| -------------------------- | --------- | ----------- |
| Pages complete & navigable | 7/7       | 0/7 (Day 1) |
| API connection working     | YES       | TBD         |
| UI consistency score       | >90%      | TBD         |
| App crash-free hours       | 4+        | TBD         |
| Code coverage (UI tests)   | >70%      | TBD         |
| Time tracking              | ≤40 hours | --          |

---

## Handoff to Phase 2.3

**What we deliver (Feb 14 EOD):**

- ✅ Functional desktop app with 7-page shell
- ✅ API client ready for real method wiring
- ✅ Mock data source for prototyping
- ✅ Testing framework in place

**What Phase 2.3 receives:**

- ✅ Desktop-ui scaffold 100% complete
- ✅ "Storage page needs storage API wiring" → Task for Phase 2.3
- ✅ "Compression page needs compression backend" → Task for Phase 2.3

---

**🚀 Phase 2.2 is LIVE. Begin execution immediately.**

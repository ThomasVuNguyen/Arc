# How Arc's features work (macOS, v1.174.0)

This document explains how Arc for macOS (The Browser Company, build 1.174.0 / 91305) implements its product features internally. It is reconstructed from a local reverse-engineering extraction of the shipped app. Nothing here comes from source code, private user data or company documents.

- **Sources:** reconstructed Swift type declarations from the main binary (`vault/extracted/swift/Arc.swift`, about 250k lines), printable strings (`vault/extracted/strings/Arc.txt`), bundled resources (`vault/extracted/bundles/*/raw/`), the AppleScript dictionary (`meta/Arc.sdef`) and `Arc.app/Contents/Info.plist`.
- **Notation:** types are written as `Module.Type`. Declarations are shortened. `Identifier<X>` is Arc's typed string ID (`ARCFoundationBase.Identifier`).
- **Confidence:** the type names, fields and enum cases are exact. Descriptions of runtime behavior are inferred from those names, log messages and UI strings. When something is inferred, the text says so ("appears to", "likely").
- **Redactions:** API keys, tokens, DSNs, signing keys and client IDs that appear in the binary are left out on purpose (`<redacted>`).

For the on-disk files and sync protocol, see [data-model.md](data-model.md).

---

## Contents

1. [Architecture overview](#1-architecture-overview)
2. [Spaces and profiles](#2-spaces-and-profiles)
3. [Sidebar: favorites, pinned, Today, folders](#3-sidebar-favorites-pinned-today-folders)
4. [Auto-archive and the Archive](#4-auto-archive-and-the-archive)
5. [Split View](#5-split-view)
6. [Tab groups and Tidy Tabs](#6-tab-groups-and-tidy-tabs)
7. [Little Arc](#7-little-arc-littlebrowser)
8. [Peek, hover cards and favorite previews](#8-peek-hover-cards-and-favorite-previews)
9. [Command Bar, URL input and search](#9-command-bar-url-input-and-search)
10. [Air Traffic Control (link routing)](#10-air-traffic-control-link-routing)
11. [Boosts](#11-boosts)
12. [Easels and Capture](#12-easels-and-capture)
13. [Arc Notes (documents)](#13-arc-notes-documents)
14. [Live Folders (GitHub) and live data](#14-live-folders-github-and-live-data)
15. [Live Slack, Notion and Calendar clients](#15-live-slack-notion-and-calendar-clients)
16. [Arc Max and AI features](#16-arc-max-and-ai-features)
17. [Media controls and Picture-in-Picture](#17-media-controls-and-picture-in-picture)
18. [Home button, App Tray, Arc menu, sidebar banners](#18-home-button-app-tray-arc-menu-sidebar-banners)
19. [Site Control Center](#19-site-control-center)
20. [Ad blocking](#20-ad-blocking)
21. [Translation](#21-translation)
22. [Sharing spaces, folders and splits](#22-sharing-spaces-folders-and-splits)
23. [Membership card and referrals](#23-membership-card-and-referrals)
24. [Account, onboarding and Welcome to Arc](#24-account-onboarding-and-welcome-to-arc)
25. [Import from other browsers](#25-import-from-other-browsers)
26. [Settings](#26-settings)
27. [Key bindings](#27-key-bindings)
28. [Sound effects](#28-sound-effects)
29. [Software updates (Sparkle)](#29-software-updates-sparkle)
30. [AppleScript API](#30-applescript-api)
31. [URL schemes and arc.net links](#31-url-schemes-and-arcnet-links)
32. [Remote configuration, feature flags and telemetry](#32-remote-configuration-feature-flags-and-telemetry)
33. [The sunset: farewell banner and export paths](#33-the-sunset-farewell-banner-and-export-paths)
34. [Module index](#34-module-index)

---

## 1. Architecture overview

Arc is a native Swift/AppKit/SwiftUI shell around a private Chromium build.

| Layer | What it is | Evidence |
|---|---|---|
| **ArcCore.framework** | Arc's Chromium fork. The bundled build reports Chromium 158.0.8127.37. Owns the `User Data` directory, cookies, history, passwords and extensions. | `Frameworks/ArcCore.framework`, `ArcCore-Info.json`, strings `Application Support/Arc/User Data` |
| **ADK** ("ADK" modules: `ADK`, `ADKClient`, `ADKModels`, `ADKClientLive`) | The Swift bridge to ArcCore: browser contexts (profiles), web contents, downloads, DevTools protocol, importers, translation, PiP. | `ADK.ADKApplication`, `ADK.ChromiumBrowser`, `ADK.DevTools.*`, `ADK.ImportingController` |
| **Feature modules** | About 170 Swift modules, mostly built with The Composable Architecture (TCA). Each feature has a reducer with `State`, `Action`, and `Dependencies.Dependency` clients. | `ComposableArchitecture.*`, `Dependencies.*`, `XCTestDynamicOverlay` |
| **Storable** | A small JSON persistence layer that writes `Storable*.json` files with versioning and rolling backups. | `Storable.StorableDataStore`, `Storable.BackupPolicy` |
| **Cloud** | Firebase (Auth, Firestore, Functions, Storage) for the account, Easels, Notes, Boosts, sharing and encrypted sidebar sync. CloudKit for the older iCloud sidebar sync. | `FirebaseClient`, `SidebarSyncCloudKit`, `FirebaseSidebarSyncClient` |

The main app target (`Arc.*`) holds the AppKit window controllers (`Arc.BrowserWindow`, `Arc.SidebarViewController`, `Arc.TablistView`, `Arc.MainMenuManager`) and the root reducers (`Arc.AppReducer`, `Arc.WindowsReducer`, `Arc.WindowReducer`).

**Arc and Dia share one codebase.** The binary contains Dia types and endpoints next to Arc's: `BaseModels.DiaAppIcon`, `releases.diabrowser.com`, `aiproxy.diabrowser.engineering`, user-default keys such as `supertabModelNameOverride` and `isOnboardingSuggestionHidden_upgradeToClia`, and the `win-*` feature flags from Arc for Windows. Many modules in this build serve Dia or Arc for Windows and are dormant in Arc for macOS.

Helper processes (from `meta/helpers.txt`): `Browser Helper`, `(GPU)`, `(Renderer)`, `(Alerts)`, plus an "Aperitif" family (`Browser Helper (Aperitif)`, `(Aperitif GPU)`, `(Aperitif Renderer)`, `(Aperitif Alerts)`) backed by `ArcCore.framework/Libraries/libaperitif.dylib`. That dylib links only `libsandbox` and `libSystem`, so it appears to be a sandbox-launch shim. Its purpose is not otherwise visible.

---

## 2. Spaces and profiles

**What it does.** A *Space* is a named sidebar with its own pinned tabs, Today tabs, icon and color theme. A *Profile* is a separate Chromium browser context (its own cookies, history, logins and extensions). Every space belongs to exactly one profile, and several spaces can share a profile.

**How it is implemented.**

- `BaseModels.SpaceModel` is the space record. It has `id`, `title`, `containerIDs` (which sidebar items are the pinned and Today roots), `customInfo` (icon plus `windowTheme`) and `profile`.
- `ADKModels.Profile` is either `.initial` (encoded as `"default"`; it is the Chromium `Default` directory) or `.custom(ProfileID)`, where `ProfileID = { directoryBasename, machineID }`. `directoryBasename` is the Chromium folder name, such as `Profile 1`.
- Creating a profile goes through `ADK.ADKApplication.createBrowserContext(userVisibleName:onCreated:)`. Deleting one goes through `deleteBrowserContext(directoryBasename:)`. `ADK.BrowserContextAttributes` holds `directoryBasename`, `userVisibleName` and `userColor`.
- **Space creation:** `SpaceCreation.SpaceCreation`. You pick a name, an icon, a theme card and a profile (`SpaceCreation.ProfileOption`). Insertion uses `SidebarDataStoreMutationContext.SpaceCreationOptions` with `insertionIndex`, `profile` and `machineID`.
- **Space styling:** `SpaceStyleEditor.SpaceStyleEditor` is the color pad, dial, noise slider and light/dark toggle. It edits `BaseModels.WindowTheme`: a background that is a basic color, a blended single color or a blended gradient, with `noiseFactor`, `intensityFactor` and an `overlay` of `grain`, `sand`, `denim` or `tweed`. A primary palette and a semantic palette are derived from it. Bundled Lottie files `automatic.json`, `sun.json` and `moon.json` drive the appearance toggle.
- **Profile UI:** `ProfilesUI.CreateProfileDialog`, `ChangeProfileDialog`, `DeleteProfileDialog`, `DeleteUnusedProfilesDialog` (behind the flag `delete-unused-profiles-button-enabled`) and `SpaceSelectionDialogView` (pick which spaces move to a new profile). Moving tabs between spaces that use different profiles shows a confirmation (`ProfileDialogUtils.ConfirmInterProfileMoveDecision`), because cookies do not follow the tab.
- **Switching spaces:** spaces are paged horizontally (`Arc.SidebarPagingContainerViewController`, `Arc.SpaceManagementView`). Each window remembers `focusedSpaceID`, and `StorableWindows.lastFocusedSpaceID` is restored at launch.

**Persistence.** Spaces live in `StorableSidebar.json` inside `SidebarContainer.spaces`, an ordered dictionary. Profile directories live under `User Data/`. See [data-model.md](data-model.md#7-profiles-and-the-chromium-user-data-directory).

---

## 3. Sidebar: favorites, pinned, Today, folders

**What it does.** The sidebar holds Favorites (the icon grid at the top, shared by every space that uses the same profile), each space's Pinned section, and the Today section (unpinned tabs that auto-archive).

**How it is implemented.** The sidebar is a graph of `BaseModels.SidebarItem` nodes, each with `id`, `title`, `childrenIds`, `parentID` and `data`. The nodes live in one flat dictionary per container (`BaseModels.SidebarContainer.items`). Roots are special `itemContainer` items:

| UI section | Root item | Type |
|---|---|---|
| Favorites | `SidebarItemContainer.ContainerType.topApps(Profile)` | One per profile, listed in `SidebarContainer.topAppsContainerIDs[profile]` |
| Pinned | `.spaceItems(spaceID)` | `SpaceModel.containerIDs[.pinned]` |
| Today | `.spaceItems(spaceID)` | `SpaceModel.containerIDs[.unpinned(.shared)]`, or `.unpinned(.desktop(machineID, windowID))` for per-machine Today lists |

The item kinds (`BaseModels.SidebarItemData`) are `tab`, `list` (folder), `arcDocument` (Note), `easel`, `itemContainer`, `welcomeToArc`, `splitView`, `sharedObject`, `instantLinks` and `tabGroup`. The full schema is in [data-model.md §5](data-model.md#5-the-sidebar-model).

- **Folders** are `list` items. `SidebarList.customInfo.iconType` sets the folder icon (an emoji, one of about 60 built-in `SidebarIconType` glyphs, or an SF Symbol). `automaticLiveFolderData` turns a folder into a Live Folder (§14). The folder icon is drawn by `FolderIcon.FolderIconView` with the states `collapsed`, `expanded`, `peekedOpen` and `peekedClosed`. Per-window expansion is stored as `SidebarItemExpansionState.expanded` or `.peeked([ids])` in `CodableWindowData.expandedItems`. "Peeked" means a collapsed folder that shows only its active child.
- **Pinned tabs** remember the URL they were pinned at (`SidebarTab.savedURL`, `savedTitle`, `savedFaviconPNGData`). Navigating away inside a pinned tab does not change the saved URL.
- **Renaming:** a user title overrides the page title (`SidebarItem.title` against `SidebarTab.savedTitle`). Arc Max can rename pinned tabs with an LLM (`LLMFeature.renamePinnedTabs`, flag `rename-pinned-tabs-using-ai`).
- **Collapsing the pinned section:** `CodableWindowData.spacesWithCollapsedPinnedSections` and `BaseModels.CollapsedPinnedSection(id, peekedItemID)`.
- **Mutations** all go through `BaseModels.SidebarMutation` (`insert`, `upsert`, `move`, `delete`, `rawDelete`, `updateItem`, `insertSpace`, `moveSpace`, `deleteSpace`, `sortSpaces`, `updateSpace`), applied in transactions by `SidebarDataStore.SidebarDataStoreImpl`. Placement uses `SidebarInsertionStrategy`: either `.absolute(parent, index)` or `.relative(targetID, before/after)`. Failures are typed (`SidebarMutationError.invalidHierarchy`, `itemAlreadyExists`, and so on). The same mutation list is what sync replays (see [data-model.md §8](data-model.md#8-sync)).
- **Sidebar modes:** `BaseModels.SidebarMode` is `anchored` or `noChrome`. `SidebarPresentation` is `locked`, `floating` or `hidden`. The width and mode are saved per window and as the default in `StorableWindows.sidebarViewPreferences`.
- **Multiple containers:** `BaseModels.SidebarContainerType` is `global` (the normal synced sidebar), `incognito(windowID)`, `littleBrowser(windowID)` or `standalone(windowID)`. Incognito and Little Arc windows get their own throwaway containers.
- **Linear tab switcher:** `SharedWindowFeature.LinearTabSwitcherState` stores a per-space MRU cycling state (flag `linear-tab-switcher-enabled`).

**Persistence.** `StorableSidebar.json` holds the sidebar plus sync state. `StorableWindows.json` holds per-window UI state such as expansion, widths and last-active dates.

---

## 4. Auto-archive and the Archive

**What it does.** Today tabs that have not been used for a while are closed and moved to the Archive, where you can search and restore them.

**How it is implemented.**

- `Archive.ArchiveFeature` is a reducer with the actions `didLaunch`, `runAutoArchive`, `autoArchiveItems([containerType: Set<itemID>])`, `removeExpiredItems`, `willTerminate` and the debug action `simulateAutoArchive(inactivityThreshold:)`. Two timers, `autoArchiveTimer` and `cleanupTimer`, drive it.
- **Thresholds:** `Archive.AutoArchiveInactiveThreshold` is one of `twelveHours`, `twentyFourHours`, `sevenDays`, `thirtyDays` or `never`, plus `oneHour`, `sixHours` and a 20-second debug option. They can be set per profile (`AutoArchiveTimeThresholdsPerProfile`, flag `per-profile-auto-archive-pref-available`) and separately for Little Arc (`AutoArchiveType.littleArc`, flag `auto-archive-little-arc-windows-enabled`). They are stored in user defaults (`autoArchiveTimeThreshold`, `autoArchiveTimeThresholdsPerProfile`, `autoArchiveLittleArcTimeThreshold`).
- **Inactivity** is measured from each window's `itemLastActiveDates`, from `SidebarTab.timeLastActiveAt`, and from `StorableArchive.autoArchiveStartTime`, which is a watermark so a fresh install does not archive everything at once.
- **Archived records:** `ArchiveDataStoreClient.ArchivedItem` holds a full copy of the `sidebarItem`, a `reason` (`auto`, `manual`, `clearButton` or `clearTabGroup`), `archivedAt` and a `source` (`.space(id)`, `.littleArc`, `.standaloneSidebar` or `.unknown`). A page snapshot image and favicon are cached separately (`ArchiveSnapshotCacheClient`, the `ArchiveFaviconCacheClientKey` cache).
- **The Archive UI** is a Home page (`HomeButton.ArchivePage`, `ArchivePageReducer`) with a source filter (`ArchiveSourceFilterType`: a space, all, or Little Arc).
- The "Clear" button over Today archives everything with `reason: clearButton`. Related user defaults show an AI "clean tabs" upsell (`autoCleanInactiveTabsEnabled`, `cleanTabsTriggerCount`).

**Persistence.** Items are in `StorableArchiveItems.json`. The auto-archive watermark is in `StorableArchive.json`.

---

## 5. Split View

**What it does.** Two or more tabs share one window, laid out side by side or stacked, and are saved as a single sidebar item.

**How it is implemented.**

- **In the sidebar,** a split is a `splitView` item whose `childrenIds` are the tabs. `BaseModels.SidebarSplitViewData` holds `itemWidthFactors: [childID: CGFloat]`, `layoutOrientation` (`horizontal` or `vertical`), `focusItemID`, `timeLastActiveAt` and `customInfo`.
- **In the window,** `WindowContents.SplitViewState` holds an ordered `windowContentIDs`, the orientation, `focusedContentID` and an `interactionState` (drag-to-drop target, `isResizingPanes`). `WindowContents.WindowSplitViewLayout.paneWidths` caches widths per window.
- **Opening content into a split** uses `WindowContentPresentationDisposition.splitView(SplitViewTarget)`, where the target is `paneAtIndex`, `newPane(index/after/before/last/afterFocusedPane)`, `pane(id)`, `replaceAllPanes` or `firstEmptyOrNewPane`. Exceeding the pane limit raises `splitViewMaximumPanesExceeded`.
- **Pane menu operations** (`BaseModels.SplitViewPaneMenuOperation`): `moveLeft`, `moveRight`, `addPaneLeft/Right/Top/Bottom`, `separate`, `copyLink` and `flipLayoutOrientation`.
- **Related flags:** `drag-to-combine-tabs-into-split-enabled`, `split-view-actions-hover-button-enabled`, `sidebar-drag-to-split-preview-ui-enabled`, `option-click-split-tab-close-button-to-unsplit-enabled` and `show-toolbar-in-split-view-enabled`.
- **Sharing:** a split can be shared as a link (`SharableArcObjectType.split`, URL kind `ArcNetURL.split`).

---

## 6. Tab groups and Tidy Tabs

**What it does.** "Tidy Tabs" uses an LLM to cluster Today tabs under group headers. Tab groups are also created from context menus, drag and drop, imports and meetings.

**How it is implemented.**

- **The sidebar item** is `tabGroup`. `BaseModels.SidebarTabGroup` holds only a `title`, and the grouped tabs are its children.
- **AI grouping:** `SharedWindowFeature.WindowAction.TabGroupAction.didGenerateTabGroups(Result<[itemID: groupName], TabGroupingWithAIError>, spaceID)`. The LLM feature tag is `LLMFeature.groupTabs`. The UI is `Arc.SidebarTidyButton` and `Arc.TidyTabsButtonImageView`, with the user default `tidyTabsEnabled`. Strings include "No tab groups found" and "Tab group of miscellaneous tabs".
- **Header actions:** you can remove a group header and keep its tabs (with an undo prompt), turn a group into a folder (`onDidClickCreateFolder`), or close it, which archives the tabs with `ArchiveReason.clearTabGroup`.
- **Analytics** describe more creation sources than the Mac UI exposes (`TabGroupCreationSource`: `liveGroupPRCreation`, `liveGroupNotionPageCreation`, `meeting`, `chatToolCall`, and so on). Those belong to shared Dia code.

---

## 7. Little Arc (`LittleBrowser`)

**What it does.** A small, minimal window for quick links, especially links opened from other apps. You can then promote it to a full Arc tab.

**How it is implemented.**

- **State:** `LittleBrowser.LittleBrowser.State` holds `id` (a window ID), `session` (`LittleBrowserSession`: `id`, `entryPoint`, `preferredFrame`, `startTime`), `profile`, `downloads` (a mini downloads tray), `moveMenuState`, `modalState` and `nuxState`.
- **Entry points** (`LittleBrowserEntryPoint`): `internalLink(URL)`, `externalLink(URL)`, `floatingWindow(URL)`, `mainMenu`, `statusItem`, `globalHotkey`, `sidebarPlusButton`, `browserPopup` and `draggedTab`.
- **Global hotkey:** `GlobalHotkeyListenerClient.registerLittleBrowserShortcut` registers a system-wide shortcut that creates a Little Arc window (`onCreateLittleBrowserWindow`). It is toggled by the user default `globalLittleBrowserHotkeyEnabled`.
- **External links:** with `openExternalLinksInLittleBrowserEnabled`, links from other apps open in Little Arc. Air Traffic Control can also send a link to Little Arc (§10).
- **Promotion:** "Move to…" (`LittleBrowserMoveMenu`) calls `moveContentToStandardGlobalWindow(itemID, destination)`. The destination is pinned, unpinned, or an exact container (`MoveToStandardWindowDestination.DestinationType`). A per-profile confirmation can be skipped with `shouldBypassConfirmLittleBrowserProfileDialog`.
- **Sidebar and archiving:** each Little Arc window has a private sidebar container (`SidebarContainerType.littleBrowser(windowID)`) and can be auto-archived (`ArchivedItemSource.littleArc`).
- **Persistence:** a Little Arc window is a `WindowStyle.little(PersistedLittleBrowserState)` entry inside `StorableWindows.json`.

---

## 8. Peek, hover cards and favorite previews

### Peek

**What it does.** Links from a pinned tab or favorite to another site open in a floating overlay over the current page.

**How it is implemented.** Peek uses the "modal V2" presentation: `WindowContents.ModalWindowContentStateV2` maps content to a `ModalState(source, presentationState, presentationSource)`. The `source` is `.sidebarItem(id)` or `.window`. The `presentationSource` is `.webContentLink` or `.easelObject(id)`. The sidebar badge for an open peek is `WindowContents.State.PeekState(parentID, contentID, favicon, isSelected)`. The setting string reads "Open a Peek window when clicking on links to other sites". Shift-click into the modal can be disabled (`disableShiftClickToOpenLinksInModal`). The flags are `modal-v2-native-gestures-enabled`, `modal-v2-chromium-overscroll-enabled` and `peeked-modal-controls-alternate-order-enabled`.

### Hover cards ("5-second previews")

**What it does.** Hovering a link with Shift shows a card with a page snapshot and an AI summary.

**How it is implemented.** The `HoverCards` module: `HoverCardsController`, `HoverCardViewModel` (with `CacheKey`, `SummaryTimeout` and `Output`), and `HoverCards.Summary { quickSummary, details[] }`. Some domains have custom selectors (`HoverCardsSupportedDomain { host, selectors[] }`). The summary comes from `LLMFeature.hoverCards`. The flags are `hover-cards-enabled`, `hover-cards-llm-delay-interval`, `hover-cards-caching-enabled` and `hover-cards-share-enabled`, and the user default is `hoverCardsEnabled`.

### Favorite previews

**What it does.** Hovering certain favorites shows a live preview (unread Gmail, today's calendar, recent pages, a folder's contents).

**How it is implemented.** The `Previews` module, keyed by `BaseModels.PreviewType`: `gmail(inboxNumber)`, `gcalendar`, `outlookMail` and `outlookCalendar` (personal or work Microsoft account), `recentPages(domain)`, `folder(itemID)`, `twitter` and `whatsApp`. There are fetchers such as `Previews.GmailDataFetcher`. The Microsoft endpoints are `graph.microsoft.com/v1.0` and `login.microsoftonline.com`. Each preview has its own on/off user default (`gmailPreviewEnabled`, `calendarPreviewEnabled`, `outlookEmailPreviewEnabled`, `recentPagesPreviewEnabled`, `folderPreviewEnabled`, `notionCalendarPreviewEnabled`). Badges for X and WhatsApp unread counts are toggled by `twitterBadgeEnabled` and `whatsAppBadgeEnabled`. The cache is `StorablePreviewsDataClient.json` (`PreviewsDataStore.StorableData`, keyed by preview type and profile).

---

## 9. Command Bar, URL input and search

**What it does.** Cmd-T and Cmd-L open the Command Bar, which mixes open tabs, sidebar items, history, top sites, Notes, Easels, commands ("Type Travel"), search suggestions, site search and AI shortcuts.

**How it is implemented.**

- **UI and state:** `CommandBar.CommandBar` (the reducer), `CommandBarState`, `CommandBarViewReducer` and `CommandBarView`. Entry points (`CommandBarState.EntryPoint`) include `keyboardShortcutT`, `keyboardShortcutL`, `keyboardShortcutCommandOptionG`, `sidebarNewTabButton`, `sidebarPlusButton`, `sidebarDoubleClick`, `topBarURL`, `newStandardWindowOpen`, `newLittleWindowOpen`, `splitViewPaneCreated` and `appMenu`. The result opens with `CommandBarDestinationType`: `overrideCurrentTab(showCurrentURL)`, `createNewTab` or `noop`.
- **Candidate providers** (`SearchClientManager`): `SidebarCandidatesProvider` (global or per-window), `TopDomainsCandidatesProvider` (bundled `TopDomains.json` and `TLD-short-list.json`), `DocumentsCandidateProvider` (Notes), `EaselCandidatesProvider`, `TypeTravelCandidatesProvider` (menu items, extensions and settings panes as commands) and Chromium autocomplete (`ADK.BrowserSearchResults`).
- **Ranking (ASE2).** All candidates are scored by the `ASE2` engine:
  - `ASE2.Archetype` defines the result kinds: `chromiumArchetype`, `navigateWhatYouTyped`, `searchWhatYouTyped`, `askGPTWhatYouTyped`, `tab`, `document`, `easel`, `typeTravel`, `topDomain`, `instantLinks`, `askAssistant` and `assistantHistory`.
  - `ASE2.Feature` lists the scored signals: URL, title and hot-word match score, position and percentage, `fuzzySearchConfidence`, `lastNavigated`, `frequencyEver`, `typedCountEver`, `mostVisitedRank`, `siteEngagementScore`, `globalSiteRank`, `chromiumRelevanceScore` and `saveLevel`.
  - The weights come from an `ASE2.Configuration` with sections `archetype`, `match`, `importance`, `recency`, `chromium`, `save` and `boosts`. It is cached in `StorableASEConfiguration.json`.
  - Your own selections feed back into ranking through `StorableCommandBarAdditionalRanking.json` (recently switched-to tabs, which archetype you picked for a query, and Type Travel usage).
- **Remote tuning:** `command_bar_behavior.json` (bundled, and fetched from `content.arc.net`) currently holds `dedupByTitleAndHostList`.
- **Search engines:** `BaseModels.SearchEngine { name, keyword, status, isPrepopulated, searchURLTemplate, faviconURL }` maps onto Chromium's keyword engines (`arc://settings/searchEngines`). Site search ("Tab to search") is configured per keyword. Flags such as `command-bar-calculator-enabled` turn on inline answers.
- **Search suggestion privacy:** a one-time consent view (`CommandBarSearchSuggestionsPrivacy`) controls sending keystrokes to the search provider.
- **URL inputter:** `URLInputter.URLInputterFeature` is a lighter URL field used by Little Arc and editing flows (`Suggestion`, `LinkTextState`).
- **Instant Links (Arc Max).** Typing a query and pressing Shift-Enter opens the results directly:
  - The request is `InstantLinks.InstantLinksRequest { query, itemID, spaceID }`.
  - The v2 response contains typed actions (`web`, `image`, `map`, `directions`, `flights`, `news`, `siteSearch`, `history`) and an intent (`navigate` or `search`).
  - While it loads, a placeholder `instantLinks` sidebar item shows `status: loading` or `error`.
  - The flags are `instant-links-v2-enabled`, `instant-links-suggestion-enabled` and `instant-links-intent-prototype-enabled`.
- **ChatGPT in the Command Bar:** the archetype `askGPTWhatYouTyped` opens `chat.openai.com` with the query, configured by the flags `gpt-command-bar-integration-*`. The user default is `gptSiteSearchEnabled`.

---

## 10. Air Traffic Control (link routing)

**What it does.** Rules send links opened from other apps to a specific space or to Little Arc, based on URL patterns.

**How it is implemented.** The `LinkRouting` module:

```swift
struct LinkRouting.LinkMatchingRule {
    var id: Identifier<LinkMatchingRule>
    var sourceComponents: IdentifiedArray<LinkSourceComponent>  // each: .urlMatch(style, pattern)
    var destination: LinkDestination
}
enum LinkRouting.LinkSourceTextMatchingStyle { case matches, contains }
enum LinkRouting.LinkDestination { case space(ProfileDestination), littleArc(ProfileDestination) }
enum LinkRouting.LinkDestination.ProfileDestination { case profile(Profile), space(SpaceID), mostRecent }
```

- **Rule editing:** `LinkRoutingEditor` edits the rules (add, delete, match style, pattern, destination) and a `defaultDestination` that applies when no rule matches.
- **Outcomes:** `LinkOutcome` lists what a link can do: `opensNewBackgroundTab`, `opensNewForegroundTab`, `opensNewWindow`, `opensInPeek`, `opensSplitView` or `opensLittleArc`. `LinkExplainedOutcome` powers the explanatory tooltip.
- **Settings:** the editor appears under Settings → Links (`PreferencesFeature.LinksPreferencePane`, `LinkRoutingDialog`).
- **Persistence:** `StorableLinkRouting.json` (`StorableLinkRoutingState { version, rules, defaultDestination }`).

---

## 11. Boosts

**What it does.** Per-site customization: color schemes, fonts, text transform and zoom, "Zap" (hide elements), and custom CSS and JS. Boosts can be shared without JS and installed from a link.

**How it is implemented.**

```swift
struct BoostsClient.BoostData {
    let data: InternalData?            // css, js, font, textTransform, textZoom, zaps[], colorScheme
    var type: BoostType                // .edited | .installed
    let hostPattern: String
    let author: String; let title: String
    let signature: BoostSignature?     // hand-drawn signature curves
    let lastModified: Date; let isActive: Bool
    let forkedFromSnapshotID: BoostSnapshotID?; let forkedFromBoostID: BoostID?
}
```

- **Components** (`BoostDataComponent`): `css`, `js`, `font(family)`, `textTransform` (capitalize, uppercase or lowercase), `textZoom(level)`, `colorScheme` and `zaps([selector])`.
- **Color schemes:** `BoostColorScheme.colorWheelDriven(BoostColorWheelScheme)` (primary hue and saturation, secondary hue offset, invert lightness, plus advanced lightness and saturation controls) or `.themeDriven` (follows the space theme).
- **Editor:** `BoostsEditor.BoostsEditor`. Modalities are `code(css|js)`, `zap` and `none`. It has an undo/redo `ChangeStack`, a selector picker (bundled `SelectorPicker.js`) in `zap` or `copyToPasteboard` mode, and a Monaco-based code panel behind `boosts-v2-monaco-enabled`. The Boost IDE talks to Chromium through `ADK.BoostIDERequest`/`BoostIDEResponse` and loads code from `arc://boost/v2/css/` and `arc://boost/v2/js/`.
- **Application:** `BoostsWebContentHelperImpl` maps `hostPattern` to the boost, injects stylesheets by type (`StylesheetType`: `user`, `font`, `textTransform`, `zaps`) and arbitrates which boost owns the color scheme or text zoom for a host.
- **Storage:** boosts are tied to the signed-in user and stored in Firestore (`BoostsStorageFirebaseImpl`; collections `boosts` and `boostSnapshots`). Only the list of locally enabled boost IDs is on disk (`StorableBoostsData.json`), with preview images in `BoostsImageCache`.
- **Sharing:** `BoostsSharingDialog` creates an immutable `BoostSnapshotData` (original ID, data, title, creator name, signature, preview image) and a share link. Sharing is refused when the boost contains JS or is empty (`CannotShareReason.hasJS`, `.isEmpty`). Installing from a link (`ArcNetURL.boostInstallRequest`) goes through `BoostsInstallationDialog`.
- **Discovery:** the Site Control Center shows boosts for the current site (§19), and Home has a Boosts page.

---

## 12. Easels and Capture

**What it does.** Easels are collaborative canvases that hold live web captures, images, text and drawings. Capture takes screenshots of a region, a full page or the whole window.

**How it is implemented.**

- **Document model:** `EaselClient.EaselDocument` holds `objects: [ObjectID: EaselObject]`, `palette`, `allParticipantsEver`, live `presence`, `shareStatus` (`readOnly`, `publicReadWrite` or `creatorOnly`), `titleObjectID`, `customOGImageID` and `serverTitle`.
- **Object content** (`EaselObject.Content`): `image`, `text`, `richText`, `shape` (arrow, freehand, rectangle or circle), `webCard` (a captured snapshot with URL, favicon and layout information so it can refresh), `browser` (a live embedded page) and `link`.
- **Backend:** Firestore collections `easels`, `objects`, `memberships`, `presence`, `readStates` and `readStatesPerParticipant` (`EaselClient.EaselCollectionIDs`), with a presence pinger and per-participant read state. Images likely upload to Firebase Storage (the `FirebaseStorage` module and `EaselClient.ImageUploadContent` are present). On disk there is only `EaselImagesCache`.
- **In the sidebar:** an `easel` item (`SidebarEasel { easelID, shareStatus, title, creatorID }`).
- **Export:** Easels can be exported as static web pages. The bundle ships `EaselExportViewer.html/js/css`, `EaselExportCollection.html` and a README, and the "Export All Easels" menu runs `exportAllEasels()` (flag `easel-exporter-enabled`).
- **Capture:**
  - `WindowContents.CaptureAction` has `onDidTapButton(type, source)`, `onDidTapFullPageButton`, `onDidTapFullWindowButton(background)`, `onDidTapSave(to: easelID?)`, `onDidTapCopyCapturedImage`, `onDidTapSendViaiMessage` and `onDidTapSaveAsFile`.
  - Window captures can have a "portrait" background and a watermark (user defaults `portraitCaptureBackground`, `portraitCaptureHidesWatermark`).
  - Captures saved to the library are recorded in `StorableCaptures.json` (`CaptureClient.CaptureData { id, url, createdDate, text, captureType, captureLayoutInfo }`), with images in `CaptureImageCache`.
  - The capture shutter plays `capture.wav` (§28).

---

## 13. Arc Notes (documents)

**What it does.** Lightweight rich-text notes in the sidebar. Notes are being retired, and this build adds an export path.

**How it is implemented.**

- **Model:** `DocumentsClient.ARCDocument { id, data, title, shareStatus (private/public), creatorID, createdAt }`. The content is a "scratchpad": `ARCDocumentScratchpadContents { blocks: [BlockID: ScratchpadBlock], rootBlocks }`. Today every block is type `fullBlob`, with `text` and `properties: [.richText(range, RichTextFormatType)]`.
- **Formats** (`BaseModels.RichTextFormatType`): bold, italic, underline, strikethrough, h1 to h3, hyperlink, `formattedHyperlink(url)`, `orderedList(level)`, `unorderedList(level)` and `image`. Markdown shortcuts are converted as you type (`ArcRichTextEditor.MarkdownTransformType`).
- **Editor:** `ArcRichTextEditor.ArcRichTextEditorView`, a TextKit-based view with a format menu, and `TextEditor.TextEditorViewController` (title, gutter).
- **Storage:** each note is saved twice. Locally it is one JSON file per note in the `StorableARCDocuments/` folder (`StorableFolderDataStore<StorableARCDocument>`). Remotely it is a Firestore document (`ARCFirebaseDocument`; save locations `.disk` and `.firebase`). Notes need sign-in (`DocumentError.loginRequired`).
- **In the sidebar:** an `arcDocument` item (`SidebarArcDocument { arcDocumentID, isEditable, customInfo }`). The "new note" action can instead open an external notes app (`BaseModels.NoteDocumentType.webDocument` with a `newDocURL` such as `doc.new` or `notion.so/new`, user default `defaultNoteDocumentApp`).
- **Deprecation:** UI copy says "…we're saying goodbye to Arc Notes" and "You can still edit and create Arc Notes until %@ … after then, you will only be able to export them." The flags are `export-arc-notes-enabled`, `disable-new-note-entry-points`, `disable-notes-editor` and `export-arc-notes-dialog-note-viewing-end-date`. Export zips the notes into `Arc-Notes-Export-…` (`attemptToZipDocuments(_:strategy:)`).

---

## 14. Live Folders (GitHub) and live data

**What it does.** A folder fills itself with your open GitHub (or Bitbucket) pull requests and shows status subtitles such as review and check state.

**How it is implemented.**

- **The folder:** a `list` item with `automaticLiveFolderData`:

  ```swift
  struct BaseModels.AutomaticLiveFolderData {
      let dataSource: AutomaticLiveFolderDataSource   // only .github
      var lastFetch: LastFetch?                       // timestamp + .success(date) | .error(...)
      var hiddenItems: Set<LiveItem.ID>
      var filter: AutomaticLiveFolderDataFilter?      // .github(PullRequestFilter)
  }
  ```

- **Child tabs** carry `SidebarTab.liveItemID`, which points into the live data store. `BaseModels.LiveItem { id (.url or .placeholder), data, lastModified, lastViewed, firstSeen }`. `LiveItem.Data` can be `pullRequest(.github/.bitbucket)`, `notion`, `googleDrive`, `confluence`, `googleCalendar`, `chat` or `liveFolderAction`. Only GitHub is wired to folders on Mac. The others belong to the shared Dia "live" infrastructure.
- **No API tokens.** `GitHubClient` does not use the GitHub API. It loads github.com pages in your logged-in browser context and parses the HTML: `fetchAndParsePullRequestsImplementation(BrowserWindowContext, …)`, `ParsingRule`, `GitHubHTMLSelector`, `PullRequestParsingConfig`. It also fetches checks, the merge box, PR stacks, threads, diffs and user hovercards. The errors reflect this approach: `needsSingleSignOn(URL)`, `unableToGrabHTML`, `unexpectedPageStructure`, `rateLimitExceeded` and `requestedTooSoon`.
- **Refresh** is rate-limited (flag `automatic-live-folders-min-refresh-interval-in-seconds`). The feature is behind `enable-git-hub-live-folders` and `git-hub-live-folders-team-review-enabled`.
- **Persistence:** live item data is per profile in `StorableLiveData.json` (`liveDataPerProfile: [Profile: LiveItemsData]`).

---

## 15. Live Slack, Notion and Calendar clients

These clients reuse the session cookies already in your Chromium profile. They do not use OAuth apps.

| Module | Endpoint style | Notes |
|---|---|---|
| `LiveSlackClient` | Slack's internal web-client APIs (unreads, activity feed, mentions, saved items, conversation history and replies, DMs, user, bot and file info, search, `postMessage`, `openConversation`) plus `edgeapi.slack.com/cache/` | `FetchParams { browserContextID, preferredTeamID, preferredTeamDomain }`. There is about 800 lines of response types, including huddle transcription types (`SlackFileTranscription`). |
| `LiveNotionClient` | Notion's private `app.notion.com/api/v3/*` (`loadPageChunk`, `syncRecordValues`, `queryCollection`, search, notification log, page visitors, spaces) | `NotionAuthData { cookies: [ArcCookie], notionUserId }`. Includes `NotionBlocksToMarkdown`, which converts pages for the AI features. |
| `LiveCalendarClient` | `www.googleapis.com/calendar/v3/calendars/primary/events` | `FetchParams { browserWindowContext, accountNumber, fetchMultipleCalendars }` |

**Where they show up on Mac:**

- **Calendar live preview:** a favorite or banner shows the next meeting with a quick-join button (`BaseModels.LiveCalendar`, `ActiveEventSession`, `LiveCalendarInterval`: `never`, `onStart`, or 2, 5 or 10 minutes before). The flags are `calendar-live-preview-enabled`, `calendar-live-preview-multi-cal-support` and `calendar-live-preview-min-fetch-interval-in-seconds`.
- **Favorite subtitles and badges:** `SharedWindowFeature.WindowAction.TopAppsAction.setSubtitlesEnabled` and `setBadgingEnabled` are toggled per `BaseModels.TopApp` (whatsapp, twitter, gmail, gcal, notionCalendar, spotify, youtube, notion, slack, figma, outlook).
- **Shared Dia code:** much of the Slack and Notion surface (`postMessage`, transcripts, Markdown conversion) serves Dia's assistant rather than an Arc Mac UI.

`WebContentPageType` classifies the current page (Notion, GitHub, Bitbucket, Linear ticket, Google Docs/Calendar/Meet, Zoom, and a long `WebApp` list from Airtable to Zendesk). It is used for context-aware UI and AI. Linear appears only here, as a page type and a sidebar icon. There is no Linear live folder.

---

## 16. Arc Max and AI features

**What it does.** "Arc Max" is the opt-in bundle of AI features. The Max settings pane (`PreferencesFeature.State.MaxFeature`) toggles: `askOnPage`, `hoverCards` (5-second previews), `renamedPinnedTabs` (tidy pinned titles), `renameDownloads` (tidy download names), `gptSiteSearch` (ChatGPT in the Command Bar), `tidyTabs` and `instantLinks`. Max can be disabled by organization policy (`arcMaxDisabledByOrgPolicy`).

### Browse for Me (`AskArc`)

You type a query and Arc builds a summarized results page.

- **Request:** `AskArc.AskArcRequest { id, query, source, context (.referrer or a union), options, parentSessionID }`. `AskArcOptions` includes `contentGuidelines`, `webContext` (standard or incognito), the Google results-page selectors, response-language preferences, `suggestedFollowUpsEnabled`, `searchEngines` and `hiddenWebContentScrapingTimeout`.
- **Pipeline (inferred):**
  1. Run web searches. `WebSearch` contains a Brave Search API client (`BraveSearchAPI`, proxied), Google HTML scraping in a hidden WebKit view (`GoogleSearchEngineHiddenWebContentWebKit`, with selectors overridable by the flags `google-search-engine-*-override`), a Reddit scraper, and a web-results service (`websearch.diabrowser.engineering/api/web-results`).
  2. Scrape the top pages.
  3. Stream an LLM answer that is rendered as typed display units.
- **Display units** (`AskArcDisplayUnit.UnitType`): `pageTitle`, `sectionTitle`, `imageCarousel`, `emojiList`, `video(s)`, `topResults`, `allResults`, `citation`, `listing`, `oneBox` (weather, currency, unit conversion, time, definition, translation, sports, flights and showtimes), `followUpQuestions`, `linkCarousel`, `userFeedback` and `footer`.
- **Caching and tooling:** pages are cached (`AskArcPersistentCacheEntry`). Internal builds can collect fine-tuning samples (`FineTuneSample`) and compare outputs (`AskArcComparisonTool`, "Browse For Me Comparison Tool").
- **Entry points:** the URL kind `ArcNetURL.browseForMe(query)` and the flags `browse-for-me-enabled` and `browse-for-me-pip-enabled`.

### Ask on Page (`AskInPage`)

A chat thread about the current page, opened from Find (Cmd-F). `AskInPage.AskInPageChatThread` holds `messages: [LLM.LLMMessage]`, `fractionOfContextUsed` and `isTyping`, and uses `LLMProvider` with `LLMFeature.askInPage`. Page text comes from Chromium content extraction (`ADK.HTMLExtractionMode`, flag `content-extraction-hydrated-outline-enabled`) and `HTML2Markdown`.

### Other AI uses

| Feature | `LLM.LLMFeature` |
|---|---|
| Tidy pinned-tab titles | `renamePinnedTabs` (also rule-based `TidyTabTitles`, see below) |
| Tidy download file names | `renameDownloads` (`Arc.DownloadNamingFeature`, sidebar banner `DownloadRenameItemState`) |
| Tidy Tabs | `groupTabs` |
| Hover-card summaries | `hoverCards` |
| Browse for Me | `askArc` |
| Mobile-only, present in the shared code | `callArc`, `pinchToSummarize`, `mobileAskInPage` |
| Dia features, present in the shared code | `supertabs`, `memory`, `connectedData`, `selfDriving`, `please`, `classifier`, `pageCategorization` |

**Rule-based tidy titles.** These do not use AI. `web_content_behavior.json → tidyTitles` holds per-site regex rules (52 hosts, such as `mail.google.com` and `linkedin.com`) that strip noise from tab titles (`TidyTabTitles.TidyTabTitle { match, title: .always | .removingPattern(s) }`).

### LLM layer (`LLM`, `AIInfraProtocols`)

**Providers and models.** `LLM.LLMModel` is one of three provider families:

| Family | Model IDs referenced in the binary |
|---|---|
| `chatGPT` (OpenAI chat-completions format) | gpt-3.5-turbo (and -16k, -1106), gpt-4, gpt-4-32k, gpt-4-turbo-preview, gpt-4o, gpt-4o-mini, gpt-4o-2024-11-20, gpt-4.1-2025-04-14, o1, o1-mini, o1-preview, o3, o3-mini, o4-mini, and several company fine-tunes of gpt-3.5-turbo, gpt-4o, gpt-4o-mini and gpt-4.1 (for citations, inline citations, memory-query parsing, tab grouping and Ask Arc) |
| `claude` (Anthropic Messages streaming format) | claude-v1, claude-instant-v1 (and -100k), claude-2, claude-3-haiku-20240307, claude-3-sonnet-20240229, claude-3-opus-20240229, claude-3-5-sonnet-20240620 |
| `universal` (a provider-agnostic proxy schema with reasoning and verbosity options) | Google: gemini-2.0-flash, gemini-2.0-flash-lite, gemini-3-pro, gemini-3-flash. OpenAI: gpt-4o, gpt-4.1, gpt-4o-mini, o3, o4-mini, gpt-5.1, gpt-5.2, gpt-5.6-luna, gpt-5.6-sol, gpt-6-luna, gpt-6-astra, gpt-6.1-sol. Claude: claude-sonnet-4, claude-sonnet-4-5, claude-sonnet-5, claude-sonnet-5-5, claude-haiku-5-5, claude-opus-4-5, claude-opus-4-6, claude-opus-4-8, claude-opus-5, claude-opus-5-5. Plus `custom(String)`. |

**Endpoints.** The client never calls OpenAI, Anthropic or Google directly. Every request goes through The Browser Company's proxies:

- `aiproxy.diabrowser.engineering/api/dia-claude-stream`
- `webresultproxy.diabrowser.engineering/api/claude-stream`
- `webresultproxy.diabrowser.engineering/api/open-ai-chat-stream`
- `ai-service.diabrowser.engineering/aiproxy` (with staging and `ai-service-eval` variants)

Requests carry `X-Client-Version` and `X-Request-Environment` headers and a feature tag (`LLMParameters.subFeature`, `featureTags`).

**Proxy-side safety.** The proxy can reject requests with typed reasons: `suspicious_activity` (`bot_identity`, `brute_forcing`, `account_mining`, `ai_farming`, `credential_stuffing`, `account_compromised`), "Safety violation", "Content filter", "Client update required", and token limits.

**End-to-end encryption ("Watchtower").** `LLMParameters.encryptionHandlers` and `LLM.WatchtowerEncryptionContext { requestID, method, target }` (the context string is `ai-watchtower/e2e/v1`) encrypt the request and the streamed response between client and proxy.

**Request options.** Requests also carry `qos` (`userBlocking`, `userNonBlocking` or `background`), `allowedFetchWebContentUrlPatterns` and a JSON schema for structured output.

**Token counting.** OpenAI BPE vocabularies (`r50k`, `p50k`, `cl100k`, `o200k`) are downloaded from `openaipublic.blob.core.windows.net` for local token counts. Embedding model names (`text-embedding-3-small`/`-large`, `ada-002`) are referenced.

**On-device ML.** `AIInfraProtocols` loads a separate inference dylib (`AIServiceParameters.dylibURL`). It supports `LocalCompactBertClassifier`, `LocalDistilBertClassifier` (with LoRA config), an MLX actor, and local LLM IDs `phi3_5`, `llama_3_2`, `gemma2b`, `qwen205b` and `openelm270m`. These appear to be Dia infrastructure.

---

## 17. Media controls and Picture-in-Picture

**What it does.** When audio or video plays in a tab you are not looking at, a mini player appears at the bottom of the sidebar. Leaving a video tab pops the video into a floating PiP window. Google Meet gets PiP with meeting controls.

**How it is implemented.**

- **Data store:** `MediaControlsDataStore.MediaControlsData` holds `maxActiveMediaControls`, `activeMediaControls`, a map from `MediaContentID` (window content plus window) to its control, and `pipSessions` (a history of `PIPSessionState` values: `pendingActive`, `active`, `hidden`, `removed`, `userRequestedClose`, `userRequestedMinimize`, `closeFailed`, and so on).
- **Mini player:** `MediaControlsFeature.MiniPlayerFeature`, with media type `audioVideo` or `recording`. A recording means the tab is using the camera or microphone, shown in a media tray (flag `media-tray-for-recording-tabs-enabled`). The flag `mini-player-marquee-title-enabled` scrolls long titles.
- **PiP:** `PictureInPicture.PictureInPictureState { contentState, isHidden, presentationSourceRect }`. `contentState` is `.video(sourceContentID, customPIPConfig)` or `.document(...)`, which uses Chromium Document PiP for whole-page PiP. Controls include play, scrub, skip-ad and back-to-tab, plus `MeetingControls` (mute, camera, hang up).
- **Per-site PiP behavior** comes from `web_content_behavior.json`: `pipDisallowList`, and `pipSiteConfigs` with `customAttributes` that map the site's own buttons, such as Meet's chat and hang-up buttons, to PiP controls.
- **Auto PiP** can be disabled per host (`autoPipDisabledForHosts`), globally (`autoPipGloballyDisabled`), or on app switch. Related flags are `google-meet-auto-picture-in-picture-enabled`, `ignore-disable-pi-p-attribute` and `autoPictureInPictureOnWindowOccluded`.
- **Background tabs:** the same config file has `keepaliveAllowList` (tabs never suspended) and `tabSuspensionBlocklist`.

---

## 18. Home button, App Tray, Arc menu, sidebar banners

- **Home** (`HomeButton`, `BaseHomeComponents`, `HomeBadging`): the button at the bottom left opens a library with pages (`HomePageID`): `downloads`, `archive`, `easelsAndNotes`, `screenshotsAndCaptures`, `boosts` and `spaces`. Each page has Lottie icons bundled as `archive.json`, `boosts.json`, and so on.
  - The button badges new items from watched sources (`HomeBadgingSourcePreference`: `documents`, `desktop`, `screenshot`, `capture`, `download`) and needs folder access permissions (`HomeDirectoryPermissions`).
  - Badged items can be AirDropped or previewed (`ItemPreviewPresenter`).
  - State is saved in `StorableHome.json`: preferences, last selected page, permissions and `isOnboardedToMediaPage`.
- **App Tray** (`AppTray`): the Favorites grid. It handles item selection, drag and reorder, pinned extensions, keyboard-shortcut hints when you hold Cmd (flag `show-top-app-shortcuts-when-holding-cmd`), live-item subtitles and calendar events (`AppTray.LiveItemAction.LiveCalendarEventAction`).
- **Arc menu** (`ArcMenu`): Arc's custom popover menu system (`ArcMenuItem`, with accessories such as a toggle, icon button or hoverable button). It is used for the extensions menu, the sidebar "+" menu and the overflow menu (`WindowContents.WindowArcMenuType`: `browserExtensions`, `sidebarPlusButton`, `navigationButtonsMore`).
- **Sidebar plus button and dock:** the `SidebarPlusButton` and `SidebarDock` modules draw the space switcher and dock at the bottom of the sidebar. The dock is a collection view with drag and drop and paging.
- **Sidebar banners** (`SidebarBanner`): one slot for transient banners. Kinds include update available, update summary (with a video link), manage ad blockers, new Arc icon unlocked, download renamed, auto-archive education, "Windows buddy day", and the farewell banner (§33).
- **Toasts** (`Toasts`): window toasts, for example "Tab moved! Click to go there."

---

## 19. Site Control Center

**What it does.** Clicking the site icon in the URL area opens a panel with site permissions, content blocking, boosts and extensions for the current site.

**How it is implemented.** `SiteControlCenter.SiteControlCenterFeature.State { browserContextID, webContentFrameIdentifier, url, isConnectionSecure, settings: [ADK.SiteSetting] }`. `ADK.SiteSetting` is one of:

- `contentSettings(type, value)`: Chromium content settings such as camera, microphone, location and notifications
- `popupBlocking(type, value)`
- `contentBlocking(enabled | disabled | unavailable)`
- `sidebarPreview(isEnabled)`
- `developerMode(isEnabled)`: per-host developer mode, stored in `developerModeEnabledForHosts`

The panel also lists the site's boosts (`SiteControlCenterBoostsView`, `BoostIndicatorButtonState`) and extensions (`SiteControlCenterExtensionsView`, with pin buttons and an extension picker).

---

## 20. Ad blocking

**What it does.** A native ad, tracker and cookie-banner blocker. It replaces extension ad blockers when you agree.

**How it is implemented.**

- **Lists:** `BlockListClient` downloads filter lists listed in a manifest. The bundled `manifest.json` points at `dia-blocklists-release.diabrowser.engineering`, and EasyList and EasyPrivacy ship as fallbacks. List categories (`BlockListCategory`) are `generic` (EasyList, AdGuard Ads, uBlock), `privacy` (EasyPrivacy, AdGuard Spyware and Social, Fanboy third-party), `cookies` (CookieMonster, AdGuard Cookies), `regional` (about 35 language lists) and `bcny` (the company's own lists).
- **Per-profile state** (`BlockListClient.BlockListsData`): `blockListsPerProfile`, `excludedDomains` per profile, `enabledBlockLists` and `excludedHosts`. Enforcement happens in Chromium (`ADK.ContentBlockerStatus`, and `ADK_ADK/raw/adblock_list.json` with `selectors.css` for cosmetic filtering).
- **Coexistence with extensions:** `ADK.AdBlockerExtensionID` recognizes about 20 extension blockers (uBlock, uBlock Lite, AdGuard, Ghostery, AdBlock Plus, and others). `AdBlocking.ManageAdBlockersDialogContext` offers to switch to the native blocker. The flags are `native-ad-blocker`, `multiple-ad-blockers-sidebar-banner-enabled` and `auto-disable-u-block-on-allow-listed-domains-enabled`.
- **Turning it on:** onboarding has an "Ad blockers" step (`AuthFeature.Setup.State.Step.adBlockers`). Settings has an advanced dialog (`AdBlockAdvancedSettingsDialog`).

---

## 21. Translation

**What it does.** Translates pages using Chromium's built-in translate engine.

**How it is implemented.** `Translation.TranslateFeature` and `TranslateBubble` (a popover anchored to the toolbar). The state holds `sourceLanguage`, `knownTargetLanguages`, `displayState` and `isTranslateDisabledForHost`. ADK reports `TranslateAvailability.available(targetLanguage, isPending)` or `.unavailable`. "Always" and "never" choices are stored in user defaults (`translateSourceLanguagesAlwaysOrNever`, `translateNeverHosts`, `UserDefaultsClient.setTranslateDisabledForHost`). The flag is `translate-enabled`.

---

## 22. Sharing spaces, folders and splits

**What it does.** You can share a space, a folder or a split as an arc.net link. The recipient sees a read-only preview and can add it to their sidebar.

**How it is implemented.**

- **Publishing:** `SharableArcObjectsClient.sharableArcObjectURL(data, type)` uploads a `SharableArcObjectsData { id, author, creatorID, data: String }` to Firebase. Here `data` is a serialized `SidebarSharedObjectData`:
  - `.space(SharableSpaceObject { space, items })`
  - `.tab(SharableTabObject { rootID, items })`
  - `.tabs(SharableNewFolderObject { rootItems, items })`
- **Link types:** `SharableArcObjectType` is `folder`, `space` or `split`. Links parse as `ArcNetURL.folder`, `.space` or `.split`.
- **Receiving:** a `sharedObject` sidebar item (`SidebarSharedObject { id, sidebarData, slug, author, timeLastActiveAt }`) is displayed by `SharableObjectsFeature.SharedObjectFeature` as a card stack of the shared tabs (`CardStack`, `TabRow`).
- **Copying links:** "Copy Link" on a split can produce an arc.net share link (flag `override-super-copy-on-split-views-for-sharable-links`). "Copy Quote as URL" appears to use an arc.net link shortener (`Arc.ArcURLShortener` with `Body { url, title, description, quote }`) and `arc.net/api/redirect-links/image` for preview images.
- **Easels and Notes** have their own share status. They do not use this mechanism.

---

## 23. Membership card and referrals

- **Membership card** (`MembershipCard`): a generated card (palette number, background blob layout, shape name, title, plus anniversary accessories by year) that can be shared as an image (`MembershipCardSharingPicker`). Your chosen look is saved in `StorableMembershipCard.json`: `{ version, backgroundBlobInfo: [Int], paletteNumber, shapeName, title }`.
- **Referrals and invites** (`ReferralCodeFeature`, `ReferralCodeClient`): `getOrCreateReferralCode` returns `ReferralCodeGenerationState { generatedOrExistingCode, isNewCode, timesUsed, maxTimesUsable, hasReachedMaxUsage, daysLeftTillNextCode }`. Arc started as invite-only, and `FirebaseClient` still has `getRedeemedInviteCount`. Invite links parse as `ArcNetURL.inviteLink(inviteCode)`. Gift links use `arc.net/gift/`.

---

## 24. Account, onboarding and Welcome to Arc

- **Account:** Firebase Authentication with email and password (`FirebaseClient.signIn`, `sendPasswordReset`, `sendVerifyAccountEmail`, `sendVerifyAndChangeEmail`, `deleteUser`). The local session is in `StorableAuthState.json` (`AuthSession { user: User { id, name, email, avatarUrl, createdAt }, finishedOnboarding, wasExistingUser, emailChangePendingVerification }`). Account deletion is `DeleteAccountFeature`. Arc requires sign-in: window restoration logs "No valid auth session found. Not restoring window."
- **Onboarding ("unboxing")** (`AuthFeature`):
  - It runs in an `UnboxingWindow` with an intro animation, music and a video (bundled `intro-music.mp3`, `demo.mov`).
  - The sign-in and sign-up flow can show a closed-signups screen (`ClosedSignupsScreen`).
  - `Setup.State.Step` then walks through `importSource`, `importFromSafari`, `importBookmarks`, `safariPasswordImportOptions`, `importSafariKeychain`, `spaceStyleEditor`, `topApps` (pick favorites), `adBlockers`, `arcMax`, `defaultBrowser` and `finished`.
  - Sync can be enabled during onboarding (`EnableSync.State.EntryPoint.unboxing`).
- **Default browser prompts** (`DefaultBrowserPrompts`): `afterOnboarding`, `day2` and `afterTrial` prompts with "try for a week" logic. The history is kept in `StorableDefaultBrowserPrompts.json`.
- **Welcome to Arc** (`WelcomeToArcFeature`): a special `welcomeToArc` sidebar tab (`SidebarWelcomeToArc.tabType`: `legacy` or `modernGetStarted`) that hosts the "Arc 101" lessons (`Arc101Step`: `pinTabs`, `spaces`, `splitView`, `newTab`), each with a bundled video (`pinning.mp4`, `space_swiping.mp4`, `split_view.mp4`, `new_tab.mp4`). It also opens through `ArcNetURL.welcomeToArc`.
- **Keyboard shortcut education:** `KeyboardShortcutsEducationFeature` and `Arc.PinnedTabSectionEduBanner`.

---

## 25. Import from other browsers

**What it does.** Imports bookmarks, history, passwords, cookies and extensions from another browser into a new or existing Arc profile.

**How it is implemented.**

- **Sources** (`ADK.ImportSource.Browser`): `brave`, `chrome`, `edge`, `firefox`, `opera`, `operaGX`, `safari`, `safariExportedData`, `vivaldi`, `arc` and `dia`. Each source lists its importable profiles (`ImporterProfile`). Chromium's importer does the work (`ADK.ImportingController`, `ImportEvent.ImportCategoriesStatus`: `noneFinished`, `allSucceeded`, `someSucceeded`, `allFailed`).
- **Options** (`ImportFeature.ImportProfile.Options { sourceProfile, destination, importCookies }`): the destination is an existing profile (optionally renamed) or a new profile. Safari needs Full Disk Access (`FullDiskAccessAuthorizer`). The Safari keychain import has its own step.
- **Smart setup:** Arc also reads `recentHistory` and `siteEngagement` from the source (`FetchCategory`) to suggest favorites (`ImportedTopApp`, `TopAppAndScore`) and pinned tabs.
- **UI:** `ImportMenuFeature` (File → Import, `ImportDialog`, `ProfilesDialog`) and a password-import prompt (`PasswordImportPrompt`).

---

## 26. Settings

**Panes** (`PreferencesFeature.ArcPreferencePane`). The contents column is inferred from each pane's view-state types and UI strings.

| Pane | What it covers |
|---|---|
| `account` | Name, email, password, Arc Sync setup (Firebase sync dialog, recovery phrase), iCloud sync state |
| `general` | Default browser, quit behavior (`QuittingPreference`), window restoration (`WindowRestorationSetting`: preserve, close or follow system), auto-update and beta channel, ad blocking, archive thresholds, search engine, previews |
| `max` | Arc Max toggles (§16) |
| `profiles` | Per-profile settings: name, archive threshold, ad blocking, search, Little Arc defaults |
| `keyBindings` | Shortcut editor (§27) |
| `links` | Air Traffic Control (§10) and Little Arc link behavior |
| `advanced` | Chromium feature switches, Metal and Skia toggles, developer options, data export |
| `appIcon` | Alternate icons (`BaseModels.ArcAppIcon`: `original`, `candy`, `hologram`, `neon`, `flutedGlass`, `schoolbook`, `colorful`), some unlocked by usage. The dock tile is updated through a DockTile plug-in. |
| `staff` | Internal only |

Most simple preferences are `NSUserDefaults` keys in `~/Library/Preferences/company.thebrowser.Browser.plist`. `ARCFoundationModels.ArcUserDefaultSettings` lists about 300 keys, many of them Dia-only. Some preferences sync through Firestore (`SyncedPreferencesClient`, one `value` field per setting). Chromium settings (passwords, site permissions, search engines) live in the Chromium profile and open as `arc://settings/...`.

---

## 27. Key bindings

**What it does.** Every menu command can be rebound. A conflict is detected and shown in the editor.

**How it is implemented.**

- **Registration:** actions are registered from the main menu. Each `NSMenuItem` carries an `arcKeyBindingID` runtime attribute (`KeyBindingMenuManager.initialRegistration`), and a duplicate ID triggers an assertion.
- **Model:**

  ```swift
  struct KeyBindings.KeyBinding {
      var action: KeyBindableAction           // { identifier, name }
      var default: DefaultAttributes?         // { shortcut, priority, typeTravelTriggers[] }
      var state: State                        // .valid(shortcut) | .conflict(shortcut, conflictingActions) | .unset
      var source: Source                      // .userDefined | .default
      var priority: Priority                  // .low | .promptAfterConsumedByWebView | .overrideWebView
  }
  ```

- **Priority** decides who wins when a web page also handles the key: Arc, the page, or "the page first, then Arc after a prompt".
- **Type Travel triggers** (`typeTravelTriggers`) are the words that surface the action in the Command Bar.
- **Persistence:** only your overrides are saved, in `StorableKeyBindings.json` (`{ version, userOverrides: [KeyBinding] }`). Related user defaults are `commandKeyShowsCommandBar`, `controlKeyShowsTypeTravel` and `switchToNinthSidebarItemEnabled`.

---

## 28. Sound effects

`SoundEffects.SoundEffectClient` with `SoundEffect.capture`. The bundle `ARC_SoundEffects` has `capture.wav` (the screenshot shutter) and `event.m4a` (likely the calendar event chime). UI sounds can be turned off with `playUserInterfaceSoundsDisabled`. Separate chat and report notification sounds belong to Dia (`chatNotificationSoundEnabled`).

---

## 29. Software updates (Sparkle)

- **Feed:** from `Info.plist`, `SUFeedURL = https://releases.arc.net/updates.xml`, `SUScheduledCheckInterval = 28800` (8 hours), `SUAutomaticallyUpdate` and `SUEnableAutomaticChecks` are true, and updates are EdDSA-signed (`SUPublicEDKey = <redacted>`).
- **Channels** (`SoftwareUpdaterClient.SoftwareUpdaterFeed`): `release`, `releaseCandidate`, `canary`, `prototype`, `pullRequest(Int)` and `test`. Settings can switch to beta (`ConfirmSwitchToBetaDialog`, flag `switch-to-beta-enabled`). Other hosts in the binary are `releases.browserinternal.com` and an S3 bucket for the same feed.
- **Update records:** `AppUpdate { title, bundleVersion, displayVersionString, description, majorUpgrade, criticalUpdate, channel }`. Version comparison allows canary downgrades (`DowngradableVersionComparison`).
- **Installing:** Arc uses a custom Sparkle user driver (`CustomUserDriver`) and its own UI (sidebar banners, a release-notes view, a relaunch animation). Auto-install waits for inactivity (flags `auto-update-inactivity-delay-in-seconds` and `auto-update-required-idle-duration-in-seconds`). A restart helper script (`arc_restart_helper.sh`) and an update-restart journal survive the relaunch.
- **Disable switch:** the command-line flag `--disable-software-updater`.

---

## 30. AppleScript API

Arc ships a scripting dictionary (`Arc.sdef`, implemented in `AppDelegate+Applescript.swift`, with wrappers `Arc.AppleScriptWindowWrapper`, `AppleScriptTabWrapper` and `AppleScriptSpaceWrapper`). It has one suite.

| Class | Properties | Elements | Commands it responds to |
|---|---|---|---|
| `application` | `name`, `frontmost`, `version` (all read-only) | `windows` | `quit`, `make`, `count` |
| `window` | `closeable`, `minimizable`, `minimized`, `resizable`, `visible`, `zoomable`, `zoomed`, `active tab` (ro), `active space` (ro), `incognito`, `mode` (`"normal"` or `"incognito"`, settable only at creation) | `tabs`, `spaces` | `close` |
| `tab` | `id` (ro), `title` (ro), `URL` (rw), `loading` (ro), `location` (`"topApp"`, `"pinned"` or `"unpinned"`) | none | `select`, `go back`, `go forward`, `reload`, `stop`, `execute javascript "…"` (returns text), `close` |
| `space` | `id` (ro), `title` (ro) | `tabs` | `focus` |

Commands: `make new <class> with properties {…}`, `count`, `close`, `select`, `go back`, `go forward`, `reload`, `stop`, `execute … javascript "…"` and `focus`.

```applescript
tell application "Arc"
  tell front window
    make new tab with properties {URL:"https://example.com"}
    get {title, URL, location} of every tab of active space
  end tell
end tell
```

There is no AppleScript access to folders, Easels, Notes or archive data. To work with those, read the JSON files described in [data-model.md](data-model.md).

---

## 31. URL schemes and arc.net links

- **Registered schemes** (`Info.plist → CFBundleURLTypes`): `http`, `https`, `mailto` and `arcBrowser`. Arc also opens PDF, HTML, XHTML and similar documents as a viewer.
- **Internal links** are parsed into `BaseModels.ArcNetURL`:

  ```swift
  enum BaseModels.ArcNetURL {
      case boostInstallRequest(boostSnapshotIDRawValue: String)
      case document(id: ArcDocumentID), easel(id: EaselID)
      case folder(id: SharedArcObjectID), split(id: SharedArcObjectID), space(id: SharedArcObjectID)
      case inviteLink(inviteCode: String)
      case browseForMe(query: String)
      case quit(Scheme), restart(Scheme)       // Scheme: .chrome | .arc | .arcbrowser
      case welcomeToArc
  }
  ```

- **Scheme handling:** `quit` and `restart` are recognized under three schemes (`ArcNetURL.Scheme`: `chrome`, `arc`, `arcbrowser`), so `arc://quit` and `arcbrowser://restart` appear to be valid. Web navigation to `arcbrowser` URLs is intercepted in `decidePolicyForWebContentFrameNavigation`. Other Arc objects are identified by `https://arc.net/...` links, such as `/easel`, `/note`, `/object`, `/boosts` and `/gift/`. Those links open in the matching native view.
- **Internal pages** include `arc://settings`, `arc://settings/searchEngines`, `arc://password-manager/passwords`, `arc://extensions`, `arc://history/?q=%s` and the Boost IDE (`arc://boost/v2/...`).
- **Apple universal links:** Arc fetches `apple-app-site-association` files (`UniversalLinks.AppleSiteAppLinks`) so links can open in native apps.

---

## 32. Remote configuration, feature flags and telemetry

- **Feature flags:** LaunchDarkly (`clientstream.launchdarkly.com`; the mobile key is `<redacted>`). Generated flag tables include `AppFeatureFlags`, `CommandBarFeatureFlags`, `InstrumentationFeatureFlags`, `MobileFeatureFlags`, `SoftwareUpdateFeatureFlags`, `UnboxingFeatureFlags` and `WebContentFeatureFlags`, with about 190 non-Windows keys in this build. Flag values are cached in `StorableFeatureFlags.json` (`{ version, flags: [{ id, value }] }`). Developers can override them locally (`transientFeatureFlagOverrides`, `FeatureFlagsUI`).
- **Content configuration files**, fetched from `content.arc.net` with bundled fallbacks:
  - `web_content_behavior.json`: tidy titles, PiP lists, keepalive and suspension lists
  - `command_bar_behavior.json`
  - `memory_behavior.json`
  - `sso_embed_behavior.json`
- **Telemetry:**
  - Segment analytics (`AnalyticsClient`; its enormous event-property enums are a useful map of every UI surface)
  - Datadog (logs, traces and RUM intake hosts)
  - Sentry crash reporting (DSN `<redacted>`)
  - OpenTelemetry API types
  - An internal bug reporter (`incoming.browserinternal.com/bug-report`)

  Usage-data sharing is a user default (`shouldShareUsageData`). Log verbosity can be adjusted remotely per subsystem (`StorableDynamicLogLevels.json`).

---

## 33. The sunset: farewell banner and export paths

Build 1.174.0 carries the sunset UI:

- **Farewell banner:** `FeatureFlags.ArcFarewellBannerState { stage, daysRemaining }` with stages `thirtyDays`, `fourteenDays`, `sevenDays`, `oneDay` and `lastDay`. Each stage has remotely configurable copy (`ArcFarewellBannerCopy`, flag `arc-farewell-banner-copy`). The default copy says "Arc is sunsetting on December 22, 2026" and that spaces come over to Dia as profiles with tabs, passwords and extensions. Links go to `arc.net/farewell` and `arc.net/wemightnotmakeit`. The dismissed stage is stored in `arcFarewellBannerDismissedStage`.
- **Forced sign-out:** the flag `arc-force-sign-out-enabled`.
- **Export paths inside Arc:**
  - Notes export to a zip (§13).
  - Easels export as web pages (§12).
  - "Export All Passwords" uses the Chromium password manager.
  - Dia's importer accepts `ImportSource.Browser.arc`.
- **Backups:** the internal `Arc.RestoreSidebarDataFlow` and `RestoreDataViewController` can restore the sidebar and windows from the dated JSON backups. See [data-model.md §10](data-model.md#10-migrating-off-arc) for doing the same yourself.

---

## 34. Module index

These are the Swift modules found in the binary, grouped by role. Counts of declared types are approximate.

| Area | Modules |
|---|---|
| App shell | `Arc` (≈660 types), `SharedAppFeature`, `SharedWindowFeature`, `SharedWindowsFeature`, `WindowContents`, `WindowBackground`, `WindowProvider`, `ContentPanel`, `Dialogs`, `ModalContent`, `Toasts`, `ContextMenus`, `ArcTooltip`, `DragAndDrop` |
| Sidebar | `BaseModels`, `SidebarDataStore`, `StorableSidebar`, `SidebarUI`, `SidebarFeature`, `SidebarItemUI`, `SidebarDock`, `SidebarPlusButton`, `SidebarBanner`, `FolderIcon`, `AppTray`, `Archive`, `ArchiveDataStoreClient`, `StorableArchive`, `SharedArchiveFeature` |
| Sync and account | `SidebarSyncCloudKit`, `CloudKitContainerClient`, `FirebaseSidebarSyncClient`, `FirebaseSidebarSyncCommon`, `FirebaseSidebarSyncModel`, `FirebaseSidebarSyncSchemaClient`, `FirebaseSyncRemoteEncryptionClient`, `FirebaseSyncDebugClient`, `EncryptionClient`, `EncryptionRecoveryClient`, `Sodium`, `FirebaseClient`, `AuthFeature`, `DeleteAccountFeature`, `SyncedPreferencesClient`, `KeychainClient` |
| Browsing | `ADK`, `ADKClient`, `ADKModels`, `ADKClientLive`, `ADKApplicationFeature`, `WebContent`, `WebContentPageType`, `WebContentLifecycleOptimization`, `BackForwardList`, `PermissionRequests`, `SessionRestorationClient`, `DownloadsUI`, `SharedDownloadsFeature`, `UniversalLinks`, `TopDomains`, `DomainParser` |
| Navigation and search | `CommandBar`, `CommandBarAdditionalRankingDataStoreClient`, `URLInputter`, `SearchClientManager`, `ASE2`, `TypeTravel`, `WebSearch`, `InstantLinks`, `LinkRouting`, `LittleBrowser`, `GlobalHotkeyListenerClient`, `ModalItemSwitcher` |
| Creation | `EaselUI`, `EaselClient`, `Easel`, `EaselLibraryClient`, `Capture`, `CaptureClient`, `DocumentsClient`, `DocumentsFeature`, `DocumentsLibraryClient`, `ArcRichTextEditor`, `TextEditor`, `LibraryData` |
| Customization | `BoostsClient`, `BoostsEditor`, `BoostsDialog`, `SpaceCreation`, `SpaceStyleEditor`, `WindowThemeUI`, `ProfilesUI`, `AppIconClient`, `KeyBindings`, `PreferencesFeature`, `Settings`, `ShareSettings` |
| Live data | `LiveFoldersFeature`, `GitHubClient`, `LiveSlackClient`, `LiveNotionClient`, `LiveCalendarClient`, `LiveCalendars`, `Previews`, `HoverCards`, `HomeBadging`, `HomeButton`, `BaseHomeComponents` |
| AI | `LLM`, `AIInfraProtocols`, `AskArc`, `AskArcComparisonTool`, `AskInPage`, `PromptGeneration`, `Scraping`, `HTML2Markdown`, `TidyTabTitles` |
| Media | `MediaControlsFeature`, `MediaControlsDataStore`, `PictureInPicture`, `AudioProcessing`, `YouTubePlayerKit`, `SoundEffects` |
| Safety and privacy | `AdBlocking`, `BlockListClient`, `SiteControlCenter`, `Translation` |
| Growth | `WelcomeToArcFeature`, `KeyboardShortcutsEducationFeature`, `ImportFeature`, `ImportMenuFeature`, `DefaultBrowserPrompts`, `MembershipCard`, `ReferralCodeFeature`, `ReferralCodeClient`, `SharableObjectsFeature`, `SharableArcObjectsClient` |
| Infrastructure | `Storable`, `ApplicationPaths`, `UserDefaultsClient`, `FeatureFlags`, `FeatureFlagsClient`, `FeatureFlagsUI`, `DynamicLogLevels`, `DeveloperModeClient`, `SoftwareUpdaterClient`, `AnalyticsClient`, `TelemetryClient`, `Meter`, `TracingFeature`, `Logging`, `LifetimeTracker`, `RateLimiting`, `WebContentBehaviorConfigurationClient` |
| Third-party | ComposableArchitecture, Dependencies, CasePaths, IdentifiedCollections, OrderedCollections, AsyncAlgorithms, CombineExt, SwiftSoup, Fuzi, Mustache, Parsing, Sodium, Firebase (Auth, Firestore, Functions, Storage), LaunchDarkly, Segment, Datadog, Sentry, OpenTelemetry, SDWebImage, Lottie, Sparkle, ZIPFoundation, YouTubePlayerKit, SwiftUIIntrospect |

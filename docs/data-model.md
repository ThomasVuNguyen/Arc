# Arc's data model, on-disk files and sync (macOS, v1.174.0)

This document describes what Arc writes to disk, how those files are encoded, how the sidebar is modeled, and how it syncs.

- **How the schemas were derived:** from the reconstructed Swift `Codable` types in the shipped binary (`vault/extracted/swift/Arc.swift`) and strings (`vault/extracted/strings/Arc.txt`). No user data was opened to write this.
- **Example JSON is synthetic:** fake IDs, `example.com` URLs, "My Space". It shows the shape the types produce, not a copy of a real file.
- **Exactness:** field names come straight from `CodingKeys`. Shapes that depend on hand-written `Codable` code (noted as *custom-coded*) are inferred.

See [features.md](features.md) for what each feature does.

---

## Contents

1. [Where Arc keeps its data](#1-where-arc-keeps-its-data)
2. [The Storable layer: versioning, backups, recovery](#2-the-storable-layer-versioning-backups-recovery)
3. [JSON encoding conventions](#3-json-encoding-conventions)
4. [File catalog](#4-file-catalog)
5. [The sidebar model](#5-the-sidebar-model)
6. [Window themes and color palettes](#6-window-themes-and-color-palettes)
7. [Profiles and the Chromium User Data directory](#7-profiles-and-the-chromium-user-data-directory)
8. [Sync](#8-sync)
9. [Other files in detail](#9-other-files-in-detail)
10. [Migrating off Arc](#10-migrating-off-arc)

---

## 1. Where Arc keeps its data

| Location | Contents |
|---|---|
| `~/Library/Application Support/Arc/` | Arc's own state: `Storable*.json` files, their dated backups, caches, sentinels |
| `~/Library/Application Support/Arc/User Data/` | The Chromium profile tree (`Default/`, `Profile 1/`, …, `Local State`), owned by `ArcCore.framework` |
| `~/Library/Preferences/company.thebrowser.Browser.plist` | `NSUserDefaults`: about 300 simple settings (`ARCFoundationModels.ArcUserDefaultSettings`) |
| Login Keychain | "Arc Safe Storage" (Chromium's cookie and password encryption key), Firebase Auth tokens |
| Cloud | Firebase (account, Notes, Easels, Boosts, shared objects, encrypted sidebar sync) and CloudKit container `iCloud.net.arc.sidebar` (legacy iCloud sync) |

`ApplicationPaths.ApplicationPaths.Location` lists every path Arc resolves under its base directory. A user default (`customApplicationDataBaseURLPath`) can override the base, which is used by tests. The cases are: `arcCore`, `boosts`, `boostsImageCache`, `database`, `sidebarFaviconCache`, `featureFlags`, `sidebar`, `windows`, `authState`, `aseConfiguration`, `arcDocuments`, `archivedItems`, `archiveFaviconCache`, `archiveSnapshotCache`, `archive`, `commandBarAdditionalRanking`, `remoteAssetDirectory`, `traces`, `capture`, `captureImageCache`, `pasteboard`, `profiles`, `previewsDataClient`, `ignoredPaths`, `library`, `easelImagesCache`, `keyBindings`, `defaultBrowserPrompts`, `membershipCards`, `linkRouting`, `home`, `developerMode`, `encryptionKey`, `firebaseSyncDebugKey`, `firebaseLastSeenSchemaVersion`, `dynamicLogLevels`, `liveData`, the sentinel and journal files (`uncleanShutdownSentinel`, `launchInProgressSentinel`, `updateRestartJournal`, …), `sessionRestorationData`, `blockList`, `downloadMetadata`, `localBoostsData`, `storableProfileContainers`, `memoryWebContentSnapshots`, `logFiles`, `todosData` and `tempDiaTabStorage`.

---

## 2. The Storable layer: versioning, backups, recovery

Almost every JSON file goes through one generic store:

```swift
struct Storable.StorableDataStore<A: Storable> {
    var readSyncThrowing:  (URL?, Bool, StorableDataDecoderInfo?) throws -> A?
    var saveSyncThrowing:  (A, Bool /*createBackup*/) throws -> Void
    var deleteSync, deleteAllSync: () -> Void
    var restoreFromBackup: (StorableDataDecoderInfo?) -> A?
    var allStoredFiles:    () -> [StorableFile]      // StorableFile { url, isBackup, date? }
}
class Storable.StorableDataStoreImpl<A> {
    let fileURL: URL; let fileName: String; let queue: DispatchQueue
    let jsonEncoder: JSONEncoder; let jsonDecoder: JSONDecoder
    let dateFormatter: DateFormatter          // "yyyy-MM-dd-HH-mm-ss-SSS" for backup names
}
struct Storable.BackupPolicy { var interval: Calendar.Component; var duration: Int; var maxAllowableBackups: Int }
```

- **Versioning.** The `Storable` protocol requires `Codable & Equatable` plus static metadata (stripped from the binary; likely the file name and the current version). Every top-level storable has `"version": Int`. Before the full decode, the store reads only `{ "version" }` (`StorableDataStoreImpl.StorableVersion`). If the file's version is outside what the build supports, decoding fails with `StorableError.versionOutdated(oldVersionNumber:currentVersionNumber:)`.
- **Deprecation.** Types can throw a `StorableDataDeprecationError` when they meet a key that is no longer supported, such as `BaseModels.SidebarDataDecodingError.deprecatedKeyDecoded` for the removed sidebar item kinds `archiveContent`, `download` and `arcSearch`, or `ASE2.DeprecatedArchetypeError`.
- **Rolling dated backups.** On save with `createBackup`, the previous file is kept as `<Name>.<yyyy-MM-dd-HH-mm-ss-SSS>.json` next to the live file, for example `StorableSidebar.2026-01-31-09-15-02-123.json`. The `BackupPolicy` (one per interval unit, for a duration, capped at `maxAllowableBackups`) decides which to keep. Old ones are deleted with the log line "Removing old backup file for storable…". The `allStoredFiles()` API returns live and backup files with their parsed dates.
- **Failure handling.** If decoding fails, the store copies the bad file aside for inspection ("After failing to read, copied a backup of the current file for inspection to…") and can fall back to `restoreFromBackup`, which tries the newest backups. The developer menu has a manual "Restore data" tool (`Arc.RestoreSidebarDataFlow`) that lists `StorableSidebar` and `StorableWindows` backups and restores the chosen one.
- **Folder stores.** `Storable.StorableFolderDataStore<A: IdentifiableStorable>` writes one file per object into a folder. Notes use it (`StorableARCDocuments/`).
- **Decoder options.** `StorableDataDecoderInfo` passes `CodingUserInfoKey` values to the decoder. One known key is `includeFaviconInSidebarTabEncode`, which controls whether tab favicons are embedded as PNG data.

---

## 3. JSON encoding conventions

Arc uses Foundation's `JSONEncoder` with default strategies and Swift's synthesized `Codable`. These are the rules you need to parse the files:

| Swift construct | JSON shape | Example |
|---|---|---|
| `struct` | object keyed by `CodingKeys`. `nil` optionals are omitted, not `null`. | `{"id": "…", "createdAt": 750000000.0}` |
| `Date` | number of **seconds since 2001-01-01 00:00:00 UTC** (Apple reference date). Add `978307200` to get Unix time. | `750000000.0` → 2024-10-07 |
| `Data` | base64 string | `"savedFaviconPNGData": "iVBORw0KGgo…"` |
| `URL` | absolute string | `"https://example.com/"` |
| `Identifier<T>`, `WindowID`, `ArcDocumentID`, … | plain string (UUIDs) | `"00000000-0000-4000-8000-000000000001"` |
| `Array`, `Set`, `OrderedSet`, `IdentifiedArray` | JSON array | `"childrenIds": ["…", "…"]` |
| `Dictionary` with `String` keys | JSON object | `"overrides": {"sync": "debug"}` |
| `Dictionary` with any other key type (enum, struct, `Identifier`) | **flat array `[k1, v1, k2, v2, …]`** | `"topAppsContainerIDs": [{"default": {}}, "…id…"]` |
| `OrderedDictionary` (swift-collections) | **always** a flat array `[k1, v1, …]`, whatever the key type | `"spaces": ["space-id", {…space…}]` |
| enum with raw values (`String`) | the raw value, usually the case name | `"layoutOrientation": "horizontal"` |
| enum without raw values, no payload | `{"case": {}}` | `{"pinned": {}}` |
| enum case with one unlabeled payload | `{"case": {"_0": payload}}` | `{"spaceItems": {"_0": "space-id"}}` |
| enum case with labeled payload | `{"case": {"label": …}}` | `{"desktop": {"machineID": "…", "windowID": "…"}}` |
| *custom-coded* enums | `{"case": payload}` with **no** `_0` wrapper | `{"tab": {"savedURL": "…"}}` |

**Which enums are custom-coded.** These enums declare only a top-level `CodingKeys` and no per-case `XCodingKeys`, so they have hand-written `Codable`:

- `BaseModels.SidebarItemData` (`{"tab": {...}}`, `{"list": {...}}`, …)
- `ADKModels.Profile` (keys `default` and `custom`)
- `BaseModels.SidebarCustomIcon` (keys `emoji`, the legacy `emojiInt`, `icon` and `symbol`)
- `BaseModels.LiveItem.Data`
- `BaseModels.PreviewType`

**Which enums encode as plain strings.** These conform to `RawRepresentable`: `SidebarTab.MuteStatus`, `SidebarEasel.ShareStatus`, `SidebarSplitViewData.LayoutOrientation`, `SidebarIconType`, `SidebarMode`, `ArchiveReason`, `WindowTheme.Overlay`, `WindowTheme.Appearance` and `TranslucencyStyle`, `ARCDocument.ShareStatus`, `KeyBinding.Priority`, `AutoArchiveInactiveThreshold` and `Logger.Level`.

`scripts/tools/export_sidebar.py` in this repo implements these rules (`pairs()` for flat arrays, `case()` for single-key enum objects, `APPLE_EPOCH` for dates).

---

## 4. File catalog

All of these files are in `~/Library/Application Support/Arc/` and all have a top-level `"version"` unless noted. "Rolling backups" means dated copies exist (the sidebar and windows files are the ones restored by the built-in restore tool).

| File | Swift type | Purpose | Top-level keys |
|---|---|---|---|
| `StorableSidebar.json` | `StorableSidebar.StorableSidebar` | **The sidebar:** all spaces, favorites, pinned and Today items, folders, splits, plus per-item sync bookkeeping | `version`, `sidebar`, `sidebarSyncState?`, `firebaseSyncState?` |
| `StorableSidebar.<date>.json` | same | Rolling backups of the above | same |
| `StorableWindows.json` | `StorableWindows.StorableWindows` | Open windows, focused space, per-window expansion state, last-active dates, sidebar width and mode, split layout, Little Arc windows | `version`, `sidebarViewPreferences?`, `windows?`, `lastFocusedSpaceID?`, `platformData?` |
| `StorableArchiveItems.json` | `ArchiveDataStoreClient.StorableArchivedItems` | Archived tabs and folders (full `SidebarItem` copies) | `version`, `items` (flat `[id, ArchivedItem, …]`) |
| `StorableArchive.json` | `StorableArchive.StorableArchive` | Auto-archive watermark | `version`, `autoArchiveStartTime?` |
| `StorableLinkRouting.json` | `LinkRouting.StorableLinkRoutingState` | Air Traffic Control rules | `version`, `rules`, `defaultDestination` |
| `StorableHome.json` | `BaseHomeComponents.StorableHome` | Home button badging prefs, last page, folder permissions | `version`, `preferences?`, `lastSelectedHomePage?`, `permissions?`, `isOnboardedToMediaPage?` |
| `StorableKeyBindings.json` | `KeyBindings.StorableKeyBindings` | Your shortcut overrides only | `version`, `userOverrides` |
| `StorableLiveData.json` | `LiveFoldersFeature.StorableLiveData` | Live Folder items (GitHub PRs and others) per profile | `version`, `liveDataPerProfile` |
| `StorableMembershipCard.json` | `MembershipCard.StorableMembershipCardState` | Membership card look | `version`, `backgroundBlobInfo`, `paletteNumber`, `shapeName`, `title` |
| `StorableAuthState.json` | `BaseModels.StorableAuthState` | Signed-in user and onboarding flags (tokens are in the Keychain) | `version`, `session?` |
| `StorableFirebaseEncryptionKey.json` | `EncryptionClient.EncryptionKeysStorable` | **Secret.** Arc Sync's local key material. | `version`, `hashedPassword`, `encryptionKeysByID` |
| `StorableFirebaseLastSeenSchemaVersion.json` | `FirebaseSidebarSyncSchemaClient.FirebaseSchemaStorable` | Highest sync schema committed | `version`, `firebaseSchemaVersion` |
| `StorableFirebaseSyncDebugState.json` | `FirebaseSyncDebugClient.StorableSidebarSyncDebugData` | Optional local sync debug log (last mutation per item and space) | `sidebarItemMutations`, `spacesMutations` (no version) |
| `StorableCommandBarAdditionalRanking.json` | `CommandBarAdditionalRankingDataStoreClient.StorableCommandBarAdditionalRankingData` | Command Bar learning signals | `version`, `dataByProfile` |
| `StorableASEConfiguration.json` | `ASE2.StorableASEConfiguration` | Cached ranking-engine weights | `version`, `configuration?` |
| `StorableSessionRestorationData.json` | `SessionRestorationClientImpl.StorableDataType` | Maps sidebar tabs to Chromium tab sessions so back/forward history survives relaunch | `version`, `mapping` |
| `StorableDefaultBrowserPrompts.json` | `DefaultBrowserPrompts.StorableDefaultBrowserPromptsState` | Default-browser nag schedule | `version`, `scheduledNext?`, `displayHistory` |
| `StorableBoostsData.json` | `BoostsClient.StorableBoostsData` | Which boosts are enabled on this Mac (boost bodies are in Firestore) | `version`, `locallyEnabledBoostIDs` |
| `StorableCaptures.json` | `CaptureClient.StorableCaptureItems` | Screenshot library index (images in `CaptureImageCache`) | `version`, `items` (flat) |
| `StorableARCDocuments/` | `DocumentsClient.StorableARCDocument` (folder store) | One file per Arc Note | each: `version`, `arcDocument` |
| `StorableFeatureFlags.json` | `FeatureFlagsClient.StorableFeatureFlags` | Cached LaunchDarkly values | `version`, `flags: [{id, value}]` |
| `StorableDynamicLogLevels.json` | `DynamicLogLevels.StorableDynamicLogLevels` | Remote log-level overrides | `version`, `overrides: {subsystem: level}` |
| `StorableDeveloperModeState.json` | `DeveloperModeClient.StorableDeveloperModeState` | Developer-mode toggles | `version`, `state` |
| `StorablePreviewsDataClient.json` | `Previews.PreviewsDataStore.StorableData` | Cached favorite previews (Gmail, Calendar, …) | `version`, `data` (flat `[{previewType, profile}, PreviewData, …]`) |
| `IgnoredPaths.json` | `FileQueryClient.StorableIgnoredPaths` | Files and folders Home badging should ignore | `version`, `ignoredFilePaths`, `ignoredDirectoryPaths` |
| `StorableDownloadMetadata.json` | (Storable `DownloadRenameMetadata`) | Download rename history (Tidy Downloads) | not recovered |
| `StorableProfiles.json`, `StorableProfileContainers.json`, `StorableLibrary.json`, `StorablePasteboardHistory.json`, `StorableTodosData.json` | (names only) | Path constants present in the binary. Their types are not recovered, and several belong to Dia or Arc for Windows. | |

Block-list state (`BlockListClient.BlockListsData { version, blockListData, excludedDomains: [Profile: [String]], blockListsPerProfile, enabledBlockLists?, excludedHosts? }`) is also a `Storable`, at the `blockList` path.

**Caches and other non-JSON items:** `BoostsImageCache`, `EaselImagesCache`, `CaptureImageCache`, sidebar and archive favicon caches, `archiveSnapshotCache`, `RemoteAssetDirectory`, `MemoryWebContentSnapshots`, the crash and launch sentinels (`UncleanShutdownSentinel`, `LaunchInProgressSentinel`, …), `UpdateRestartJournal` and `SuspiciousEventLog`.

---

## 5. The sidebar model

### 5.1 Container hierarchy

```text
StorableSidebar
├── version
├── sidebar: SidebarDataStore.AppSidebarReducerState
│   └── containers: [SidebarContainerType: SidebarContainer]        (flat array)
│       ├── {"global": {}}  →  SidebarContainer   ← the real, synced sidebar
│       ├── {"incognito": {"_0": windowID}}  →  …  (per incognito window)
│       ├── {"littleBrowser": {"_0": windowID}} →  … (per Little Arc window)
│       └── {"standalone": {"_0": windowID}} →  …
├── sidebarSyncState: SidebarSyncCloudKit.ZoneSyncData?              (iCloud sync)
└── firebaseSyncState: FirebaseSidebarSyncCommon.PersistedFirebaseSidebarSyncState?  (Arc Sync)
```

```swift
struct BaseModels.SidebarContainer {
    var items: [Identifier<SidebarItem>: SidebarItem]                       // flat array
    var spaces: OrderedDictionary<Identifier<SpaceModel>, SpaceModel>       // flat array, ordered
    var topAppsContainerIDs: [ADKModels.Profile: Identifier<SidebarItem>]   // flat array
}
// CodingKeys also include legacy: topAppsContainerID, activeSpaceIDs, pendingSpaceID
```

The order of `spaces` is the order of the space switcher. Every space and the favorites of every profile point at root **item containers** in `items`. All tabs and folders hang below those roots through `childrenIds`.

### 5.2 `SidebarItem`

```swift
struct BaseModels.SidebarItem {
    var id: Identifier<SidebarItem>
    var title: String?                         // user-set title; nil = use page title
    var childrenIds: OrderedSet<Identifier<SidebarItem>>
    var parentID: Identifier<SidebarItem>?
    var data: SidebarItemData                  // custom-coded {"kind": payload}
    var createdAt: Date
    var isUnread: Bool
    var originatingDevice: String?             // machine that created it (sync)
}
```

### 5.3 `SidebarItemData` kinds and payloads

| Kind | Payload struct | Fields |
|---|---|---|
| `tab` | `SidebarTab` | `savedURL?`, `savedTitle?`, `savedFaviconPNGData?` (base64 PNG), `savedMuteStatus?` (`allowAudio`/`mute`), `customInfo?` (`iconType`), `referrerID?`, `activeTabBeforeCreationID?`, `timeLastActiveAt?`, `liveItemID?`. Legacy keys read on decode: `tabId`, `liveItem_legacy`, `url_legacy`, `title_legacy`, `pageInfoWhenSaved_legacy` (`{url, title}`). |
| `list` (folder) | `SidebarList` | `customInfo?` (`iconType`), `automaticLiveFolderData?` (see 5.6) |
| `arcDocument` (Note) | `SidebarArcDocument` | `arcDocumentID`, `timeLastActiveAt?`, `isEditable`, `customInfo?` |
| `easel` | `SidebarEasel` | `easelID`, `shareStatus` (`readOnly`/`publicReadWrite`/`creatorOnly`), `title`, `timeLastActiveAt?`, `customInfo?`, `creatorID?` |
| `itemContainer` | `SidebarItemContainer` | `containerType`: `{"topApps": {"_0": Profile}}` or `{"spaceItems": {"_0": spaceID}}`. An older format, `PrePILOT322ContainerType`, had `topApps` without a profile. |
| `welcomeToArc` | `SidebarWelcomeToArc` | `tabType` (`legacy`/`modernGetStarted`), `timeLastActiveAt?` |
| `splitView` | `SidebarSplitViewData` | `itemWidthFactors` (flat `[childID, CGFloat, …]`), `layoutOrientation` (`horizontal`/`vertical`), `timeLastActiveAt?`, `customInfo?`, `focusItemID?`. The panes are the item's `childrenIds`. |
| `sharedObject` | `SidebarSharedObject` | `id` (`{value}`), `timeLastActiveAt?`, `sidebarData` (`space`/`tab`/`tabs`, each `{"_0": …}` containing a `SpaceModel` and/or `items: [SidebarItem]`), `slug` (`folder`/`space`/`split`), `author` |
| `instantLinks` | `SidebarInstantLinks` | `status` (`loading`/`error`). This is a transient placeholder. |
| `tabGroup` | `SidebarTabGroup` | `title`. The grouped tabs are the item's children. |

Removed kinds (`archiveContent`, `download`, `arcSearch`) raise a deprecation error and are dropped.

**Custom icons** (`SidebarCustomIcon`, custom-coded):

- `{"emoji": "🚀"}`, or the legacy integer form `emojiInt`
- `{"icon": "<SidebarIconType>"}`, one of about 60 names such as `star`, `bookmark`, `heart`, `folder`, `calendar`, `code`, `github`, `linear` and `figma`
- `{"symbol": "<SF Symbol name>"}`

### 5.4 `SpaceModel`

```swift
struct BaseModels.SpaceModel {
    var id: Identifier<SpaceModel>
    var title: String?
    var containerIDs: [ContainerType: Identifier<SidebarItem>]   // flat array
    var customInfo: CustomInfo        // { iconType?: SidebarCustomIcon, windowTheme?: WindowTheme }
    var profile: ADKModels.Profile
}
enum SpaceModel.ContainerType { case pinned, unpinned(UnpinnedContainerType) }
enum SpaceModel.ContainerType.UnpinnedContainerType { case desktop(machineID: String, windowID: WindowID), shared }
// CodingKeys also include legacy `legacyContainerIDs` (old pinned/unpinned) and CustomInfo.windowThemeHash
```

A space normally has one `pinned` root and one `unpinned(shared)` root (the Today section). The `desktop(machineID, windowID)` variant lets a Today list belong to one machine and window instead of syncing. `SpaceModel.MachineFilter` (`machine(id)`, `all`, `current`) selects between them. The feature flag `migrate-default-space-container-ids` indicates a migration between these layouts.

### 5.5 Synthetic example

```json
{
  "version": 1,
  "sidebar": {
    "containers": [
      { "global": {} },
      {
        "spaces": [
          "00000000-0000-4000-8000-0000000000aa",
          {
            "id": "00000000-0000-4000-8000-0000000000aa",
            "title": "My Space",
            "profile": { "default": {} },
            "customInfo": { "iconType": { "emoji": "🌱" } },
            "containerIDs": [
              { "pinned": {} }, "00000000-0000-4000-8000-000000000002",
              { "unpinned": { "_0": { "shared": {} } } }, "00000000-0000-4000-8000-000000000003"
            ]
          }
        ],
        "topAppsContainerIDs": [ { "default": {} }, "00000000-0000-4000-8000-000000000001" ],
        "items": [
          "00000000-0000-4000-8000-000000000002",
          {
            "id": "00000000-0000-4000-8000-000000000002",
            "childrenIds": ["00000000-0000-4000-8000-000000000010"],
            "data": { "itemContainer": { "containerType": { "spaceItems": { "_0": "00000000-0000-4000-8000-0000000000aa" } } } },
            "createdAt": 750000000.0,
            "isUnread": false
          },
          "00000000-0000-4000-8000-000000000010",
          {
            "id": "00000000-0000-4000-8000-000000000010",
            "title": "Docs",
            "parentID": "00000000-0000-4000-8000-000000000002",
            "childrenIds": ["00000000-0000-4000-8000-000000000011"],
            "data": { "list": { "customInfo": { "iconType": { "icon": "book" } } } },
            "createdAt": 750000100.0,
            "isUnread": false
          },
          "00000000-0000-4000-8000-000000000011",
          {
            "id": "00000000-0000-4000-8000-000000000011",
            "parentID": "00000000-0000-4000-8000-000000000010",
            "childrenIds": [],
            "data": { "tab": { "savedURL": "https://example.com/", "savedTitle": "Example Domain",
                               "timeLastActiveAt": 750000200.0 } },
            "createdAt": 750000150.0,
            "isUnread": false,
            "originatingDevice": "example-machine-id"
          }
        ]
      }
    ]
  }
}
```

The exact payload under `{"default": …}` for `Profile.initial` may differ, because that enum is custom-coded. Match on the key name. The version number shown is illustrative.

### 5.6 Live folder payload

```swift
struct BaseModels.AutomaticLiveFolderData {
    let dataSource: AutomaticLiveFolderDataSource      // {"github": {}}
    var lastFetch: LastFetch?                          // { timestamp, status: {"success": {"_0": date}} | {"error": …} }
    var hiddenItems: Set<LiveItem.ID>                  // LiveItem.ID: {"url": {"_0": "…"}} | {"placeholder": {"_0": "…"}}
    var filter: AutomaticLiveFolderDataFilter?         // {"github": {"_0": PullRequestFilter}}
}
```

The tabs inside the folder reference live items by `SidebarTab.liveItemID`. The live items themselves are in `StorableLiveData.json` (§9).

### 5.7 Mutations

All edits are `BaseModels.SidebarMutation` values: `insert(item, strategy)`, `upsert(item)`, `move(itemID, strategy, indexingStyle)`, `delete(itemID)`, `rawDelete(itemID)`, `updateItem(itemID, updater)`, `insertSpace(space, index)`, `upsertSpace`, `moveSpace(spaceID, toIndex, indexingStyle)`, `deleteSpace`, `sortSpaces([ids])` and `updateSpace`. They are applied in a `SidebarDataStoreTransaction`, and the resulting `SidebarDataStoreChangeSet` drives both the UI and sync. The same enum is what `StorableFirebaseSyncDebugState.json` records.

---

## 6. Window themes and color palettes

A space's look is `SpaceModel.customInfo.windowTheme`:

```swift
struct BaseModels.WindowTheme {
    var background: AppearanceBasedConfiguration<Background>
    var windowAppearance: AppearanceBasedConfiguration<Appearance>?     // light | dark
    var primaryColorPalette: PrimaryColorPalette   // tintedLight, midTone, shaded, shadedDark
    var semanticColorPalette: AppearanceBasedConfiguration<SemanticColorPalette>
}
enum AppearanceBasedConfiguration<A> { case single(A), appearanceBased(light: A, dark: A) }
struct WindowTheme.Background { var style: Style; var contentOverBackgroundAppearance: Appearance?; var isVibrant: Bool }
enum Background.Style { case color(ColorType) }
enum Background.Style.ColorType { case basicColor(Basic), blendedSingleColor(BlendedSingle), blendedGradient(BlendedGradient) }
```

| Struct | Fields |
|---|---|
| `BasicColorConfiguration` | `color`, `translucencyStyle?` (`light`/`dark`/`auto`) |
| `BlendedSingleColorConfiguration` | `color`, `translucencyStyle?`, `modifiers` |
| `BlendedGradientConfiguration` | `baseColors[]`, `overlayColors[]`, `translucencyStyle?`, `modifiers`, `wheel` (`complimentary`/`analogous`) |
| `BlendedBackgroundModifiers` | `noiseFactor`, `intensityFactor`, `overlay` (`grain`/`sand`/`denim`/`tweed`) |
| `SemanticColorPalette` | `foregroundPrimary`, `foregroundSecondary`, `foregroundTertiary`, `maxContrastColor`, `minContrastColor`, `backgroundExtra`, `background`, `focus`, `hover`, `cutoutColor`, `title`, `subtitle` |
| `ARCUI.StorableColor` | `colorSpace` (`"extendedSRGB"`), `red`, `green`, `blue`, `alpha` (0 to 1 floats; extended sRGB may exceed that range) |

A synthetic `single` basic theme fragment:

```json
"windowTheme": {
  "background": { "single": { "_0": {
    "style": { "color": { "_0": { "basicColor": { "_0": {
      "color": { "colorSpace": "extendedSRGB", "red": 0.2, "green": 0.4, "blue": 0.9, "alpha": 1 }
    } } } } },
    "isVibrant": true
  } } },
  "primaryColorPalette": { "tintedLight": { "…": "StorableColor" }, "midTone": { "…": "…" },
                           "shaded": { "…": "…" }, "shadedDark": { "…": "…" } },
  "semanticColorPalette": { "single": { "_0": { "foregroundPrimary": { "…": "StorableColor" } } } }
}
```

Other color enums: `BaseModels.StandardColor` (`yellow`, `pink`, `red`, `lightGreen`, `darkGreen`, `purple`, `lightBlue`, `darkBlue`, `black`) and the brand palettes `BrandColorPalettes.Standard`, `Success` and `Error`.

---

## 7. Profiles and the Chromium User Data directory

```swift
enum ADKModels.Profile { case initial, custom(ProfileID) }     // custom-coded keys: "default", "custom"
struct ADKModels.ProfileID { var directoryBasename: String; var machineID: String }
struct ADKModels.BrowserContextID { var contextType: BrowserContextType /* normal, incognito… */; var profile: Profile }
struct ADK.BrowserContextAttributes { let directoryBasename: String; let userVisibleName: String; let userColor: NSColor? }
```

| Arc profile | JSON | Chromium directory |
|---|---|---|
| The first profile, "Default" (may be renamed "Personal") | `{"default": …}` | `User Data/Default/` |
| Each additional profile | `{"custom": {directoryBasename: "Profile 1", machineID: "…"}}` (likely shape) | `User Data/Profile 1/`, `Profile 2/`, … |
| Incognito windows | `BrowserContextType` ≠ normal | Chromium off-the-record context, nothing persisted |

- **One profile, many spaces.** Several spaces can point at the same profile and then share cookies, history, passwords and extensions. Favorites are per profile (`topAppsContainerIDs[profile]`), so every space on a profile shows the same favorites.
- **What lives in each Chromium profile:** the standard Chromium files, including `History`, `Bookmarks`, `Login Data`, `Cookies`, `Preferences`, `Extensions/`, `Local Storage/`, `IndexedDB/` and so on. Arc does not use Chromium's bookmark model for the sidebar. The sidebar is entirely in `StorableSidebar.json`. The profile's display name and color are kept by Chromium in `User Data/Local State`. Arc sets them through `setProfileUserVisibleName(for:name:completion:)`.
- **The machine ID** is part of the profile identity because profile folders are local to one Mac. The decoder requires both fields ("Decoding context requires directoryBasename and machineID fields"). Older files that stored a bare string (`ProfileID.V1CodingKeys.rawValue`) are backfilled with the current machine (`machineIDForProfileBackfill`).
- **Profile management:** profiles are created with `createBrowserContext(userVisibleName:)` and deleted with `deleteBrowserContext(directoryBasename:)`. "Delete unused profiles" removes directories that no space uses. The user default `defaultProfileDirectoryBasename` and the migration flag `didAttemptDefaultProfileNameMigrationToPersonal` track renaming of the default profile.
- **Encryption:** Chromium data (cookies, saved passwords) is encrypted with the "Arc Safe Storage" key in the login Keychain. Copying `User Data` to another Mac or user does not make those values readable.
- **Per-profile maps elsewhere:** `StorableLiveData.liveDataPerProfile`, `BlockListsData.blockListsPerProfile` and `excludedDomains`, `Archive.AutoArchiveTimeThresholdsPerProfile`, `PreviewsDataStore` keys, and `StorableCommandBarAdditionalRankingData.dataByProfile` (keyed by a profile string).

---

## 8. Sync

Arc has two sidebar sync engines. Both share one reducer (`SidebarSyncCloudKit.SidebarSync`, whose `State` holds `firebaseSyncState`, `cloudKitSyncState` and `sharedSyncState`). Which one runs is decided by `BaseModels.SyncMode`: `undetermined`, `iCloud`, `firebase` or `unsupported`. **Only the `global` container syncs.** Incognito, Little Arc and standalone containers stay local.

### 8.1 What is synced

- Every `SidebarItem` in the global container: tabs with their saved URL, title and favicon, folders, splits, Notes and Easel references, tab groups, and favorites roots.
- Every `SpaceModel`, including title, icon, theme and profile reference.
- The ordered list of space IDs and the favorites-root map.

**Not synced** by these engines: open-window state (`StorableWindows`), archive, Chromium data (history, passwords, cookies, extensions), and settings other than the few `SyncedPreferencesClient` keys stored in Firestore. Notes, Easels and Boosts sync through their own Firestore collections. Per-machine Today lists (`unpinned(.desktop(machineID, windowID))`) let unpinned tabs stay on one Mac.

### 8.2 iCloud (CloudKit), the legacy engine

- **Container:** `iCloud.net.arc.sidebar`, private database, one custom zone (the string `SidebarZone-4` suggests the zone name carries a format generation). `CloudKitContainerClient.SyncEngine.SyncMetadata { zoneID, hasCreatedCustomZone, hasCreatedPrivateSubscription, serverChangeToken }`.
- **Records:** one CKRecord per item, per space and for the container. `ZoneSyncData` keeps a local mirror: `container: SyncedValue<SyncedContainer>`, `items` and `spaceModels` (each `SyncedValue { value, encodedCKRecordFields (archived CKRecord system fields), lastChangeDate }`), plus `syncMetadata`, `lastSuccessfulSyncDate` and `lastSyncErrorState`. Favicons travel as a separate record field (`decodeRecordFaviconPNGData`).
- **`SyncedContainer`:** `{ topAppsContainerIDs, orderedSpaceIDs, version }`. A version mismatch shows "Incompatible Arc versions in iCloud (%i vs %i)" and sets `CloudKitSyncStatus.localVersionOutdated`.
- **Change flow:** push notifications plus a `serverChangeToken` for incremental fetch (`fetchRemoteChanges`). `fetchRemoteSnapshot` and `resetContainer` handle recovery.
- **Conflicts:** a `serverRecordChanged` error is resolved in `resolveConflict(with:)` by comparing client and server records. The UI messages cover the cases: "Your devices may be out of sync", "Client has newer changes", "Your iCloud is full!", "iCloud limit exceeded".
- **Being phased out:** the strings include "Introducing Arc Sync! End-to-end encrypted, fast, and doesn't rely on iCloud", and the flags `i-cloud-sync-deprecation-ui-enabled` and `new-user-cloud-kit-sync-enrollment-disabled`. When CloudKit is still active, the Firebase engine's `SyncHealthStatus.notWorking(.cloudKit)` reflects it.

### 8.3 Arc Sync (Firebase / Firestore, end-to-end encrypted)

**Wire unit.** Each item, each space, and a few metadata documents are one Firestore document in a per-user sidebar-sync collection. Document IDs carry a type prefix (strings `space|`, `metadata|`, `metadata|updateMarker`). The visible fields are:

| Field | Meaning |
|---|---|
| `encryptedData` | the encrypted JSON of the `SidebarItem`, `SpaceModel` or ordered-space list |
| `encryptedKey`, `publickey` | the per-document key, wrapped for the user's key pair |
| `encryptionKeyId` | which sync key encrypted it |
| `upsertTimestamp` | server timestamp; documents without one are rejected (`missingServerTimestamp`) |
| `device` | originating machine |
| `schemaVersion` | writer's schema |
| `dataEra` | generation counter (see below) |
| `debug_title`, `debug_url`, `debug_parentId`, `debug_profile`, `debug_itemType`, `debug_isContainer`, `debug_childrenIds`, `debug_spaceNameKey` | **plaintext** debug fields, written only when the flag `firebase-sidebar-sync-push-debug-info-enabled` is on |

**Metadata documents** (`FirebaseSidebarSyncCollection.MetadataDocument`): `orderedSpaces`, `currentEncryptionKeyHash`, `dataEra` and `wipeInProgress`. Schema migration markers are `schemaV4SpaceOrderDocument` and `schemaV6UpdateMarkerDocument`. An `encryptedDocumentsIds` list tracks documents during key re-encryption.

**Local mirror.** It is kept in `StorableSidebar.firebaseSyncState`:

```swift
struct FirebaseSidebarSyncCommon.PersistedFirebaseSidebarSyncState {
    var syncData: SyncData            // { dataEra?, items: [id: FirebaseSyncedValue<SidebarItem>],
                                      //   spaceModels: [id: FirebaseSyncedValue<SpaceModel>],
                                      //   orderedSpaceIDs: FirebaseSyncedValue<[spaceID]>? }
    var firebaseSidebarUnrecoverableError: FirebaseSyncUnrecoverableErrorType?
    var unacknowledgedItemDeletions: Set<Identifier<SidebarItem>>
    var lastSyncedTimestamp: Date?
    var currentPublishTransactionRetryCount: Int?; var currentPublishTransactionRetryState: PublishRetryState?
    var publishInProgress: Bool?
    var syncHealthStatus: SyncHealthStatus   // healthy | off | loading(…) | notWorking(…)
}
struct FirebaseSidebarSyncModel.FirebaseSyncedValue<A> { var value: A; var lastChangeDate: Date; var lastChangedDevice: String? }
```

**Publishing.**

1. Local mutations are diffed into a `SidebarFirebaseServerUpdate { upsertItems, upsertSpaces, deletedItemIDs, deletedSpaceIDs, orderedSpaceIDs? }`.
2. Bursts are coalesced by a `TimeThrottlingRebatcher` (`maxWaitTime` and `minGapTime`, set by the flags `firebase-sync-event-max-wait-time-ms` and `firebase-sync-event-min-gap-time-ms`).
3. The update is written in a Firestore **transaction** (`PublishTransaction`), which first validates that the current encryption key matches the remote `currentEncryptionKeyHash`.
4. Failures are retried with backoff (`PublishRetryState { nextAttempt, lastAttempt, attemptCount }`). `transactionFailedDueToCongestion` and `permissionDenied` are tracked separately. After too many failures the engine stops with `publishTransactionFailedTooManyTimes`.

**Receiving.** A snapshot listener yields `SidebarUpdatesBatch { updates: [upsert | delete | undecodable | ignored], metadata { isAbandoningOldData, dataEra } }`. Decryption or decoding failures become `undecodable` with a reason (`schemaTooLow`, `missingEncryptedKey`, `sidebarItemDecodeFailure`, …) and are skipped rather than corrupting the tree.

**Conflict handling.** These points are inferred from type names and log strings:

- **Last writer wins per document.** Each value carries `lastChangeDate` and `lastChangedDevice`, and the server orders writes by `upsertTimestamp`. There is no field-level merge: an item or space is replaced as a whole.
- **Deletes win over stale upserts.** Local deletions stay in `unacknowledgedItemDeletions` until the server confirms them, so a late-arriving upsert does not resurrect the item. The log line "Detected deletion and upsert of the same document" covers the race.
- **Orphan protection.** If an item arrives before its parent, or its parent was deleted elsewhere, `Type2OrphanProtectionResult` and `OrphanSavePlan` keep the orphan and re-upsert or protect its parents instead of dropping data. Debug tooling also tracks "zombie" split views (`ZombieSplitSeenLocation`).
- **Schema gating.** `FirebaseSidebarSyncSchemaClient` tracks the client's read, write and preferred schema versions and the last committed remote version (stored in `StorableFirebaseLastSeenSchemaVersion.json`). A remote version newer than the client gives `SchemaError.gotFutureVersion`, and then `clientVersionTooOld` (you must update Arc).
- **Data eras and wipes.** `dataEra` lets one device declare that older data should be abandoned (for example after the user chooses "abandon data" during key recovery). A `wipeInProgress` metadata document coordinates a full remote wipe (`FirebaseSyncWipeoutState`).

**Encryption.** It uses libsodium (the `Sodium` module).

- **Password.** Enabling sync asks for a sync password (`EnableSync.State.Step.passwordEntry`). It is hashed with `crypto_pwhash` (Argon2 is available, `PWHash.Alg.Argon2ID13`), and the hash is kept locally as `hashedPassword`. `EncryptionClientError.saltTooShort` hints at a salt check.
- **Hybrid scheme.** Each document is encrypted with a fresh symmetric key, and that key is wrapped with the user's public key (`EncryptionClient.EncryptedEntity { encryptedData, encryptedKey, publicKey }`, `HybridEncryption`). Several keys can coexist (`encryptionKeysByID`). The active one is advertised remotely by hash (`currentEncryptionKeyHash`), and a key change re-encrypts all documents (`MatchEncryptionKeysTransaction`).
- **Recovery phrase.** `EncryptionRecoveryClient.secretToRecoveryPhrase` turns the key into words. Arc can save a "recovery card" image to Downloads. On a new device you enter the password or the phrase (`recoveryPhraseEntry`). If both are lost you can abandon the remote data (`abandonDataScreen`).
- **Local key file.** `StorableFirebaseEncryptionKey.json` holds `hashedPassword: [UInt8]` and `encryptionKeysByID: {keyID: [UInt8]}` as JSON byte arrays. **Treat it like a password: never commit or share it.**

### 8.4 Other cloud data

| Data | Store | Notes |
|---|---|---|
| Account | Firebase Auth plus a Firestore user doc (`RemoteUser { id, name, email, avatar1024String, avatar128String, createdAt }`) | `StorableAuthState.json` caches the session |
| Notes | Firestore `documents` / `arcDocuments` | Mirrored locally in `StorableARCDocuments/` |
| Easels | Firestore `easels`, `objects`, `memberships`, `presence`, `readStates`, `readStatesPerParticipant` (+ Storage for images) | Only the image cache is local |
| Boosts | Firestore `boosts`, `boostSnapshots` | Only `locallyEnabledBoostIDs` is local |
| Shared spaces, folders and splits | Firestore (`ARCFirebaseSharableArcObjects`) | `SharableArcObjectsData { id, author, creatorID, data }` |
| Synced preferences | Firestore, one `value` field per `ArcUserDefaultSettings` key | `SyncedPreferencesClient` |
| History (mobile and Dia) | Firestore fields `encryptedURLSuffix`, `title`, `lastVisited` | `FirebaseClient.HistoryDocumentFieldIDs`. Not used for Arc Mac history, which stays in Chromium. |

Firebase project identifiers ship in `Arc.app/Contents/Resources/GoogleService-Info.plist` (values `<redacted>` here).

---

## 9. Other files in detail

### `StorableWindows.json`

```swift
struct StorableWindows.StorableWindows {
    var version: Int
    var sidebarViewPreferences: SidebarViewPreferences?   // { sidebarMode: anchored|noChrome, sidebarWidth }
    var windows: [CodableWindowData]?
    var lastFocusedSpaceID: Identifier<SpaceModel>?
    var platformData: PlatformWindowsData?                // empty on macOS
}
struct SharedWindowFeature.CodableWindowData {
    var id: WindowID; var focusedSpaceID: Identifier<SpaceModel>; var sidebarMode: SidebarMode
    var itemLastActiveDates: [ItemID: Date]; var itemCreatedDates: [ItemID: Date]   // flat arrays; drive auto-archive
    var stayOnTop: Bool; var sidebarWidth: CGFloat
    var windowContentsState: WindowContents.State     // open panes, split state, peek/modal state
    var style: WindowStyle                            // .standard(sidebarContext: global|standalone|incognito) | .little(PersistedLittleBrowserState)
    var expandedItems: [ItemID: SidebarItemExpansionState]   // .expanded | .peeked([ids])
    var spacesWithCollapsedPinnedSections: Set<SpaceID>
    var platformData: PlatformWindowData?
}
```

Whether windows are restored at launch depends on the user default `windowRestorationSetting` (`preserveTabsAndWindows`, `closeTabsAndWindows` or `useSystemSetting`).

### `StorableArchiveItems.json`

```json
{ "version": 1,
  "items": [ "00000000-0000-4000-8000-000000000020",
    { "sidebarItem": { "id": "00000000-0000-4000-8000-000000000020", "childrenIds": [],
                       "data": { "tab": { "savedURL": "https://example.com/old", "savedTitle": "Old page" } },
                       "createdAt": 749000000.0, "isUnread": false },
      "reason": "auto",
      "archivedAt": 750100000.0,
      "source": { "space": { "_0": "00000000-0000-4000-8000-0000000000aa" } } } ] }
```

The `reason` is `auto`, `manual`, `clearButton` or `clearTabGroup`. The `source` is `{"space": {"_0": id}}`, `{"littleArc": {}}`, `{"standaloneSidebar": {}}` or `{"unknown": {}}`. Older files used `spaceID_legacy`.

### `StorableLinkRouting.json`

`rules` is an array of `LinkMatchingRule { id, sourceComponents: [{ id, componentType: {"urlMatch": {"_0": {"contains": {}}, "_1": "example.com"}} }], destination }`. The `destination` is `{"space": {"_0": ProfileDestination}}` or `{"littleArc": {"_0": …}}`, and a `ProfileDestination` is `{"space": {"_0": spaceID}}`, `{"profile": {"_0": Profile}}` or `{"mostRecent": {}}`. `defaultDestination` has the same shape.

### `StorableKeyBindings.json`

`userOverrides: [KeyBinding]`. Each entry is `{ action: {identifier, name}, default?: {shortcut, priority, typeTravelTriggers}, state: {"valid": {"_0": shortcut}} | {"conflict": …} | {"unset": {}}, source, priority }`, where a shortcut is `{ deviceIndependentModifierFlags: <NSEvent.ModifierFlags raw int>, keyEquivalent: "t" }`.

### `StorableLiveData.json`

`liveDataPerProfile` is a flat array of `[Profile, LiveItemsData]` pairs. `LiveItemsData.items` is a flat array of `[LiveItem.ID, LiveItem]` pairs, where `LiveItem { id, data (custom-coded: pullRequest/notion/googleDrive/confluence/googleCalendar/chat/liveFolderAction), lastModified?, lastViewed?, firstSeen? }`. Pull requests (`BaseModels.PullRequest`) include repository, author, status, checks and stack membership.

### `StorableHome.json`

`preferences.dataSourcePreferences` is a flat array of `[HomeBadgingSourcePreference, Bool]` pairs (`documents`, `desktop`, `screenshot`, `capture`, `download`). `lastSelectedHomePage` is one of `downloads`, `archive`, `easelsAndNotes`, `screenshotsAndCaptures`, `boosts` or `spaces`. `permissions.folderToPermissions` is a flat array of `[URL, Properties]` pairs.

### `StorableAuthState.json`

`session` is `AuthSession { user: { id, name, email?, avatarUrl, createdAt }, finishedOnboarding (default true), wasExistingUser (default true), emailChangePendingVerification?: { previousEmail, newEmail } }`. It contains no tokens.

### `StorableMembershipCard.json`

`{ version, backgroundBlobInfo: [Int], paletteNumber: Int, shapeName: String, title: String }`. The card is regenerated from these values.

### `StorableCommandBarAdditionalRanking.json`

`dataByProfile: { "<profile key>": { recentlySwitchedToTabs: [itemID, CappedStack<Date>…], queriesToSelectedArchetype: { "<query>": { archetype, selectedAt } }, typeTravelUsage: [DedupKey, { executed, frequency }…] } }`. A `CappedStack` is `{ elements: [...], maxSize }`. A `DedupKey` is `search`, `normalizedHumanReadableURL`, `titleAndHost`, `tab`, `document`, `easel`, and so on. This file holds the queries you typed, so treat it as private.

### `StorableSessionRestorationData.json`

`mapping` is a bidirectional map from `TabOwnerId { itemId, browser }` to Chromium `TabSessionID { value: Int }`. It lets a sidebar tab reattach to its Chromium session (back/forward history) after relaunch. The flags are `use-session-restoration` and `use-session-restoration-writer`.

### `StorableDefaultBrowserPrompts.json`

`scheduledNext?` and `displayHistory` (a `Stack { elements }`) hold `DisplayEvent { type: afterOnboarding|day2|afterTrial (each with its UI state), timestamp }`.

---

## 10. Migrating off Arc

Arc stops working on December 22, 2026 (according to the farewell-banner copy in this build). The data that matters is:

| You want | Where it is | How to get it out |
|---|---|---|
| Spaces, pinned tabs, folders, favorites, Today tabs | `StorableSidebar.json` | `scripts/tools/export_sidebar.py` (below) |
| Tabs that were auto-archived | `StorableArchiveItems.json` | same script, "Archived tabs" section |
| Tabs that disappeared recently | `StorableSidebar.<date>.json` backups | same script, "Recovered from older snapshots" |
| History, Chromium bookmarks, extensions | `User Data/<Profile>/` | `scripts/backup-user-data.sh` exports CSV and TSV per profile |
| Passwords | Chromium `Login Data` (Keychain-encrypted) | Arc → Settings → Passwords → Export, or `arc://password-manager/passwords`, then import the CSV elsewhere |
| Notes, Easels | Firestore (+ local mirrors) | Arc's own "Export notes" and "Export All Easels" menu items |
| Boosts | Firestore | Copy the CSS out of the Boost editor. No bulk export was found. |

### `scripts/backup-user-data.sh`

This script refuses to run while Arc is running (the databases may be inconsistent), then:

1. `rsync`s `~/Library/Application Support/Arc` into `vault/user-data/Application Support/` (gitignored, `chmod 700`). It skips regenerable caches: `Cache/`, `Code Cache/`, `GPUCache/`, shader and Dawn caches, `component_crx_cache/`, `Safe Browsing/`, `OptimizationHints/`, `WidevineCdm/`, `optimization_guide_*` and `Singleton*`.
2. Converts `~/Library/Preferences/company.thebrowser.Browser*.plist` to XML.
3. Runs `export_sidebar.py` into `vault/user-data/export/`.
4. Exports each Chromium profile (`User Data/Default` and `User Data/Profile*`) into `export/profiles/<name>/`:
   - `Bookmarks.json` (Chromium bookmarks, which are separate from Arc's sidebar)
   - `history.csv`, from a *copy* of the `History` SQLite database, with Chromium timestamps converted from the 1601 epoch
   - `extensions.tsv`, with each extension's ID, name, version and Chrome Web Store URL taken from `Extensions/*/*/manifest.json`

Cookies and passwords in the backup stay encrypted with the "Arc Safe Storage" Keychain key, so the backup alone cannot decrypt them. That is why passwords should be exported from Arc.

### `scripts/tools/export_sidebar.py`

Usage: `python3 -I scripts/tools/export_sidebar.py [<arc-data-dir>] [<out-dir>]`. The data directory defaults to `~/Library/Application Support/Arc` and the output directory to `arc-export`.

What it does, step by step:

1. **Loads the global container.** It reads `StorableSidebar.json`, takes `sidebar.containers`, and picks the first container object that has an `items` key (that is the global container in the flat `[type, container, …]` array).
2. **Builds an item index** from `items` (keeping entries that are objects with an `id`), the `spaces` list, and `topAppsContainerIDs` (decoded with `pairs()`).
3. **Walks each space's `containerIDs`.** Labels are decoded with `case()`: `pinned` becomes **Pinned** and `unpinned` becomes **Today**. Each root item's `childrenIds` are followed recursively, with cycle protection.
4. **Converts each item:**
   - `tab`: its title (user title, else `savedTitle`, else URL), `savedURL`, and the page title if it differs
   - `list`, `tabGroup`, `splitView`, `itemContainer`: folders (default names "Folder", "Tab Group", "Split View")
   - `easel`, `arcDocument`, `sharedObject`: a note that the content lives in Arc's cloud or local store, not at a URL
   - creation dates converted from the 2001 epoch to ISO 8601
5. **Exports favorites per profile.** The `default` profile becomes "Favorites" and other profiles become "Favorites (other profile)".
6. **Adds archived tabs** from `StorableArchiveItems.json` (`items` → `sidebarItem.data.tab.savedURL`), with `archivedAt` and `reason`, newest first.
7. **Recovers older tabs.** It scans every `StorableSidebar.*.json` backup and collects tab URLs that are in neither the live sidebar nor the archive, recording the backup file each was last seen in.
8. **Writes three files:**
   - `bookmarks.html`: a Netscape bookmark file (root "Arc" → per-space folders with Pinned and Today subfolders, plus Favorites, Archived tabs and Recovered). It imports into Chrome, Dia, Zen, Firefox, Safari, Brave, Edge, Orion and others.
   - `sidebar.json`: the clean tree `{favorites, spaces[{id, title, pinned, today}], archived, recoveredFromSnapshots}`.
   - `sidebar.md`: the same tree as a Markdown outline.

It prints a summary line: `spaces=N live_urls=N archived=N recovered=N`.

**Known limits** (taken from the code, useful if you extend it):

- It does not export space themes or icons.
- Shared and per-machine (`desktop`) Today roots both decode to the label `unpinned`. If a space has more than one Today root, only the last one is exported.
- It does not resolve Live Folder items to PR metadata.
- Notes and Easels are not exported. Use Arc's own exporters for those.

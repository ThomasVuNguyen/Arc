# Arc for macOS 1.174.0: network services, integrations, feature flags and telemetry

This document maps what Arc (The Browser Company, macOS build `1.174.0`, bundle version `91305`, built 19 Nov 2026) talks to on the network, which third-party services it integrates with, which remote feature flags it reads, and what telemetry it sends. It also looks at what is likely to keep working once Arc's servers are turned off. Arc says it is "sunsetting on December 22, 2026".

## How this was produced, and caveats

- **Static analysis only.** Everything here comes from the shipped app bundle: printable strings of the main binary, Swift type metadata reconstructed from the binary, `Info.plist`, entitlements, and the JSON/plist resources inside the app's resource bundles. No traffic was captured, and no private user data was opened.
- **Presence is not proof of use.** Arc 1.174 is built from a monorepo it shares with The Browser Company's newer browser, **Dia**. Many modules, analytics events and endpoints in the binary are Dia features (Supertab, Skills, "Morning Brief", artifacts, connected apps, billing). They are compiled in but probably dormant in Arc. Where a host or feature is clearly Dia-only, this document says so.
- **"Inferred" means inferred.** Purposes are reconstructed from nearby strings, type names and field names. Flag types are inferred from naming and from the flag system's value types (`bool`, `string`, `number`, `json`); the in-binary defaults are compiled constants and mostly not recoverable as strings.
- **Credentials are redacted.** The binary embeds several client credentials: LaunchDarkly mobile keys, a Firebase/Google API key, Google OAuth client IDs and one client secret, a Microsoft app ID, a Filestack API key, a Sentry DSN, Datadog and Segment client tokens. None of them are reproduced here. Where one matters, it is written as `<redacted>`.

---

## 1. Backend map (first-party hosts)

### 1.1 All first-party hosts found

| Host | Owner | Purpose (inferred) |
|---|---|---|
| `arc.net` | Arc | Marketing site and the web side of several in-app features: `/privacy`, `/release-notes`, `/boosts?ref=arc-app` (Boosts gallery), `/farewell` (sunset page), `/wemightnotmakeit`, `/get-started-with-arc`, `/welcome-to-arc`, `/max/tutorial`, `/gift/…` (gift/referral links), `/recovery-help`. `/api/redirect-links/image?url=` is an image proxy for "Copy Quote as URL" links. `/easel`, `/note`, `/object` are the web hosts for shared Easels, Notes and shared objects. `webcredentials:arc.net` is the associated domain for password and passkey autofill. |
| `start.arc.net` | Arc | Terms of use, release notes, privacy-rights-by-region page. |
| `resources.arc.net` | Arc (Zendesk help centre) | Help articles linked from the UI (Boosts, Profiles, Spaces, Sync, Updates, Ad blocker, Arc Max…). `thebrowsercompany.zendesk.com` is used for support requests. |
| `content.arc.net` | Arc | **Remote config.** Fetches `web_content_behavior.json`, `command_bar_behavior.json` and `memory_behavior.json` (a bundled copy of the first ships in the app, see 1.9). `sso_embed_behavior.json` is also named, as a local resource. |
| `releases.arc.net` | Arc | **Sparkle update feed** (`https://releases.arc.net/updates.xml`) and DMG/delta downloads. `releases.arc.net.s3.us-east-2.amazonaws.com` is the S3 origin behind it. |
| `releases.browserinternal.com` | TBC internal | Internal update feeds (canary, release-candidate, prototype, per-pull-request builds), reached with an access token. Not used by public builds. |
| `incoming.browserinternal.com` | TBC internal | `/bug-report`, the endpoint for in-app bug reports. |
| `thebrowser.company` | TBC | Company site (linked from the About window). |
| `ai-service.diabrowser.engineering` | TBC (Dia infra) | `/aiproxy`, the main **LLM proxy** used by the "Universal" LLM client. `ai-service.staging.…/eval/aiproxy` and `ai-service-eval.…/eval/aiproxy` are staging and evaluation variants. |
| `aiproxy.diabrowser.engineering` | TBC | `/api/dia-claude-stream`, a streaming Claude proxy. |
| `webresultproxy.diabrowser.engineering` | TBC | `/api/claude-stream`, `/api/open-ai-chat-stream`, `/api/web-results`: older LLM streaming proxies and a web-search results proxy. |
| `websearch.diabrowser.engineering` | TBC | `/api/web-results`, a **web search proxy**. Types point to Brave Search behind it (`BraveSearchEngine`, with "vercel" and "aws" proxy versions). |
| `artifactcdn.diabrowser.engineering` | TBC | CDN for "artifacts" (a Dia feature). |
| `dia-blocklists-release.diabrowser.engineering` | TBC | **Ad-block list mirror.** Arc's native ad blocker fetches `manifest.json` and the individual filter lists from here (see 1.8). |
| `auth.diabrowser.com`, `www.diabrowser.com`, `help.diabrowser.com`, `status.diabrowser.com`, `releases.diabrowser.com` | Dia | Dia's site, auth, help, status page and update host. Arc links to Dia for its migration path ("Download Dia", "Move to Dia"). `releases.diabrowser.com` appears in the same allow-list as Arc's release hosts. |
| `bcny-arc-server` (Firebase project) | Google Firebase | Auth, Firestore, Cloud Functions and Cloud Storage for accounts, sync, Boosts, Easels, Notes, sharing and referrals (see 1.2 to 1.5). The dev project is `bcny-arc-server-dev`. |
| `iCloud.net.arc.sidebar` (CloudKit container) | Apple iCloud | Legacy sidebar sync over CloudKit (production environment), being phased out (see 1.3). |
| `thebrowsercompany.sentry.io` / `o298668.ingest.sentry.io` | Sentry | Crash and error reporting (see section 4). |

The `BCNY` prefix that shows up in many identifiers (`BCNYBuildDate`, `X-BCNY-Encryption-Context`, `BCNYBlocklists`, `bcny-arc-server`) is The Browser Company of New York.

### 1.2 Auth and accounts

- **Identity provider: Firebase Authentication** in project `bcny-arc-server`, with **email + password** sign-in (`signIn(email, password)`, `sendPasswordReset`, `verifyCurrentPassword`, email verification and verified email change). The Firebase SDK talks to Google's standard Identity Toolkit and Secure Token endpoints (`…/v1/token?key=<redacted>`). The Firebase API key is in the binary and is `<redacted>` here.
- The **user profile** is a Firestore document with `name`, `email`, `avatar1024String`, `avatar128String` and `createdAt`.
- **Keychain access groups**: `S6N382Y83G.company.thebrowser.browser.auth` holds auth tokens and `…browser.webauthn` holds passkeys. The `com.apple.developer.web-browser.public-key-credential` entitlement lets Arc act as a browser passkey (WebAuthn) client.
- **Onboarding** (`AuthFeature`) has stages `welcome`, `syncSetup`, `signIn`, `closedSignups` and `setup`. The `ClosedSignupsScreen` state (email input plus "Download Dia" and "Copy Dia link" actions) shows that **new Arc sign-ups are closed** and new users are pointed at Dia.
- **Delete account** (`DeleteAccountFeature`) runs an exit survey (reasons: slow, frequently crashing, resource intensive, difficult to use, privacy concerns, missing features, other), re-verifies the password, writes a "deleted user" document to Firestore and then deletes the Firebase user. It links to GDPR info and the help email.
- **Referrals and invites** (`ReferralCodeClient`): `getOrCreateReferralCode` (with times used, maximum uses, days until the next code) and `hasReferralsAvailable`, plus a `redeemedInviteCount` read from Firebase that unlocks custom app icons. The Firebase client also exposes `createRedirectLink`, a server-side helper used for quote and share links.
- **Membership card**: a locally rendered "member since" card with an anniversary accessory, shareable as an image. Its state is stored locally.
- **Remote sign-out**: the LaunchDarkly flag `arc-force-sign-out-enabled` exists. The `extra-refresh-token-verification-enabled` and `refresh-token-throttle-timing-in-seconds` flags control how often the Firebase refresh token is re-checked.

### 1.3 Sync

Arc has two sync generations:

| Generation | Transport | Details |
|---|---|---|
| Legacy | **CloudKit** private database, container `iCloud.net.arc.sidebar` (production), custom record zone plus push subscription (`aps-environment: production`) | `SidebarSyncCloudKit`, `CloudKitContainerClient`. Flags `sidebar-sync-cloudkit`, `new-user-cloud-kit-sync-enrollment-disabled` and `i-cloud-sync-deprecation-ui-enabled` show it being retired. |
| Current | **Firebase Firestore** ("Firebase Sidebar Sync") | `FirebaseSidebarSyncClient` publishes upserts and deletes of sidebar items, spaces and the ordered space list, with schema versions, the originating device and a `dataEra` used for wipe and reset. |

- **End-to-end encryption.** Sync payloads are encrypted client-side. The types show `missingEncryptedKey` and `missingPublicKey` ingestion errors, a `FirebaseSyncRemoteEncryptionClient` that checks whether the remote data is encrypted by a known or unknown key, and the bundled `Sodium` (libsodium) library.
- **Recovery card and phrase.** `EncryptionRecoveryClient` converts the sync secret to a mnemonic recovery phrase and back. The UI offers a downloadable "recovery card" and a lost-recovery-card flow (flag `lost-recovery-card-flow-enabled`). Help: `resources.arc.net/…/Arc-Sync#recoverycardsandrecoveringsynceddata`.
- **Other synced data seen in types**: history documents (`encryptedURLSuffix`, `title`, `lastVisited`) and synced preferences (`value`).
- Sync tuning flags: `firebase-sidebar-sync-enabled`, `firebase-sync-event-max-wait-time-ms`, `firebase-sync-event-min-gap-time-ms`, `firebase-sidebar-sync-extra-validation-enabled` and related flags (see section 3).

### 1.4 Sharing

| Feature | Backend |
|---|---|
| **Shared folders, spaces and split views** ("share collection") | Firestore collection `sharedCollections`, via `SharableArcObjectsClient` (fields `id`, `author`, `creatorID`, `data`). The link is an `arc.net` URL with a slug. Analytics: `shareCollectionClicked`, `shareCollectionLinkCreated`, `sharedCollectionAddedToSidebar`. A privacy confirmation is shown before a collection is shared. |
| **Easels** (shared canvases) | Firestore documents with sub-collections, a presence pinger for live collaborators, and Firebase Storage for images (`EaselClient`). The web view is at `arc.net/easel`. Share states are `publicReadable` and `publicWritable`. |
| **Arc Notes** | Stored as Firebase-backed documents (`DocumentsClient`), web view at `arc.net/note`. Notes are being phased out: the app has an export flow (`export-arc-notes-*` flags, `disable-notes-editor`, `disable-new-note-entry-points`) that zips the notes locally. |
| **Copy Quote as URL** | `arc.net/api/redirect-links/image?url=` plus the `createRedirectLink` function. |
| **Boost sharing** | See 1.5. |

### 1.5 Boosts (site customisations) and the gallery

- Boosts are stored **per user in Firestore**, in the collections `boosts` and `boostSnapshots` (`BoostsStorageFirebaseImpl`). Locally, the app only keeps which boost IDs are enabled (`StorableBoostsData.locallyEnabledBoostIDs`).
- A boost holds `css`, `js`, a font, a text transform, a text zoom level, "zaps" (hidden elements) and a colour scheme (colour wheel or theme driven), plus a host pattern, author, title and a drawn signature.
- **Sharing** creates a *snapshot* (`createBoostSnapshot`) and uploads a preview image to Firebase Storage. Boosts that contain JavaScript cannot be shared (`CannotShareReason.hasJS`).
- The **Boosts gallery** is a web page (`https://arc.net/boosts?ref=arc-app`). There is no separate gallery API in the binary; installing from a link goes through the `boostRemoteOpened` → `boostInstallDialogOpened` → `boostInstalled` flow.
- Boost JS and CSS are injected through internal `arc://boost/v2/css/…` and `arc://boost/v2/js/…` URLs.
- Flags: `boosts-v2-enabled`, `boost-sharing-enabled`, `boosts-in-arc-home-enabled`, `boosts-v2-monaco-enabled` (Monaco code editor).

### 1.6 AI / LLM ("Arc Max" and related)

**Transport.** No direct calls to `api.openai.com`, `api.anthropic.com` or Google's Gemini endpoints were found. All model traffic goes through The Browser Company's proxies on `*.diabrowser.engineering` (see 1.1). Requests carry the headers `X-Client-Version`, `X-Request-Environment` and `X-User-Message-ID`, plus `feature`, `isDev`, `requestID` and `version` fields in the body. Responses can be encrypted ("Watchtower", with the `X-BCNY-Encryption-Context`, `X-Response-Encrypted` and `X-Server-Data-Encrypted` headers).

**Proxy-side safety and abuse signals** surfaced as client errors: `safety_violation`, content filter, too many requests, "client update required", too many input or output tokens, and "Request blocked for suspicious activity", with reason codes such as `bot_identity`, `brute_forcing`, `account_mining`, `ai_farming`, `credential_stuffing`, `account_compromised` and `unsafe_content_use`.

**Client model families (`LLM.ModelProvider`)**: `chatGPT`, `claude`, `universal` (the multi-provider proxy). Model identifiers in the binary:

| Provider | Model IDs / enum cases |
|---|---|
| OpenAI | `gpt-3.5-turbo`, `gpt-3.5-turbo-16k`, `gpt-3.5-turbo-1106`, `gpt-4`, `gpt-4-32k`, `gpt-4-turbo-preview`, `gpt-4o`, `gpt-4o-mini`, `gpt-4o-2024-11-20`, `gpt-4.1`, `gpt-4.1-2025-04-14`, `o1`, `o1-mini`, `o1-preview`, `o3`, `o3-mini`, `o4-mini`, `gpt-5.1`, `gpt-5.2`, `gpt-5.6-luna`, `gpt-5.6-sol`, `gpt-6-luna`, `gpt-6-astra`, `gpt-6.1-sol`. Embeddings: `text-embedding-ada-002`, `text-embedding-3-small`, `text-embedding-3-large`. |
| OpenAI fine-tunes (org `the-browser-company`) | Fine-tunes of `gpt-3.5-turbo-1106` (tab grouping and Ask Arc), `gpt-4o-2024-08-06` (`inline-citations`), `gpt-4o-mini-2024-07-18` (`memory-query-parsing`) and `gpt-4.1-2025-04-14`. The fine-tune ID suffixes are omitted here. |
| Anthropic | `claude-v1`, `claude-v1-100k`, `claude-instant-v1`, `claude-instant-v1-100k`, `claude-instant-1`, `claude-2`, `claude-3-haiku-20240307`, `claude-3-sonnet-20240229`, `claude-3-opus-20240229`, `claude-3-5-sonnet-20240620`, `claude-sonnet-4`, `claude-sonnet-4-5@20250929` (a Vertex-style ID), `claude-sonnet-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`, `claude-opus-4-5`, `claude-opus-4-6`, `claude-opus-4-8`, `claude-opus-5`, `claude-opus-5-5`. UI labels: "Most capable Claude model", "Great for most tasks", "Advanced reasoning & coding". |
| Google | `gemini-2.0-flash`, `gemini-2.0-flash-lite`, `gemini-3-pro`, `gemini-3-flash`. |
| On-device (`AIInfraProtocols`) | MLX-based local LLM IDs `phi3_5`, `llama_3_2`, `gemma2b`, `qwen205b`, `openelm270m`, plus local DistilBERT / "compact BERT" classifiers with LoRA config. These are most likely Dia or experimental. |

Tokenizer files are downloaded from `openaipublic.blob.core.windows.net` (`cl100k_base`, `o200k_base`, `p50k_base`, `r50k_base` tiktoken encodings, GPT-2 `vocab.bpe`) for client-side token counting.

**LLM features (`LLM.LLMFeature`)** sent as the `feature` tag: `renamePinnedTabs` (Tidy Tab Titles), `hoverCards` (5-second previews), `askInPage` (Ask on Page), `renameDownloads` (Tidy Downloads), `askArc`, `callArc`, `mobileAskInPage`, `pinchToSummarize`, `groupTabs` (Tidy Tabs), `selfDriving`, `scrapingEval`, `pageCategorization`, `please`, `supertabs`, `connectedData`, `memory`, `classifier`. QoS classes are `userBlocking`, `userNonBlocking` and `background`.

**Arc Max is opt-in.** The onboarding copy says "Arc Max requires that we send data to our AI partners. If you don't opt in, it's never sent." Flags that gate individual AI features include `rename-pinned-tabs-using-ai`, `rename-downloads-using-ai`, `hover-cards-enabled`, `hover-cards-llm-delay-interval`, `ask-in-page-enabled`, `browse-for-me-enabled` and `ask-arc-content-guidelines`. The likely default for the last one, found next to the flag list, is "Content related to illegal activity and self-harm is not allowed."

**ChatGPT in the command bar** is not an API call. It opens `chat.openai.com` with the query in a URL parameter; the parameter names and the model value are remote-configurable (`gpt-command-bar-integration-*` flags).

### 1.7 Search providers

- **Default search and suggestions**: Google (`google.com/search?q=`, `google.com/complete/search?q=`). DuckDuckGo and Neeva URL templates are also present, and users can add custom site searches (`arc://settings/searchEngines`).
- **Site search shortcuts** (command bar) are built in for Google Drive/Docs/Maps/Flights/Images/News, YouTube, Wikipedia, GitHub (repositories and code), Stack Overflow, Amazon, Reddit, X/Twitter, Threads, TikTok, LinkedIn, Pinterest, Netflix, Spotify, SoundCloud, Apple Music, Goodreads, Figma, Dropbox, Asana and others.
- **AI web search** (Browse for Me, Ask Arc): the `websearch` / `webresultproxy` hosts (Brave Search behind a proxy). There is also a **fallback that scrapes Google results** in a hidden web view. It has twelve remote-overridable CSS/XPath selector flags (`google-search-engine-*-override`) and parses Google "one-box" answers (weather, currency, flights, sports and so on). Analytics: `webSearchEngineRequestBegan/Completed`, `webSearchWithFallbackScrapingSession*`.

### 1.8 Ad blocking and blocklists

- The native ad blocker (`native-ad-blocker` flag, `BlockListClient`) ships with bundled copies of **EasyList** (about 2.0 MB) and **EasyPrivacy** (about 1.5 MB) plus a manifest of **46 known lists**: EasyList, EasyPrivacy, AdGuard Ads/Cookies/Spyware/Social, uBlock filters, CookieMonster, EasyList Social, Fanboy third-party, about 35 regional lists, and a first-party `BCNYBlocklists` list.
- The lists are refreshed from `https://dia-blocklists-release.diabrowser.engineering/manifest.json`, with each list's URL mirrored under the same host (for example `…/easylist.to/easylist/easylist.txt`).
- Lists can be selected per profile, and domains can be excluded. `auto-disable-u-block-on-allow-listed-domains-enabled` and `multiple-ad-blockers-sidebar-banner-enabled` handle the case where a uBlock extension is installed alongside the native blocker.

### 1.9 Software updates (Sparkle)

| Item | Value |
|---|---|
| Framework | Sparkle with a custom UI driver (`SoftwareUpdaterClient`) |
| Appcast (public) | `https://releases.arc.net/updates.xml` (`SUFeedURL`) |
| EdDSA public key (`SUPublicEDKey`) | `PuVxvsbwitqWEvMPriVhNzmiMiVp2AqD8psqG/qcS98=` (public by design) |
| Automatic checks | `SUEnableAutomaticChecks = true`, `SUAutomaticallyUpdate = true`, `SUScheduledCheckInterval = 28800` (8 h) |
| Feeds | `release`, `releaseCandidate` ("Early Birds"), `canary`, `prototype`, `pullRequest(n)`, `test`. Non-release feeds live on internal hosts and need an access token (`setAccessTokenProvider`). |
| Minimum version | `setMinimumVersionRequirementMode` and `--enforce-minimum-version` support a forced minimum version. |
| Kill switch | `--disable-software-updater` launch argument. The `auto-updates-enabled` remote flag also gates updates. |
| Telemetry | `appUpdateAvailable`, `appUpdateDownloaded`, `appUpdateWillInstall(OnQuit)`, `autoUpdate*` analytics, and Sentry events for check, download and install failures. |

"Early Birds" is the release-candidate channel. Its privacy addendum (in the binary) says Early Birds builds **send crash dumps tied to your email**, kept for four weeks.

### 1.10 Remote assets and config

| Source | Contents |
|---|---|
| `content.arc.net/web_content_behavior.json` (bundled fallback in `ARC_WebContentBehaviorConfigurationClient`) | `keepaliveAllowList` (21 entries), `pipDisallowList` (Slack, Google Meet, Teams), `pipSiteConfigs` (per-site picture-in-picture controls for Twitch, Meet, YouTube, Spotify, Netflix), `tidyTitles` (52 per-site title clean-up rules), `tabSuspensionBlocklist` (Notion). Fetched by a generic `RemoteConfigClient` that keeps a local cache file. |
| `content.arc.net/command_bar_behavior.json`, `memory_behavior.json` | Command-bar ranking and behaviour, "memory" behaviour. |
| LaunchDarkly | Feature flags (section 3). |
| `ARC_TopDomains/TopDomains.json`, `TLD-short-list.json`, `_App/popularDomains.json` (2,891 domains) | Bundled, offline: domain and site-name lists used for autocomplete and onboarding favourites. |
| Favicons | `google.com/s2/favicons?sz=…&domain_url=` (Google favicon service) |
| App links | For "open in app" suggestions: the site's `/.well-known/apple-app-site-association` plus `itunes.apple.com/lookup?bundleId=` (`UniversalLinks` module) |
| Avatar placeholder | `gravatar.com/avatar/000…?d=mp` |

---

## 2. Third-party integrations

Most integrations reuse the user's **existing web session in Arc** (cookies in a hidden or incognito web view) rather than OAuth. Only the hover **Previews** for Google Calendar and Outlook use real OAuth.

| Service | Mechanism | Endpoints / scopes (names only) | Used by |
|---|---|---|---|
| **Google Calendar** | OAuth 2.0 (installed-app flow; client ID `<redacted>`; redirect `com.googleusercontent.apps.<redacted>:/oauthredirect`) | Auth `/o/oauth2/v2/auth`, token `oauth2.googleapis.com/token` (also `/oauth2/v4/token`); scopes `calendar.events.readonly` and `userinfo.email`; API `googleapis.com/calendar/v3/calendars/primary/events` and `googleapis.com/oauth2/v1/userinfo` | Pinned-tab hover Previews (next meeting) |
| **Google Calendar (Live Calendar)** | Session based: seeds an incognito profile with the user's cookies and intercepts the Calendar web app's own events and calendars requests | `calendar.google.com` | Live calendar preview and meeting reminders (`calendar-live-preview-*` flags, `liveCalendar*` events) |
| **Gmail** | Session based: Gmail Atom feed (parsed as XML) | `mail.google.com` | Unread-mail hover preview |
| **Microsoft Outlook / 365** | OAuth 2.0 via Microsoft identity platform (app ID `<redacted>`; redirect `login.microsoftonline.com/common/oauth2/nativeclient`) | `/oauth2/v2.0/authorize`, `/oauth2/v2.0/token`; scopes `mail.readwrite user.read offline_access calendars.read`; Graph `v1.0/me/`, `me/calendar/calendarView`, `me/mailFolders/Inbox/messages` | Outlook Mail and Calendar Previews |
| **GitHub** | Session based scraping of `github.com/pulls` (no API token). JavaScript extracts PR state, diff stats, files changed, conflicts, unresolved conversations and awaited reviewers. | Search qualifiers such as `is:pr is:open`, `review-requested:@me`, `author:@me`, `review:approved` | **Live Folders** (GitHub PRs), flags `enable-git-hub-live-folders` and `git-hub-live-folders-team-review-enabled` |
| **Slack** | Session based: uses the logged-in `app.slack.com` web client's local config and session cookie | Web API methods `conversations.open`, `conversations.history`, `conversations.replies`, `users.conversations`, `search.modules.messages`, `chat.postMessage`, `activity.mentions`, `client.counts`-style unread counts; `edgeapi.slack.com/cache/` | `LiveSlackClient`, mostly a Dia "connected apps" feature |
| **Notion** | Session based: Notion's private web API | `app.notion.com/api/v3/` `search`, `loadPageChunk`, `queryCollection`, `getSpacesInitial`, `syncRecordValuesMain`, `saveTransactionsMain`, `getNotificationLog`, `getPageVisitors` | `LiveNotionClient`, mostly Dia. Arc itself uses `notion.so/new` as a "new doc" shortcut. |
| **Linear, Figma, Google Docs/Sheets/Slides, Replit, Confluence, Word, Meet** | Plain URL shortcuts (`linear.app/new`, `figma.new`, `doc.new`, `sheet.new`, `slide.new`, `meet.new`, `replit.com/new`, `confluence.new`, `word.new`) | none | Command bar "new …" actions |
| **YouTube** | `YouTubePlayerKit` embed (`youtube.com/embed/`) | none | In-app videos (onboarding, update summary banner) |
| **Spotify, YouTube, Netflix, Twitch, Meet** | Page-level media controls and picture-in-picture via injected scripts | none | Media controls, mini player, auto-PiP for Google Meet |
| **ChatGPT** | URL handoff to `chat.openai.com` | `?q=` style parameters (remote-configurable) | Command-bar "Ask ChatGPT" |
| **iCloud Passwords** | Prompts to install Apple's iCloud Passwords Chrome extension (`chrome-extension://pejdijmoenmkgeppbflobdenhhabjlaj/…`) | none | Onboarding (`i-cloud-passwords-*` flags) |
| **Filestack** | Upload API `filestackapi.com/api/store/S3` (API key `<redacted>`) | none | Uploading user-initiated performance traces and attachments for bug reports |
| **Zendesk, Typeform, Substack** | Links only | none | Support, surveys, newsletter |

---

## 3. Feature flags

### 3.1 How the flag system works

- **Remote store: LaunchDarkly** (iOS/macOS SDK, `LaunchDarkly` module). It streams from `clientstream.launchdarkly.com` and polls and sends events through `mobile.launchdarkly.com`. Four LaunchDarkly **mobile keys** are embedded, one per environment (`<redacted>`).
- **LaunchDarkly context**: either an identified user (Firebase user ID, account `createdAt`, `belongsToOrganization`) or anonymous (`createdAt` only), plus the app version. The app version is used for targeting and is limited to four components.
- **Flag metadata** (`FeatureFlagMetadata`): `id`, `default`, `canaryDevValue` (an alternate default for canary and dev builds) and `requiresRestart`.
- **Value sources** (`FeatureFlagValueSource`): `default` (compiled in), `remote` (LaunchDarkly) and `override`. Remote value types are `bool`, `string`, `number` and `json`.
- **Overrides** are persisted locally (`StorableFeatureFlags`), can be set from a developer "Feature Flags" UI, and can be applied transiently at launch (`transientFeatureFlagOverrides`). LaunchDarkly also keeps its own on-disk cache of the last values it received (`ld-cache-metadata`).
- Flags are generated into seven containers: **App, CommandBar, Instrumentation, Mobile, SoftwareUpdate, Unboxing (onboarding), WebContent**. In total **243 flag keys** were found. Some are Windows-only (`win-*`) or mobile-only (`mobile-*`); they are defined in the shared code but irrelevant to the macOS app.
- Whenever the flag set changes, it is reported in the `featureFlagsUpdated(featureFlags:)` analytics event, and `experimentExposure` events record experiment exposures.

**Type column legend**: `bool`, `number`, `string` and `json` are *inferred* from the key name and from the decoder types that exist (for example `ArcFarewellBannerCopy`, `PromptionURLs`, `SearchEnginesForScraping`). Where a likely default sits next to the key in the binary, it is noted.

### 3.2 App flags (179)

#### Sunset, messaging and account

| Key | Type | Meaning |
|---|---|---|
| `arc-farewell-banner-enabled` | bool | Show the sidebar "Arc is sunsetting" countdown banner (stages at 30, 14, 7, 1 and 0 days). |
| `arc-farewell-banner-copy` | json | Title and subtitle per stage (`thirtyDays`, `fourteenDays`, `sevenDays`, `oneDay`, `lastDay`). Compiled-in copy refers to December 22, 2026 and importing into Dia. |
| `arc-force-sign-out-enabled` | bool | Remotely force users to sign out. |
| `arc-updates-dialog-enabled` | bool | Show a server-driven "Arc updates" dialog. |
| `arc-updates-dialog-title`, `arc-updates-dialog-message`, `arc-updates-dialog-button-title`, `arc-updates-dialog-url` | string | Content of that dialog. `https://arc.net/wemightnotmakeit` sits next to these keys. |
| `windows-buddy-day-banner-enabled` | bool | Promo banner for Arc for Windows. |
| `plg-one-enabled-key`, `plg-two-enabled-key` | bool | Product-led-growth (referral, invite) experiments. |
| `push-one-enabled-key`, `push-two-enabled-key` | bool | Push or promotion experiments. |
| `custom-app-icons-all-access-enabled` | bool | Unlock all custom app icons without referrals. |
| `mac-os12-deprecation-ui-enabled` | bool | Show the macOS 12 deprecation UI. |
| `new-default-browser-prompts-enabled` | bool | New "set as default browser" prompts. |
| `password-change-button-enabled` | bool | Show "change password" in account settings. |
| `extra-refresh-token-verification-enabled` | bool | Re-verify the Firebase refresh token more strictly. |
| `refresh-token-throttle-timing-in-seconds` | number | Throttle for refresh-token checks. |
| `external-qa-access-for-developer-menu-enabled` | bool | Let external QA testers open the developer menu. |
| `switch-to-beta-enabled` | bool | Allow switching to Early Birds (beta). |

#### Sync, CloudKit and Firebase

| Key | Type | Meaning |
|---|---|---|
| `sidebar-sync-cloudkit` | bool | Use legacy CloudKit sidebar sync. |
| `new-user-cloud-kit-sync-enrollment-disabled` | bool | Stop enrolling new users into CloudKit sync. |
| `i-cloud-sync-deprecation-ui-enabled` | bool | Show the iCloud sync deprecation messaging. |
| `firebase-sidebar-sync-enabled` | bool | Use Firestore-based sidebar sync. |
| `firebase-sidebar-sync-push-debug-info-enabled` | bool | Push sync debug info. |
| `firebase-sidebar-sync-extra-validation-enabled` | bool | Extra validation of incoming sync updates. |
| `firebase-sync-event-max-wait-time-ms` / `firebase-sync-event-min-gap-time-ms` | number | Batching and debounce timing for sync writes. |
| `log-new-offline-items-on-sync-enabled` | bool | Log items created while offline. |
| `sync-local-debug-data-enabled` | bool | Keep local sync debug data. |
| `should-show-sync-debug-loading-state` | bool | Debug loading UI for sync. |
| `color-coded-synced-sidebar-items-enabled` | bool | Debug colouring of synced items. |
| `missing-encryption-keys-entrypoint-enabled` | bool | UI entry point when E2E keys are missing. |
| `lost-recovery-card-flow-enabled` | bool | Flow for users who lost their recovery card. |
| `migrate-default-space-container-ids` | bool | One-time migration of space container IDs. |
| `use-session-restoration` / `use-session-restoration-writer` | bool | New session-restoration reader and writer. |
| `reopened-items-store-enabled` | bool | Store for reopened (recently closed) items. |

#### Boosts, Easels and Notes

| Key | Type | Meaning |
|---|---|---|
| `boosts-v2-enabled` | bool | Boosts v2 editor and runtime. |
| `boost-sharing-enabled` | bool | Allow sharing boosts (snapshots). |
| `boosts-in-arc-home-enabled` | bool | Show Boosts in Arc Home (Library). |
| `boosts-v2-monaco-enabled` | bool | Monaco code editor for boost CSS/JS. |
| `easel-drag-optimization-enabled` | bool | Easel drag performance path. |
| `easel-search-tool-enabled` | bool | Search tool in Easels. |
| `easel-expanded-text-sizes` | bool | More text sizes in Easels. |
| `easel-exporter-enabled` | bool | "Export All Easels" as web pages (sunset tooling). |
| `export-arc-notes-enabled` | bool | Arc Notes export flow. |
| `export-arc-notes-dialog-display-count` | number | How many times the export dialog is shown. |
| `export-arc-notes-dialog-note-viewing-end-date` | string | Date after which notes become view-only or export-only. |
| `arc-note-export-document-timeout-in-seconds` | number | Per-note export timeout. |
| `disable-new-note-entry-points` | bool | Hide "new note" entry points. |
| `disable-notes-editor` | bool | Make notes read-only. |
| `unpinned-notes-insertion-strategy-enabled` | bool | Where new notes are inserted. |
| `override-super-copy-on-split-views-for-sharable-links` | bool | Cmd-Shift-C on split views copies a shareable link. |

#### AI (Arc Max) and Browse for Me

| Key | Type | Meaning |
|---|---|---|
| `rename-pinned-tabs-using-ai` | bool | Tidy Tab Titles. |
| `rename-downloads-using-ai` | bool | Tidy Downloads. |
| `hover-cards-enabled` | bool | 5-second link previews (hover cards). |
| `hover-cards-share-enabled` | bool | Share button on hover cards. |
| `hover-cards-llm-delay-interval` | number | Hover delay before calling the LLM. |
| `hover-cards-caching-enabled` | bool | Cache hover-card results. |
| `ask-in-page-enabled` | bool | Ask on Page. |
| `ask-arc-content-guidelines` | string | Content-policy text shown in Ask Arc (likely default "Content related to illegal activity and self-harm is not allowed."). |
| `browse-for-me-enabled` / `browse-for-me-pip-enabled` | bool | Browse for Me pages, and in picture-in-picture. |
| `mobile-browse-for-me-enable-fine-tuning` | bool | Use the fine-tuned model for Browse for Me. |
| `mobile-hidden-web-content-scraping-timeout-in-seconds` | number | Timeout for hidden-web-view search scraping. |
| `mobile-search-engines-for-scraping` | json | `{ engines: [...] }`, the engines scraped as fallback. |
| `instant-links-v2-enabled` / `instant-links-suggestion-enabled` / `instant-links-intent-prototype-enabled` | bool | Instant Links (open the top result directly), suggestions, intent prototype. |
| `content-extraction-hydrated-outline-enabled` | bool | Page content extraction mode for LLM context. |
| `google-search-engine-main-selector-override` | string | CSS selector override for the Google results container. |
| `google-search-engine-anchors-x-path-selector-override` | string | XPath for result anchors. |
| `google-search-engine-result-link-attribute-override` | string | Attribute holding the result link. |
| `google-search-engine-result-title-selector-override` | string | Result title selector. |
| `google-search-engine-result-description-parent-number-override` | number | Parent depth for the description node. |
| `google-search-engine-result-description-selector-override` | string | Description selector. |
| `google-search-engine-result-favicon-selector-override`, `google-search-engine-result-favicon-attribute-override` | string | Favicon selector and attribute. |
| `google-search-engine-youtube-result-selector-override`, `google-search-engine-youtube-result-link-attribute-override`, `google-search-engine-youtube-result-link-prefix-override`, `google-search-engine-youtube-result-title-selector-override` | string | Selectors for YouTube results inside Google SERPs. |

#### Tabs, sidebar, split view, Little Arc and command bar

| Key | Type | Meaning |
|---|---|---|
| `tab-suspension-state-indicators-enabled` | bool | Show which tabs are suspended. |
| `sidebar-plus-button-system-menu-enabled` | bool | Native menu for the sidebar "+" button. |
| `chevron-folders-enabled` | bool | Chevron-style folder disclosure. |
| `automatic-live-folders-min-refresh-interval-in-seconds` | number | Live Folders refresh floor. |
| `enable-folder-archive` | bool | Archive whole folders. |
| `allow-disable-archive` / `allow-debug-archive-timing` / `per-profile-auto-archive-pref-available` | bool | Auto-archive controls. |
| `auto-archive-little-arc-windows-enabled` | bool | Auto-archive Little Arc windows. |
| `little-arc-shows-under-command-bar-enabled` | bool | Little Arc placement. |
| `little-arc-windowing-behavior-fix-enabled` | bool | Little Arc window fix. |
| `add-show-and-close-little-arc-window-to-dock-menu` | bool | Dock menu items for Little Arc. |
| `show-toolbar-in-split-view-enabled` | bool | Toolbar in split view. |
| `option-click-split-tab-close-button-to-unsplit-enabled` | bool | Option-click to unsplit. |
| `drag-to-combine-tabs-into-split-enabled` | bool | Drag tabs together to split. |
| `new-split-separation-mechanisms-enabled` | bool | New ways to separate splits. |
| `split-view-actions-hover-button-enabled` | bool | Hover actions in split view. |
| `sidebar-drag-to-split-preview-ui-enabled` | bool | Preview when dragging to split. |
| `peeked-modal-controls-alternate-order-enabled` | bool | Peek modal button order. |
| `modal-v2-native-gestures-enabled` / `modal-v2-chromium-overscroll-enabled` | bool | Peek modal v2 gestures. |
| `show-top-app-shortcuts-when-holding-cmd` | bool | Cmd-number hints on favourites. |
| `linear-tab-switcher-enabled` | bool | Linear (MRU-list) tab switcher. |
| `command-bar-calculator-enabled` | bool | Calculator answers in the command bar. |
| `status-pill-mouse-avoidance-enabled` | bool | Status URL pill moves away from the cursor. |
| `new-toast-background-enabled` | bool | New toast styling. |
| `esc-key-closes-settings-enabled` | bool | Esc closes Settings. |
| `delete-unused-profiles-button-enabled` | bool | Button to delete unused profiles. |
| `extension-side-panel-enabled` | bool | Chrome extension side panels. |
| `disable-history-clusters` | bool | Disable Chromium history clusters ("Journeys"). |
| `mini-player-marquee-title-enabled` | bool | Scrolling title in the media mini player. |

#### Calendar, Meet and media

| Key | Type | Meaning |
|---|---|---|
| `calendar-live-preview-enabled` | bool | Live calendar preview on pinned Calendar. |
| `calendar-live-preview-multi-cal-support` | bool | Multiple calendars. |
| `calendar-live-preview-min-fetch-interval-in-seconds` | number | Fetch throttle. |
| `calendar-live-preview-max-minutes-visible-after-start` | number | How long an event stays visible after it starts. |
| `google-meet-auto-picture-in-picture-enabled` | bool | Auto-PiP when leaving a Meet tab. |
| `meet-pip-chat-button-enabled` | bool | Chat button in the Meet PiP window. |

#### Updates

| Key | Type | Meaning |
|---|---|---|
| `auto-updates-enabled` | bool | Master switch for automatic updates. |
| `new-auto-update-heuristic-enabled` | bool | New "when to auto-restart" heuristic. |
| `auto-update-inactivity-delay-in-seconds` / `auto-update-required-idle-duration-in-seconds` | number | Idle requirements before auto-restarting. |
| `active-forms-blocking-restart-disabled` | bool | Ignore partly filled forms when deciding to restart. |
| `update-complete-banner-video-link-enabled` | bool | Video link in the "updated" banner. |
| `update-summary-banner-video-link-title`, `update-summary-banner-video-link-url` | string | That video link. |

#### Rendering, windowing and performance

| Key | Type | Meaning |
|---|---|---|
| `window-dragging-via-webcontents-enabled` | bool | Drag windows from web content areas. |
| `page-swipe-controller-internal-scrolling-state-optimization-enabled` | bool | Swipe-navigation optimisation. |
| `certificate-transparency-enabled` | bool | Enforce Certificate Transparency. |
| `lifetime-violations-reporting-enabled` | bool | Report object-lifetime (leak) violations. |
| `reduced-tab-flashing-lite-enabled` / `reduced-tab-flashing-lite-max-placeholder-time` | bool / number | Reduce flashing on tab switch. |
| `toolbar-display-height` | number | Toolbar height. |
| `metal-window-background-rendering-enabled` | bool | Metal-rendered window background. |
| `use-metal-by-default` | bool | Metal by default. |
| `use-arc-drag-swift-ui-modifier` | bool | Custom drag modifier. |
| `sidebar-dark-mode-bias` | number | Tint bias for dark sidebars. |
| `battery-saver-mode-ui-enabled` | bool | Battery saver UI. |
| `fullscreen-animations-enabled` / `fullscreen-resize-on-screen-change-enabled` | bool | Fullscreen behaviour. |
| `skia-graphite-disabled` | bool | Disable Chromium's Skia Graphite backend. |
| `disable-compositor-recycling` | bool | Chromium compositor recycling. |
| `global-window-content-reparenting-enabled` / `reparented-window-content-placeholders-enabled` | bool | Move web contents between windows without reloading. |
| `lightweight-accessibility-mode` | bool | Reduced accessibility tree for performance. |
| `chromium-enabled-features` / `chromium-disabled-features` | json/string | Remote list of Chromium `--enable-features` / `--disable-features`. |
| `replace-permission-display-with-content-settings` | bool | Site permissions UI uses Chromium content settings. |
| `mac-unified-device-emulation-frame-architecture` | bool | DevTools device emulation frame. |
| `native-ad-blocker` | bool | Built-in ad blocker. |
| `auto-disable-u-block-on-allow-listed-domains-enabled` | bool | uBlock coexistence. |
| `multiple-ad-blockers-sidebar-banner-enabled` | bool | Warn when several ad blockers are active. |
| `record-chromium-crash-keys-in-sentry` | bool | Attach Chromium crash keys to Sentry events. |

#### Windows-only keys (shared definitions, not used on macOS)

`win-use-bindable-vector-reset-for-command-bar`, `win-remove-scroll-bar-from-command-bar-enabled`, `win-spaces-scroll-view-manual-snapping-enabled`, `win-recycle-native-widget-on-tab-switch`, `win-allow-mouse-wheel-space-navigation`, `win-keep-rounded-surface-size`, `win-deprecate-sidebar-flip-view`, `win-new-folder-icon-view-enabled`, `win-debug-self-enabled`, `win-default-browser-prompts-enabled`, `win-apply-staged-update-on-quit`, `win-max-features-enabled`, `win-drag-to-split-enabled`, `win-enable-drag-to-reorder-spaces`, `win-ignored-gpu-blocklist-rules`, `win-device-emulation-frame-enabled`, `win-detour-handle-delegated-input-before-version`, `win-tickle-message-loop-after-cmd-bar-ranking`, `win-rebuild-sidebar-content-on-dpi-change`, `win-use-dispatch-queue-handle`, `win-explicit-xaml-shutdown-enabled`. All are booleans or version strings for Arc on Windows (WinUI/XAML).

### 3.3 CommandBar flags (6)

| Key | Type | Meaning |
|---|---|---|
| `boost-type-travel-actions-for-unboxing` | bool | Rank "type travel" actions higher for new users. |
| `search-what-you-typed-provider-enabled` | bool | "Search for what you typed" suggestion provider. |
| `memory-store-suggestions-enabled` | bool | Suggestions from the local "memory" store. |
| `gpt-command-bar-integration-query-query-parameter` | string | Query-string key used when handing a query to ChatGPT. |
| `gpt-command-bar-integration-model-query-parameter` | string | Query-string key for the model. |
| `gpt-command-bar-integration-model-query-value` | string | Model value passed to ChatGPT. |

### 3.4 Instrumentation flags (8)

| Key | Type | Meaning |
|---|---|---|
| `sentry-sampling-config` | json | Sentry sample rates per app environment (`AppEnvironmentSamplingConfig`), observed live. |
| `memory-usage-event-sampling` | number/json | Sampling for `processMemoryUsed` events. |
| `mx-metrics-logging` | bool | Log MetricKit payloads. |
| `produce-view-report-on-invalid-geometry-enabled` | bool | Report NaN or infinite view frames. |
| `analytics-interaction-instrumentation-client-enabled` | bool | Interaction latency instrumentation. |
| `analytics-interaction-metrics-sampling-config` | json | Its sample rates. |
| `windows-layout-cycle-tracing-enabled` | bool | Windows layout-cycle tracing. |
| `sidebar-snapshot-analytics-enabled` | bool | Periodic `sidebarStructureSnapshot` and `spaceStructureSnapshot` events. |

### 3.5 Mobile flags (23, Arc Search for iOS, shared definitions)

`mobile-app-store-review-prompts-enabled`, `mobile-non-animated-launch-enabled`, `mobile-image-resizing-api`, `mobile-ignore-open-as-universal-link-enabled`, `mobile-ignore-universal-link-logic-v2-enabled`, `mobile-promotion-urls` (json `PromptionURLs`: title, url, isTemporary, isDefaultTab, isSearchResult), `mobile-dark-mode-plugin-enabled`, `mobile-snapshot-throttle-duration-in-seconds`, `mobile-history-store-migrations-enabled`, `mobile-collect-history-metadata-enabled`, `mobile-purge-zero-visit-history-items-enabled`, `mobile-internal-broken-website-reporting-enabled`, `mobile-fix-swipe-back-navigation-on-same-ur-ls-enabled`, `mobile-web-view-link-detector-disabled`, `mobile-cookie-autoconsent-enabled`, `mobile-cookie-autoconsent-manual-evaluation-enabled`, `mobile-optimistically-fetch-web-page-image-enabled`, `mobile-ios-18.1-plus-button-workaround-enabled`, `mobile-prevent-google-search-restoration`, `mobile-arc-search-updates-toast-enabled`, `mobile-arc-search-updates-toast-title` (likely default "Updates to Arc Search"), `mobile-arc-search-updates-toast-message` (likely default "Tap to learn more"), `mobile-arc-search-updates-toast-url`.

### 3.6 SoftwareUpdate flags (7)

| Key | Type | Meaning |
|---|---|---|
| `software-update-relaunch-animation-enabled` | bool | Animated relaunch after an update. |
| `software-update-relaunch-animation-exit-duration`, `software-update-relaunch-animation-enter-duration`, `software-update-relaunch-animation-enter-shimmer-duration` | number | Its timings. |
| `new-update-summary-banner-enabled` | bool | "What's new" banner after updating. |
| `new-update-available-banner-enabled` | bool | "Update available" banner. |
| `update-complete-sparkle-timeout-in-seconds` | number | Timeout waiting on Sparkle after an update. |

### 3.7 Unboxing (onboarding) flags (9)

| Key | Type | Meaning |
|---|---|---|
| `recovery-mnemonic-after-sign-in-enabled` | bool | Show the sync recovery phrase after sign-in. |
| `skip-and-auto-select-onboarding-favorites-enabled` | bool | Auto-pick favourites from browsing history. |
| `auto-select-favorites-engagement-threshold` | number | Engagement needed to auto-select a favourite. |
| `simple-edu-enabled` | bool | Simplified onboarding education. |
| `secure-text-reveal-button-enabled` | bool | "Show password" button. |
| `i-cloud-passwords-in-onboarding-enabled` | bool | Offer iCloud Passwords during onboarding. |
| `i-cloud-passwords-configuration-popup-workaround-enabled` | bool | Workaround for the extension popup. |
| `i-cloud-passwords-configuration-url` | string | Likely default is the iCloud Passwords extension popup URL. |
| `i-cloud-passwords-configuration-popup-reload-delay-in-milliseconds` | number | Delay before reloading the popup. |

### 3.8 WebContent flags (11)

| Key | Type | Meaning |
|---|---|---|
| `translate-enabled` | bool | Built-in page translation. |
| `media-tray-for-recording-tabs-enabled` | bool | Media tray for tabs using the camera or microphone. |
| `disable-tab-suspension-block-list` | bool | Ignore the remote tab-suspension blocklist. |
| `high-cpu-usage-while-in-background-freezing-enabled` | bool | Freeze background tabs that use a lot of CPU. |
| `ignore-disable-pi-p-attribute` | bool | Allow PiP even when a page sets `disablePictureInPicture`. |
| `max-pending-resize-frames` | number | Resize throttling. |
| `on-web-contents-close-debug-log-enabled` | bool | Debug logging on tab close. |
| `on-web-contents-close-debug-log-max-retries`, `on-web-contents-close-debug-log-min-retries`, `on-web-contents-close-debug-log-retry-stride` | number | Its retry policy. |
| `google-meet-chromium-auto-picture-in-picture-enabled` | bool | Use Chromium's native auto-PiP for Meet. |

### 3.9 Other flag-shaped JSON types

These types are decoded from remote JSON. Their keys were not seen in the Arc flag list, so they may belong to Dia: `LoginURLPatterns` (`identityProviderHostSuffixes`, `authSubdomainPrefixes`; examples near it are `signin.aws.amazon.com` and `id.atlassian.com`), `SkillsUpsellCards`, and `SpotifyPinnedTabAnimationStyle` (`pulse` / `musicNotes` / `off`).

---

## 4. Telemetry

### 4.1 Pipelines at a glance

| Pipeline | SDK / host | What goes there |
|---|---|---|
| **Product analytics** | Segment `analytics-swift` → `api.segment.io/v1`, settings from `cdn-settings.segment.com/v1` (write key `<redacted>`) | Typed events from `AnalyticsClient.AnalyticsEvent`, plus Segment's automatic lifecycle events (`Application Installed`, `Opened`, `Updated`, `Foregrounded`, `Backgrounded`, `Hidden`, `Unhidden`, `Terminated`, `Deep Link Opened`). |
| **Logs** | Datadog Logs → `browser-intake-datadoghq.com` (US1 is the SDK default; the EU, US3, US5, AP1 and gov intake hosts are compiled in by the SDK). Client token `<redacted>`. | App logs via `DataDogLogHandler` (category, level, tags, extras). A `DatadogAnalyticsLogger` suggests analytics events are mirrored to Datadog as well. |
| **Distributed tracing** | Datadog Trace (`OTTracer`, built on `OpenTelemetryApi`) | Spans from `TracingClient` (command bar, navigation, tab close, LLM calls with `llm.input_tokens`, `llm.output_tokens`, `llm.cached_tokens`, `llm.finish_reason`, `llm.reasoning_effort`), with configurable sampling rates (`sampling_rate.configured`, `sampling_rate.target`). Local `os_signpost` tracing is also used. |
| **Crashes and errors** | Sentry Cocoa SDK → `o298668.ingest.sentry.io` (org `thebrowsercompany`; full DSN `<redacted>`) | Crashes, app-hang tracking (`enableAppHangTracking`), breadcrumbs (from the logging system), custom tags and contexts, view-hierarchy attachments, Chromium "dump without crashing" reports, and named events: `bugReport`, `uncleanShutdown`, `failedSentinelRemoval`, `appUpdate*Failed`, `adkDidNotConnectTimeout`. Sample rates come from the `sentry-sampling-config` flag. |
| **MetricKit** | Apple MetricKit through Sentry's MetricKit integration | `MXCPUException` and `MXDiskWriteException` diagnostics, which also become the analytics events `cpuExceptionDiagnostic` and `diskWriteExceptionDiagnostic`. |
| **Feature-flag events** | LaunchDarkly → `mobile.launchdarkly.com` | The LaunchDarkly SDK's standard evaluation, summary and identify events. |
| **User-initiated diagnostics** | `incoming.browserinternal.com/bug-report`, Filestack upload | Bug reports, optionally with a performance trace (a trace window warns: "be sure to close out of any tabs with URLs you aren't comfortable sharing with our team"; the trace logger has a privacy-filtering option). |
| **Firebase Analytics** | none | Disabled: `IS_ANALYTICS_ENABLED = false` in `GoogleService-Info.plist`. |

### 4.2 Identity attached to telemetry

- **Segment**: `identify` with the Firebase user ID (`userLoggedIn(userID:)`, `userUpdated(userID:)`), reset on sign-out. Events also carry an `environment` and `platform`, and a `ContextPlugin` adds `app.isDefaultBrowser` (re-checked periodically), `device.modelName` and `screen.displayCount`. Segment's standard context (OS, app version, locale, anonymous ID) applies as well.
- **Sentry**: the Sentry user is set to `{ id, email }` (`TelemetryClient.User`), so **crash reports are linked to the account email**. Builds carry `build.shortVersion` and `build.sentryReleaseName`.
- **Datadog/diagnostic environment**: the app collects `operatingSystemVersion`, `hostArchitecture`, `processArchitecture`, `logicalProcessorCount`, `physicalMemoryMB`, `availablePhysicalMemoryMB`, `localeIdentifier`, system and process uptime, and `updateInstallationMethod` into a `diagnostic_environment.json`. A detailed `device.cpu.*` feature list (brand, model, SSE/AVX/AES-NI/MTE flags and so on) also exists in the strings.
- A stable per-install **machine ID** (`MachineID`) exists and is used by several clients.
- `isIgnorable` lets the client mark an install's events as ignorable, most likely for internal or test accounts.

### 4.3 Analytics events

The `AnalyticsEvent` enum has about 640 cases. They are sent with **snake_case** names (for example `splitViewOpened` becomes `split_view_opened`), and properties are snake_case too. Another roughly 100 standalone `*Event` structs exist. A large share of all of this is **Dia-only** (Supertab, skills, artifacts, connected apps, morning brief, billing and usage limits, CLIA, welcome postcard). The Arc-relevant categories:

| Category | Example events (camelCase case names) |
|---|---|
| App lifecycle | `appLaunched(startupSource)`, `appUpdated(fromVersion, installationMethod)`, `previousAppShutdown(normal)`, `appLaunchedToFirstWindowAppeared`, `appQuit`, `featureFlagsUpdated`, `experimentExposure` |
| Default browser | `setDefaultBrowserClicked`, `defaultBrowserPrompt{Shown,ButtonClicked,Dismissed,FeedbackSubmitted}`, `onboardingDefaultBrowser*` |
| Onboarding and import | `onboardingStep{Viewed,Finished,Skipped,Completed}`, `onboardingImport{Started,Failed,Ended,Completed}`, `importedFromBrowser`, `bookmarksImported`, `safariPasswordsImport`, `onboardingDataCollectionDisclosureFinished`, `onboardingAdBlockerFinished`, `arcMaxEnabled` |
| Account | `userLoggedIn(userID)`, `userUpdated(userID)`, `userLoggedOut`, `editName/Email/ChangePassword/DeleteAccountDialogAction`, `deleteAccountStepCompleted`, `authSessionRevocationReceived/Complete`, `firebaseUserNotAvailable` |
| Spaces, profiles, sidebar | `spaceCreated/Deleted/Focused(spaceID, spaceIndex, profileType, timeSinceLastFocus…)`, `spaceStyle*`, `profileCreated/Deleted/AssignedToSpace`, `sidebarToggled`, `pinnedSectionToggled`, `folderCreated`, `itemOpened/Renamed/Moved/Shared/Unarchived`, `autoArchiveEducation*` |
| Structure snapshots | `sidebarStructureSnapshot(totalSpaces, totalProfiles, activeSpacesLast7Days, activeSpacesLast30Days)`, `spaceStructureSnapshot(spaceID, pinned item count, folder count, max folder depth, unpinned count, days since last focused, has custom icon or title)` |
| Split view, Little Arc, windows | `splitTabClicked`, `splitViewEntered/Opened`, `itemAddedToSplitView`, `littleArcMovedToStandardWindow`, `newWindowCreated`, `moveTabToWindow`, `modalExpandedToTab`, `shiftClickedLinkToOpenModal` |
| Command bar and search | `commandBarOpened`, `commandBarItemSelected`, `commandBarSiteSearchUsed`, `commandBarEnteredScopedSearch`, `commandBarPerformedChatGPTScopedSearch`, `webSearchEngineRequest*`, `webSearchWithFallbackScrapingSession*` |
| Boosts | `boostCreated`, `boostEdited`, `boostDeleted`, `boostSetIsActive`, `boostShuffled`, `boostRemoteOpened/Closed`, `boostInstallDialog*`, `boostInstalled`, `boostShareDialog*` |
| Easels, Notes, Capture | `noteCreated`, `easelCreated`, `easelEdited`, `easelObjectImpression`, `documentPrivacyChanged`, `attemptedNotesExport`, `captureInitiated/Created/Cancelled/FullPage`, `quoteLinkCreated` |
| Sharing and referrals | `shareCollectionClicked`, `shareCollectionLinkCreated`, `sharedCollectionAddedToSidebar`, `referralDialogOpened/Closed`, `referralFound`, `copyReferralCodeClicked` |
| Previews, calendar, live folders | `previewUsed`, `liveItemPreview*`, `calendarPreview*`, `calendarAuthDetected`, `liveCalendar*`, `meetingReminder*` (including `meetingReminderRelevantLinkHallucinated`), `liveFolderCreated/Deleted/Fetch/FetchError` |
| Media and PiP | `mediaControlsUsed`, `audioMiniPlayer*`, `pictureInPictureModal*`, `googleMeetBackgroundPictureInPictureTriggered` |
| AI | `autoRenamedPinnedTab`, `autoRenamedDownload(Reverted)`, `hoverCardSessionComplete`, `pageSummarized`, `browseForMe*` (including feedback, with "anonymized details about your device"), `autoOrganizeTabGroupsCompleted`, `modelUsed`, `toolCalled` |
| Ad blocking and extensions | `nativeAdBlockToggled`, `nativeAdBlockDisableScopeDialog*`, `manageAdBlockersDialog*`, `multipleAdBlockersPromptShown`, `extensionInstalled/Uninstalled/Used`, `didDisableUnstableExtension` |
| Updates | `appUpdateAvailable/Downloaded/WillInstall(OnQuit)`, `autoUpdate{FlowAborted,ForegroundTriggered,Queued}`, `sleepSatisfiedForAutoUpdate`, `forcedAutoUpdateOccurred`, `softwareUpdateBannerDismissed`, `updateArcAutomaticallyToggleClicked`, `arcUpdatesDialogFunnelStageReached` |
| Sunset | `arcFarewellBannerViewed(stage, daysRemaining)`, `arcFarewellBannerButtonClicked`, `onboardingImportArcSpaces*` (the Dia-side import of Arc data) |
| Sync health | `syncEnabled/Disabled/Reset/Stopped/Suspended/Resumed`, `syncFirstCycle*`, `syncInbound*/Outbound*`, `syncFailureReported` (around 30 diagnostic fields: readiness state, data-type counts, cycle status, error counts, seconds since last success, user ID), `firestoreDiskCacheSizeDetected` |
| Performance and health | `processMemoryUsed`, `performanceHistogram`, `taskRunnerPerformance`, `interactionCompleted`, `discardOnLowMemoryPolicyMetrics`, `lightweightAccessibilityModeMetrics`, `cpuExceptionDiagnostic`, `diskWriteExceptionDiagnostic`, `sadTabAppeared`, `webContentInteractiveResize`, `encounteredUnrecoverableError` |
| Dev tools | `devToolsOpened`, `devToolsInspectElementsOpened`, `devToolsJavascriptConsoleOpened`, `devToolsNetworkPanelOpened`, `developerTabActivated` |

The properties on the cases that were inspected are mostly enums, counts, durations, booleans and internal IDs (space IDs, user ID). **Page URLs were not seen as event properties** in this static pass. That is an observation, not a guarantee.

### 4.4 Opt-out and consent

- **AI features (Arc Max) are opt-in.** Nothing is sent to AI partners unless enabled (onboarding copy).
- **Early Birds** (beta) opts you into "enhanced data collection": crash dumps tied to your email, kept for four weeks.
- Onboarding includes a **data-collection disclosure** step (`onboardingDataCollectionDisclosure*`), and the command bar shows a **search-suggestions privacy** notice.
- **No user-facing "share analytics" or "send crash reports" toggle string was found** in the binary. A general analytics opt-out may exist in a form this static pass could not see. Treat this as "not found", not "does not exist".

---

## 5. Internal URLs

### 5.1 `arc://` pages

Arc shows Chromium's WebUI pages under its own `arc://` scheme (for example, `chrome://extensions` is surfaced as `arc://extensions`). URLs referenced directly by Arc's own code:

| URL | Purpose |
|---|---|
| `arc://settings`, `arc://settings/help`, `arc://settings/searchEngines` (the strings also reference `settings/privacy` and `chrome://settings/languages`) | Chromium settings (search engines, help, privacy, languages) |
| `arc://extensions` | Extension management |
| `arc://history/` (`?q=` for search) | Full history |
| `arc://password-manager/passwords` | Password manager |
| `arc://boost/v2/css/<id>`, `arc://boost/v2/js/<id>` | Internal endpoints serving Boost stylesheets and scripts into pages |

Most other Chromium WebUI hosts are present in the bundled Chromium resources (`chrome://flags`, `chrome://version`, `chrome://gpu`, `chrome://net-export`, `chrome://downloads`, `chrome://bookmarks`, `chrome://crashes`, `chrome://policy`, `chrome://serviceworker-internals` and so on), so the `arc://` equivalents are generally reachable. `chrome://history`, `chrome://extensions` and `chrome://settings/languages` are referenced by Arc code as targets.

`about:blank?type=ask-arc` is used as a placeholder for Browse for Me / Ask Arc pages.

### 5.2 URL schemes registered by the app (`CFBundleURLTypes`)

| Scheme | Role |
|---|---|
| `http`, `https` | Default-browser handling |
| `mailto` | Mail links |
| `arcBrowser` | Arc's own scheme. The only use visible in the strings is a navigation-policy check for `arcbrowser` URLs in web content, which are intercepted and handled natively rather than loaded. No route table (path list) was recoverable from strings. |

Other app-level entry points: **AppleScript** (`Arc.sdef`; there is also a flag-gated "AppleScript JavaScript" execution and the `appLaunchedWithAppleScriptJavaScript` event), **Handoff** (`NSUserActivityTypeBrowsingWeb`), and a **Dock tile plug-in** (`company.thebrowser.arc.toDockTilePlugIn`) for custom app icons.

### 5.3 Notable launch arguments (developer/QA)

`--disable-software-updater`, `--enforce-minimum-version`, `--arc-new-window`, `--post-update-restart`, `--onboarding-force-complete`, `--onboarding-skip-wizard`, `--services-environment`, `--trace-output`, `--trace-max-duration`, `--use-mock-keychain`, `--fake-updater`, `--arc-force-crash`, `--wait-for-debugger`, `--user-data-dir`, `-cloudKitSyncEnabled`, `-shouldSkipUnboxingVideo`. Several more (`--dia-automation-*`, `--snapshot-*`, `--fixture-account`) are test automation hooks.

---

## 6. Privacy-relevant permissions

### 6.1 `Info.plist` usage descriptions

| Key | Text |
|---|---|
| `NSCameraUsageDescription` | "Websites may use your camera for features on their site." |
| `NSMicrophoneUsageDescription` | "Websites may use your microphone for features on their site." |
| `NSBluetoothAlwaysUsageDescription` | "Websites may use your bluetooth for features on their site." |
| `NSLocationUsageDescription`, `NSLocationWhenInUseUsageDescription`, `NSLocationAlwaysUsageDescription`, `NSLocationAlwaysAndWhenInUseUsageDescription` | "Websites may use your location for features on their site." |
| `NSDownloadsFolderUsageDescription` | Access to Downloads, for saving and opening downloads. |
| `NSDesktopFolderUsageDescription` | Access to Desktop, to make files accessible from Arc. |

Other relevant keys: `NSAppTransportSecurity → NSAllowsArbitraryLoads = true` (normal for a browser), `NSAppleScriptEnabled = true`, `LSFileQuarantineEnabled = true`, `LSMinimumSystemVersion = 13.0.0`. In-app copy also asks for **Full Disk Access** to import Safari history during onboarding ("Feel free to remove access when this step is finished").

### 6.2 Entitlements

| Entitlement | Meaning |
|---|---|
| `com.apple.developer.icloud-services: CloudKit`, container `iCloud.net.arc.sidebar`, environment `Production` | Legacy iCloud sidebar sync |
| `com.apple.developer.aps-environment: production` | Push notifications (CloudKit subscriptions) |
| `com.apple.developer.associated-domains: webcredentials:arc.net` | Shared web credentials with arc.net |
| `com.apple.developer.web-browser.public-key-credential` | Act as a passkey (WebAuthn) client for websites |
| `keychain-access-groups`: `…company.thebrowser.browser.auth`, `…company.thebrowser.browser.webauthn` | Auth tokens and passkeys in the keychain |
| `com.apple.security.device.camera`, `…device.audio-input` | Camera and microphone for websites |
| `com.apple.security.personal-information.location` | Location for websites |
| Team ID | `S6N382Y83G` |

---

## 7. What will likely break when Arc's servers go dark

This section is reasoning from the dependencies above, not from observed behaviour. "Servers go dark" can mean several different things: the Firebase project being shut down, LaunchDarkly or Segment being disconnected, `releases.arc.net` going away, or the AI proxies being turned off. Each has different effects.

| Area | Depends on | Expected outcome |
|---|---|---|
| **Core browsing** (Chromium engine, tabs, history, bookmarks, passwords, extensions, downloads) | Local Chromium profile | **Keeps working.** None of this needs Arc's backend. |
| **Sidebar, spaces, pinned tabs, folders** | Local `StorableSidebar` data; sync is an add-on | **Keeps working locally.** Cross-device sync stops. |
| **Being signed in** | Firebase Auth (`bcny-arc-server`) | An existing session survives *network* failures, because the Firebase SDK keeps the cached user. If the project is deleted or users are disabled, token refresh fails and the SDK signs the user out. A remote `arc-force-sign-out-enabled` flip would do the same. **Risk:** window restoration is gated on a valid auth session (the code logs "No valid auth session found. Not restoring window."), and **new sign-ins are impossible** once Auth is gone. New sign-ups are already closed in favour of Dia. |
| **Sync** (Firestore and CloudKit) | Firestore, CloudKit | Stops. Firestore's offline cache keeps the last local state. The CloudKit path depends only on the user's own iCloud, but it is deprecated and depends on Arc's container staying configured. |
| **Boosts** | Firestore collections `boosts` and `boostSnapshots` | **Fragile.** Boost contents live in Firestore, not in a local file. While the Firestore disk cache is intact and the user stays signed in, existing boosts probably still apply. Sign-out (`BoostsClientError.signedOut`), a cache wipe, or a new machine loses them. The gallery (`arc.net/boosts`) and sharing break. **Export boost CSS/JS manually before shutdown.** |
| **Easels and Arc Notes** | Firestore and Firebase Storage | **At risk.** Contents and images are server-backed. The app ships "Export All Easels" (as web pages) and an Arc Notes export (zip). Use them before shutdown. Shared `arc.net/easel` and `arc.net/note` links stop working. |
| **Shared folders, spaces and referrals** | Firestore `sharedCollections`, Cloud Functions | Shared links stop resolving. Referral codes and the invite-count-based app icon unlocks stop updating; already-unlocked icons are probably cached locally. |
| **AI features** (Tidy Tab Titles, Tidy Downloads, 5-second previews, Ask on Page, Browse for Me, ChatGPT-style answers) | `*.diabrowser.engineering` proxies | Break as soon as the proxies stop accepting Arc clients. They are shared with Dia, so they may stay up, but Arc can be cut off with a "client update required" or blocked response. The command-bar "Ask ChatGPT" handoff keeps working, because it only opens `chat.openai.com`. |
| **Search** | Google (direct), Brave via proxy for AI search | Normal search and suggestions keep working (they go straight to the search engine). AI web search breaks with the proxy. |
| **Ad blocker** | `dia-blocklists-release.diabrowser.engineering` for updates; bundled EasyList and EasyPrivacy | **Keeps working with the bundled or last-downloaded lists**, which slowly go stale. |
| **Previews** (Google Calendar, Outlook, Gmail) | Google and Microsoft APIs directly, with TBC's OAuth client IDs | Keep working as long as Google and Microsoft don't revoke Arc's OAuth clients. Gmail and Live Calendar use the user's own web session and are independent of TBC. |
| **GitHub Live Folders** | Scraping `github.com` with the user's session | Keep working until GitHub's HTML changes. Selector fixes can no longer ship. |
| **Remote config** (`content.arc.net`) | HTTP fetch with local cache | Falls back to the cached copy, then the bundled `web_content_behavior.json`. PiP and tidy-title rules freeze. |
| **Feature flags** (LaunchDarkly) | LaunchDarkly cloud | The SDK uses its **cached last values**; on a fresh install, the **compiled defaults** apply. Whatever was set last (including farewell-banner state, `auto-updates-enabled` and `arc-force-sign-out-enabled`) is effectively frozen. |
| **Updates** (Sparkle) | `releases.arc.net/updates.xml` | Update checks fail quietly; the app stays on its current version. No more security patches for the bundled Chromium, which becomes the main long-term risk. A final appcast could also push a last build or a minimum-version requirement before shutdown. |
| **Telemetry** (Segment, Datadog, Sentry, LaunchDarkly events) | Third-party SaaS | Uploads fail and are retried or dropped. No user-visible effect. |
| **Help, support, release notes, farewell pages** | `arc.net`, `resources.arc.net`, Zendesk | Links break whenever the websites are taken down. |

**No hard-coded "stop working on date X" kill switch was found.** The December 22, 2026 date appears in banner copy and in the countdown logic (with a developer override, `FarewellBannerDateOverride`). In practice, "Arc stops working" is more likely to come from server-side changes (Auth, sync, AI proxies, flags) and the end of security updates than from a local time bomb. This is an inference from static analysis.

---

### Redaction note

This file was checked for credential patterns (Google API keys, OpenAI-style keys, LaunchDarkly mobile keys, Datadog client tokens, Sentry DSNs, PEM blocks, OAuth client secrets). All such values in the binary are replaced with `<redacted>` or omitted. The Sparkle EdDSA key above is a **public** verification key published in `Info.plist`.

# Arc design system (macOS 1.174.0)

A reference of the visual design system that shipped inside **Arc for macOS 1.174.0 (build 91305)** by The Browser Company, written while Arc is being sunset. It is reconstructed from the app bundle alone: compiled asset catalogs, resource bundles, Lottie files, Metal libraries, and the Swift type metadata left in the binary.

This page lists **names, values and structure only**. Arc's images, icons, fonts, sounds, animations and videos are copyrighted by their owners and are not part of this repository. To look at them yourself, run `scripts/extract-app.sh` against your own copy of `Arc.app`; it unpacks everything into `vault/extracted/` (gitignored, never committed).

Machine-readable tokens: [`design-tokens.json`](design-tokens.json) (519 colors with light/dark values, font families, Easel text styles, Lottie timings, theme model enums, sizes, sounds).

## Contents

1. [Color](#1-color)
2. [Space theming](#2-space-theming)
3. [Typography](#3-typography)
4. [Iconography](#4-iconography)
5. [Motion](#5-motion)
6. [Sound](#6-sound)
7. [Components](#7-components)
8. [Reproducing the extraction and the contact sheet](#8-reproducing-the-extraction-and-the-contact-sheet)
9. [Method and limits](#9-method-and-limits)

---

## 1. Color

### How Arc stores color

- **519 named colors** live in the asset catalogs (`Assets.car`) of 30 resource bundles. Every one has a light value and a dark (`NSAppearanceNameDarkAqua`) value, even when both are identical.
- Each module gets a generated accessor (`<Module>.Asset.Colors`, `ColorAsset { name, color: NSColor, swiftUIColor }`), so the same token name (for example `PopoverBackground`) can exist in several bundles with slightly different values.
- 683 color renditions are sRGB, 172 are **Display P3**, and two are extended (linear) sRGB. All values below are converted to sRGB hex; tokens authored in P3 are marked `(P3)`. Example: `BrandBlue` is authored as P3 `(0.192, 0.224, 0.984)`, numerically the same as the sRGB Arc blue `#3139FB`, and lands at `#2F39FF` once converted.
- Translucency is everywhere. Most chrome tokens are black or white at a low alpha, so they sit on top of whatever color the current Space has. Opaque colors are reserved for popovers, dialogs, buttons and brand moments.
- The Space you are in drives most of the window color at runtime (see [Space theming](#2-space-theming)). The asset colors are the fixed layer on top of it. Toasts, for example, have no asset colors at all: they derive their palette from the Space theme.

### Core palette

The values that recur across bundles (count = number of light/dark slots using that exact hex):

| Role | Value | Uses | Where |
|---|---|---:|---|
| Arc blue | `#3139FB` | 21 | `PrimaryButtonFace`, `Accent`, `ButtonBackground`, `CheckboxColor`, `TextFieldFocusedBorder`, `ReadOnlyCreativeToolPrimary`, Easel dark blue, `Indigo9` (`#3138F9`/`#3239FA`) |
| Arc blue hover / pressed | `#2C33E2` / `#2A30D5` | 4 / 2 | `PrimaryButtonHovered`, `PrimaryButtonPressed`, import drop target |
| Brand blue (P3 source) | `#2F39FF` | 4 | `BrandBlue`, Ask Arc `AccentColor`, Capture toggle text |
| Cool off-white | `#FAFBFF` | 20 | `PopoverBackground`, `MenuBackground`, `PuckBackground`, dark-mode sidebar item tints (`#FAFBFF` @ 0.1 to 0.2) |
| Ink (near black) | `#0E0F10` | 9 | `ForegroundPrimary` (@ 0.9), sidebar item tints (@ 0.05 / 0.1), `SecondaryWindowInputBackground` dark |
| Home ink | `#000017` | 9 | Home/Library foregrounds and backgrounds at 0.07 to 1.0 alpha |
| Deep navy (dark surfaces) | `#120F2E`, `#151C30`, `#131C32` | 5 + | Dark modal, Capture, rich text menu, URL inputter, dark popovers |
| Brand gradient | `#FF9396` to `#0048FF` | 6 + 6 | `GradientPeach` / `GradientBlue`, `WelcomeGradientPink/Blue`, Capture overlay bubbles; `ARCUI.GradientType.peachBlue` |
| Destructive red | `#F53714` (hover `#DD3112`, pressed `#D02F11`) | 5 | Destructive button, `Vibrant.EaselRed` |
| Error red | `#C93333` / `#FF5A5F` | 6 / 4 | Error messages (light / dark), Boosts warning |
| Notes ink purple | `#2702C2`, `#220C7F` | 7 + | Rich text cursor and selection, note titles, Easel comment text |
| Focus ring | `#228CFF` | 1 | `FocusRing`, command bar hint pill text |
| Page loading border | `#0C50FF` / `#2AB6F6` | 2 | `LoadingPageBorder`, `VibrantText` (light / dark) |

### Recurring patterns

- **Radix grays.** `ARCUI` ships `Gray1` to `Gray12` and `GrayA1` to `GrayA12`. The solid scale matches Radix Colors' `gray` / `grayDark` step for step (`#FCFCFC` ... `#171717` light, `#161616` ... `#EDEDED` dark). Neutral buttons, input fields and the command bar banner use it (`Gray7` `#DBDBDB` borders, `Gray12` `#171717` text).
- **Indigo scale.** `Indigo1` to `Indigo12` is a custom 12-step scale built around Arc blue at step 9 (`#3138F9` light, `#3239FA` dark).
- **Quirk.** `GrayA1` dark is opaque `#000000` while every other `GrayA` dark step is white at an alpha. This is almost certainly an authoring slip in the catalog.
- **Sidebar and tab cells are pure alpha.** `SidebarItemBackground` `#0E0F10` @ 0.05 / `#FAFBFF` @ 0.1, hovered @ 0.1 / 0.15, current tab `#FFFFFF` @ 0.85 / `#FAFBFF` @ 0.2, previous tab @ 0.32 / 0.08. The Space color shows through.
- **Creative tool tints.** Three triads (`Primary`, `Secondary` @ 0.1, `Tertiary` @ 0.1) for Notes and Easels: `ReadOnly` (blue `#3139FB` / `#00C7F3`), `ReadAndWrite` (magenta `#C0009F` / pink `#F29BBB`), `Private` (green `#007C00` / `#00EC8D`). The names point to sharing permission states.
- **Two Easel palettes.** `Vibrant.*` and `Chill.*` each define 11 named colors (black, white, grey, yellow, pink, red, purple, light/dark blue, light/dark green). `Easel{Black,White}` invert in dark mode. They match `BaseModels.StandardColor` (`yellow, pink, red, lightGreen, darkGreen, purple, lightBlue, darkBlue, black`). The Easel export viewer uses the same values as CSS variables; default shape colors are rectangle `lightGreen`, circle `red`, arrow `lightBlue`, freehand `black`.
- **Brand palette.** 8 brand colors (`BrandBlue`, `BrandRed` `#E93800`, `BrandYellow` `#FFD335`, `BrandGreen` `#007C00`, `BrandLightGreen` `#00EC8D`, `BrandLightBlue` `#00CBF8`, `BrandMagenta` `#D200A4`, `BrandGray` `#7E7E7E`) and 10 extended ones (`Cream` `#F2EAE4`, `LightPink` `#F29BBB`, `Purple` `#AF6FA0`, `Orange` `#FF7C4A`, `Teal` `#4DBCDD`, `BlueGray` `#666789`, `Navy` `#12374A`, `Brown` `#934E1B`, `BrownPink` `#CF7F65`, `VibrantRed` `#FF0500`). The Space color picker's "Brand" row is drawn from the extended set.

### Tokens by area

Every named color, grouped by the part of the app that owns it. Values are `light` / `dark`; `@ x` is alpha. Expand a group to see its table.

#### Foundation (BaseAssets) (132)

<details><summary><code>ARCClients_BaseAssets</code>: Base and foreground (29)</summary>

| Token | Light | Dark |
|---|---|---|
| `BackgroundPrimary` | `#FFFFFF` | `#000000` |
| `BasePrimary` | `#000000` | `#FFFFFF` |
| `BasePrimaryDark` | `#FFFFFF` | `#FFFFFF` |
| `BasePrimaryLight` | `#000000` | `#000000` |
| `BaseQuaternary` | `#000000` @ 0.15 | `#FFFFFF` @ 0.15 |
| `BaseSecondary` | `#000000` @ 0.7 | `#FFFFFF` @ 0.7 |
| `BaseSecondaryDark` | `#FFFFFF` @ 0.7 | `#FFFFFF` @ 0.7 |
| `BaseTertiary` | `#000000` @ 0.3 | `#FFFFFF` |
| `DownloadProgressBarBackground` | `#CED7E7` | `#717782` |
| `FindInPageError` (P3) | `#DB1929` | `#DB1929` |
| `FindInPageSeparator` (P3) | `#000000` @ 0.1 | `#000000` @ 0.1 |
| `FloatingControlIconForeground` | `#000000` @ 0.5 | `#FFFFFF` @ 0.5 |
| `FloatingScrimBorder` | `#000000` @ 0.1 | `#FFFFFF` @ 0.2 |
| `FocusRing` (P3) | `#228CFF` | `#228CFF` |
| `ForegroundPrimary` (P3) | `#0E0F10` @ 0.9 | `#FFFFFF` @ 0.8 |
| `ForegroundSecondary` | `#000000` @ 0.5 | `#FFFFFF` @ 0.5 |
| `ForegroundTertiary` | `#000000` @ 0.3 | `#FFFFFF` @ 0.3 |
| `FullOpacityBackgroundPrimary` | `#FFFFFF` | `#000000` |
| `FullOpacityForegroundPrimary` | `#000000` | `#FFFFFF` |
| `LoadingPageBorder` | `#0C50FF` | `#2AB6F6` |
| `MoveButtonBackground` | `#FFFFFF` | `#000000` |
| `NewTabPageButtonBackground` | `#000000` @ 0.04 | `#FFFFFF` @ 0.0375 |
| `NewTabPageButtonHoveredBackground` | `#000000` @ 0.06 | `#FFFFFF` @ 0.075 |
| `PopoverBackground` (P3) | `#FAFBFF` | `#131C32` |
| `PopoverShadow` (P3) | `#131C34` @ 0.3 | `#131C34` @ 0.8 |
| `Shadow` | `#000000` @ 0.2 | `#000000` @ 0 |
| `StandaloneButtonBackground` | `#000000` @ 0.08 | `#FFFFFF` @ 0.15 |
| `VibrantSecondaryText` | `#0C50FF` @ 0.4 | `#2AB6F6` @ 0.5 |
| `VibrantText` | `#0C50FF` | `#2AB6F6` |

</details>

<details><summary><code>ARCClients_BaseAssets</code>: Brand (18)</summary>

| Token | Light | Dark |
|---|---|---|
| `BrandBlue` (P3) | `#2F39FF` | `#2F39FF` |
| `BrandExtendedBlueGray` | `#666789` | `#666789` |
| `BrandExtendedBrown` (P3) | `#934E1B` | `#934E1B` |
| `BrandExtendedBrownPink` (P3) | `#CF7F65` | `#CF7F65` |
| `BrandExtendedCream` | `#F2EAE4` | `#F2EAE4` |
| `BrandExtendedLightPink` | `#F29BBB` | `#F29BBB` |
| `BrandExtendedNavy` (P3) | `#12374A` | `#12374A` |
| `BrandExtendedOrange` (P3) | `#FF7C4A` | `#FF7C4A` |
| `BrandExtendedPurple` (P3) | `#AF6FA0` | `#AF6FA0` |
| `BrandExtendedTeal` (P3) | `#4DBCDD` | `#4DBCDD` |
| `BrandExtendedVibrantRed` (P3) | `#FF0500` | `#FF0500` |
| `BrandGray` (P3) | `#7E7E7E` | `#7E7E7E` |
| `BrandGreen` (P3) | `#007C00` | `#007C00` |
| `BrandLightBlue` (P3) | `#00CBF8` | `#00CBF8` |
| `BrandLightGreen` (P3) | `#00EC8D` | `#00EC8D` |
| `BrandMagenta` (P3) | `#D200A4` | `#D200A4` |
| `BrandRed` (P3) | `#E93800` | `#E93800` |
| `BrandYellow` | `#FFD335` | `#FFD335` |

</details>

<details><summary><code>ARCClients_BaseAssets</code>: Sidebar and tabs (15)</summary>

| Token | Light | Dark |
|---|---|---|
| `SidebarForeground` | `#000000` @ 0.3 | `#FFFFFF` @ 0.45 |
| `SidebarForegroundDarker` | `#000000` @ 0.45 | `#FFFFFF` @ 0.45 |
| `SidebarItemBackground` (P3) | `#0E0F10` @ 0.05 | `#FAFBFF` @ 0.1 |
| `SidebarItemHoveredBackground` (P3) | `#0E0F10` @ 0.1 | `#FAFBFF` @ 0.15 |
| `SidebarSeparator` | `#000000` @ 0.15 | `#FFFFFF` @ 0.15 |
| `TabCellBackgroundContentVisible` (P3) | `#FFFFFF` @ 0.7 | `#FAFBFF` @ 0.15 |
| `TabCellBackgroundCurrent` (P3) | `#FFFFFF` @ 0.85 | `#FAFBFF` @ 0.2 |
| `TabCellBackgroundMutiselected` (P3) | `#000000` @ 0.1 | `#FAFBFF` @ 0.1 |
| `TabCellBackgroundPressed` (P3) | `#0E0F10` @ 0.065 | `#FAFBFF` @ 0.065 |
| `TabCellBackgroundPrevious` (P3) | `#FFFFFF` @ 0.32 | `#FAFBFF` @ 0.08 |
| `TabCellBackgroundPreviousHovered` (P3) | `#FFFFFF` @ 0.5 | `#FAFBFF` @ 0.12 |
| `TabCellChildBackground` | `#000000` @ 0.07 | `#FFFFFF` @ 0.07 |
| `TabCellShadowBackgroundSelected` | `#FFFFFF` @ 0.9 | `#000000` @ 0 |
| `TabCellShadowSelected` | `#000000` @ 0.2 | `#000000` @ 0 |
| `TabCellSlash` (P3) | `#000000` @ 0.3 | `#FFFFFF` @ 0.3 |

</details>

<details><summary><code>ARCClients_BaseAssets</code>: Command bar (3)</summary>

| Token | Light | Dark |
|---|---|---|
| `CommandBarPlaceholderIncognitoBackground` (P3) | `#FFFFFF` @ 0.15 | `#FFFFFF` @ 0.15 |
| `CommandBarSuggestionHintPillBackground` (P3) | `#FFFFFF` | `#FFFFFF` @ 0.1 |
| `CommandBarSuggestionHintPillImageBackground` (P3) | `#000000` @ 0.03 | `#FFFFFF` @ 0.2 |

</details>

<details><summary><code>ARCClients_BaseAssets</code>: Creative tools (Notes/Easel permission tints) (9)</summary>

| Token | Light | Dark |
|---|---|---|
| `PrivateCreativeToolPrimary` (P3) | `#007C00` | `#00EC8D` |
| `PrivateCreativeToolSecondary` (P3) | `#005200` @ 0.1 | `#16F2B0` @ 0.1 |
| `PrivateCreativeToolTertiary` (P3) | `#003200` @ 0.1 | `#97F9D3` @ 0.1 |
| `ReadAndWriteCreativeToolPrimary` | `#C0009F` | `#F29BBB` |
| `ReadAndWriteCreativeToolSecondary` | `#7F0069` @ 0.1 | `#F9CDDD` @ 0.1 |
| `ReadAndWriteCreativeToolTertiary` | `#4D0040` @ 0.1 | `#FAD7E4` @ 0.1 |
| `ReadOnlyCreativeToolPrimary` | `#3139FB` | `#00C7F3` |
| `ReadOnlyCreativeToolSecondary` | `#2026A6` @ 0.1 | `#57DAF7` @ 0.1 |
| `ReadOnlyCreativeToolTertiary` | `#141764` @ 0.1 | `#99E9FA` @ 0.1 |

</details>

<details><summary><code>ARCClients_BaseAssets</code>: Easel palettes (Vibrant / Chill) (22)</summary>

| Token | Light | Dark |
|---|---|---|
| `Chill.EaselBlack` | `#000000` | `#FFFFFF` |
| `Chill.EaselDarkBlue` | `#3139FB` | `#3139FB` |
| `Chill.EaselDarkGreen` | `#1D5914` | `#1D5914` |
| `Chill.EaselGrey` | `#BBBBBB` | `#BBBBBB` |
| `Chill.EaselLightBlue` (P3) | `#30A4C0` | `#30A4C0` |
| `Chill.EaselLightGreen` (P3) | `#CED872` | `#CED872` |
| `Chill.EaselPink` | `#F2C2AC` | `#F2C2AC` |
| `Chill.EaselPurple` | `#A6729D` | `#A6729D` |
| `Chill.EaselRed` | `#D74807` | `#D74807` |
| `Chill.EaselWhite` | `#FFFFFF` | `#000000` |
| `Chill.EaselYellow` | `#C2A12A` | `#C2A12A` |
| `Vibrant.EaselBlack` | `#000000` | `#FFFFFF` |
| `Vibrant.EaselDarkBlue` | `#3139FB` | `#3139FB` |
| `Vibrant.EaselDarkGreen` | `#107A00` | `#107A00` |
| `Vibrant.EaselGrey` | `#BBBBBB` | `#BBBBBB` |
| `Vibrant.EaselLightBlue` (P3) | `#00CBF8` | `#00CBF8` |
| `Vibrant.EaselLightGreen` (P3) | `#00EC8D` | `#00EC8D` |
| `Vibrant.EaselPink` | `#FF994E` | `#FF994E` |
| `Vibrant.EaselPurple` | `#C0009F` | `#C0009F` |
| `Vibrant.EaselRed` | `#F53714` | `#F53714` |
| `Vibrant.EaselWhite` | `#FFFFFF` | `#000000` |
| `Vibrant.EaselYellow` | `#FFD335` | `#FFD335` |

</details>

<details><summary><code>ARCClients_BaseAssets</code>: Space color picker presets (36)</summary>

| Token | Light | Dark |
|---|---|---|
| `ColorPickerBrand1` | `#F2EAE4` | `#F2EAE4` |
| `ColorPickerBrand2` | `#F29BBB` | `#F29BBB` |
| `ColorPickerBrand3` | `#A6729D` | `#A6729D` |
| `ColorPickerBrand4` | `#F25E6B` | `#F25E6B` |
| `ColorPickerBrand5` | `#FF8558` | `#FF8558` |
| `ColorPickerBrand6` (P3) | `#F8D558` | `#F8D558` |
| `ColorPickerBrand7` (P3) | `#34E895` | `#34E895` |
| `ColorPickerBrand8` (P3) | `#6CBAD9` | `#6CBAD9` |
| `ColorPickerBrand9` (P3) | `#666789` | `#666789` |
| `ColorPickerDrab1` (P3) | `#4E3A5A` | `#4E3A5A` |
| `ColorPickerDrab2` (P3) | `#693558` | `#693558` |
| `ColorPickerDrab3` (P3) | `#8F4042` | `#8F4042` |
| `ColorPickerDrab4` (P3) | `#B16D40` | `#B16D40` |
| `ColorPickerDrab5` (P3) | `#D7B35D` | `#D7B35D` |
| `ColorPickerDrab6` (P3) | `#CDCCA4` | `#CDCCA4` |
| `ColorPickerDrab7` (P3) | `#7AA982` | `#7AA982` |
| `ColorPickerDrab8` (P3) | `#226149` | `#226149` |
| `ColorPickerDrab9` (P3) | `#26456B` | `#26456B` |
| `ColorPickerGreyscale1` (P3) | `#FFFFFF` | `#FFFFFF` |
| `ColorPickerGreyscale2` (P3) | `#E6E6E6` | `#E6E6E6` |
| `ColorPickerGreyscale3` (P3) | `#CCCCCC` | `#CCCCCC` |
| `ColorPickerGreyscale4` (P3) | `#B2B2B2` | `#B2B2B2` |
| `ColorPickerGreyscale5` (P3) | `#808080` | `#808080` |
| `ColorPickerGreyscale6` (P3) | `#666666` | `#666666` |
| `ColorPickerGreyscale7` (P3) | `#333333` | `#333333` |
| `ColorPickerGreyscale8` (P3) | `#1A1A1A` | `#1A1A1A` |
| `ColorPickerGreyscale9` (P3) | `#000000` | `#000000` |
| `ColorPickerPastel1` (P3) | `#FEFBFA` | `#FEFBFA` |
| `ColorPickerPastel2` (P3) | `#FFE9F3` | `#FFE9F3` |
| `ColorPickerPastel3` (P3) | `#F1D1EC` | `#F1D1EC` |
| `ColorPickerPastel4` (P3) | `#FFCBD1` | `#FFCBD1` |
| `ColorPickerPastel5` (P3) | `#FFE0D3` | `#FFE0D3` |
| `ColorPickerPastel6` (P3) | `#FFF9E5` | `#FFF9E5` |
| `ColorPickerPastel7` (P3) | `#DEFDEB` | `#DEFDEB` |
| `ColorPickerPastel8` (P3) | `#DCF3FC` | `#DCF3FC` |
| `ColorPickerPastel9` (P3) | `#C5C6E5` | `#C5C6E5` |

</details>

#### ARCUI component library (89)

<details><summary><code>ARCUI_ARCUI</code> (89)</summary>

| Token | Light | Dark |
|---|---|---|
| `ButtonDisabledBorder` | `#333333` | `#CCCCCC` |
| `ButtonDisabledFace` (P3) | `#B2B2B2` | `#819197` |
| `ContrastingButtonDropShadow` | `#D34955` @ 0.75 | `#D34955` @ 0.75 |
| `ContrastingButtonFace` | `#F36672` | `#F36672` |
| `DestructiveButtonBorder` | `#FFFFFF` @ 0 | `#FFFFFF` @ 0 |
| `DestructiveButtonDisabledFace` | `#FFC7BD` | `#673229` |
| `DestructiveButtonDisabledForeground` | `#F53714` @ 0.3 | `#FFFFFF` @ 0.172 |
| `DestructiveButtonDisabledIconBackground` | `#FFCDC4` | `#703F36` |
| `DestructiveButtonDisabledIconBorder` | `#FFFFFF` @ 0.2 | `#FFFFFF` @ 0.1 |
| `DestructiveButtonDisabledShadow` | `#DC2A09` @ 0.3 | `#B4250A` @ 0.3 |
| `DestructiveButtonFace` | `#F53714` | `#F53714` |
| `DestructiveButtonForeground` | `#FFFFFF` | `#FFFFFF` |
| `DestructiveButtonHovered` | `#DD3112` | `#DD3112` |
| `DestructiveButtonIconBackground` | `#FFFFFF` @ 0.1 | `#FFFFFF` @ 0.1 |
| `DestructiveButtonIconBorder` | `#FFFFFF` @ 0.2 | `#FFFFFF` @ 0.2 |
| `DestructiveButtonIconForeground` | `#FFFFFF` @ 0.9 | `#FFFFFF` @ 0.9 |
| `DestructiveButtonPressed` | `#D02F11` | `#D02F11` |
| `DestructiveButtonShadow` | `#B4250A` @ 0.3 | `#B4250A` @ 0.3 |
| `DimmedWindowControls` | `#000000` | `#F3F3EA` |
| `Gradient1` | `#F19E9C` @ 0.2 | `#F19E9C` @ 0.2 |
| `Gradient2` | `#1B46F5` | `#1B46F5` |
| `GradientBlue` (P3) | `#0048FF` | `#0048FF` |
| `GradientPeach` (P3) | `#FF9396` | `#FF9396` |
| `Gray1` | `#FCFCFC` | `#161616` |
| `Gray10` | `#858585` | `#7E7E7E` |
| `Gray11` | `#6F6F6F` | `#A0A0A0` |
| `Gray12` | `#171717` | `#EDEDED` |
| `Gray2` | `#F8F8F8` | `#1C1C1C` |
| `Gray3` | `#F3F3F3` | `#232323` |
| `Gray4` | `#EDEDED` | `#282828` |
| `Gray5` | `#E8E8E8` | `#2E2E2E` |
| `Gray6` | `#E2E2E2` | `#343434` |
| `Gray7` | `#DBDBDB` | `#3E3E3E` |
| `Gray8` | `#C7C7C7` | `#505050` |
| `Gray9` | `#8F8F8F` | `#707070` |
| `GrayA1` | `#000000` @ 0.012 | `#000000` |
| `GrayA10` | `#000000` @ 0.478 | `#FFFFFF` @ 0.446 |
| `GrayA11` | `#000000` @ 0.565 | `#FFFFFF` @ 0.592 |
| `GrayA12` | `#000000` @ 0.91 | `#FFFFFF` @ 0.923 |
| `GrayA2` | `#000000` @ 0.027 | `#FFFFFF` @ 0.026 |
| `GrayA3` | `#000000` @ 0.047 | `#FFFFFF` @ 0.056 |
| `GrayA4` | `#000000` @ 0.071 | `#FFFFFF` @ 0.077 |
| `GrayA5` | `#000000` @ 0.09 | `#FFFFFF` @ 0.103 |
| `GrayA6` | `#000000` @ 0.114 | `#FFFFFF` @ 0.129 |
| `GrayA7` | `#000000` @ 0.141 | `#FFFFFF` @ 0.172 |
| `GrayA8` | `#000000` @ 0.22 | `#FFFFFF` @ 0.249 |
| `GrayA9` | `#000000` @ 0.439 | `#FFFFFF` @ 0.386 |
| `Indigo1` | `#FFFFFF` | `#141421` |
| `Indigo10` | `#393ECC` | `#5458E8` |
| `Indigo11` | `#3438B2` | `#8589FF` |
| `Indigo12` | `#101245` | `#EDEEFC` |
| `Indigo2` | `#F7F8FF` | `#16162E` |
| `Indigo3` | `#F0F0FF` | `#191A40` |
| `Indigo4` | `#E8E9FF` | `#1C1D4F` |
| `Indigo5` | `#D9DAFC` | `#1F215C` |
| `Indigo6` | `#C8CAFA` | `#22246E` |
| `Indigo7` | `#AEB0F5` | `#272A8A` |
| `Indigo8` | `#8E91F0` | `#2E32B2` |
| `Indigo9` | `#3138F9` | `#3239FA` |
| `InputFieldBackgroundColor` | `#FFFFFF` | `#FFFFFF` @ 0.15 |
| `InputFieldBorderColor` | `#DBDBDB` | `#FFFFFF` @ 0.3 |
| `NeutralButtonBorder` | `#DBDBDB` | `#6362AE` |
| `NeutralButtonFace` | `#FFFFFF` | `#302F63` |
| `NeutralButtonForeground` | `#171717` | `#FFFFFF` @ 0.9 |
| `NeutralButtonHovered` | `#F2F2F2` | `#454473` |
| `NeutralButtonIconBackground` | `#000000` @ 0.1 | `#C7C0D7` @ 0.2 |
| `NeutralButtonIconForeground` | `#727272` | `#D7D7FF` @ 0.77 |
| `NeutralButtonPressed` | `#E5E5E5` | `#2B2A59` |
| `NeutralButtonShadow` | `#E2E2E2` | `#FFFFFF` @ 0 |
| `PopoverArrowIcon` | `#1E2E69` @ 0.3 | `#EEEEF6` @ 0.3 |
| `PopoverBackground` | `#FAFBFF` | `#151C30` |
| `PopoverBorder` | `#FFFFFF` @ 0 | `#D3CEED` @ 0.2 |
| `PopoverIconBackground` | `#10134D` @ 0.1 | `#C3C2FD` @ 0.2 |
| `PopoverIconColor` | `#FAFBFF` | `#F4F6FD` @ 0.95 |
| `PopoverInputText` (P3) | `#0E0F10` @ 0.8 | `#FAFBFF` @ 0.9 |
| `PopoverLogoBackground` | `#FFFFFF` @ 0.9 | `#FFFFFF` @ 0.6 |
| `PopoverLogoShadow` | `#000000` @ 0.15 | `#FFFFFF` @ 0 |
| `PopoverMessage` | `#060E2B` @ 0.75 | `#EEEEF6` @ 0.75 |
| `PopoverTitle` | `#181B1F` | `#FFFFFF` |
| `PrimaryButtonBorder` | `#FFFFFF` @ 0 | `#FFFFFF` @ 0.2 |
| `PrimaryButtonFace` | `#3139FB` | `#3139FB` |
| `PrimaryButtonForeground` | `#FFFFFF` | `#FFFFFF` |
| `PrimaryButtonHovered` | `#2C33E2` | `#2C33E2` |
| `PrimaryButtonIconBackground` | `#FFFFFF` @ 0.1 | `#FFFFFF` @ 0.1 |
| `PrimaryButtonIconBorder` | `#FFFFFF` @ 0.2 | `#FFFFFF` @ 0.2 |
| `PrimaryButtonIconForeground` | `#FFFFFF` @ 0.9 | `#FFFFFF` @ 0.9 |
| `PrimaryButtonPressed` | `#2A30D5` | `#2A30D5` |
| `PrimaryButtonShadow` | `#3438B2` | `#5A61FC` @ 0.5 |
| `SecondaryTextForeground` | `#515151` | `#515151` |

</details>

#### Command bar and URL input (22)

<details><summary><code>ARC_CommandBar</code> (14)</summary>

| Token | Light | Dark |
|---|---|---|
| `CommandBarAccessoryBackgroundColor` | `#000000` @ 0.05 | `#FFFFFF` @ 0.05 |
| `CommandBarAccessoryForegroundColor` | `#000000` @ 0.5 | `#FFFFFF` @ 0.66 |
| `CommandBarBannerBackground` | `#FDFDFE` | `#161616` |
| `CommandBarBannerSecondaryButtonBackground` | `#FFFFFF` | `#232323` |
| `CommandBarBannerSecondaryButtonBorder` | `#DBDBDB` | `#6F6F6F` |
| `CommandBarBannerSecondaryButtonText` | `#171717` | `#FFFFFF` |
| `CommandBarHairlineDividerColor` | `#000000` @ 0.1 | `#FFFFFF` @ 0.1 |
| `CommandBarRowHoverBackgroundColor` | `#000000` @ 0.05 | `#FFFFFF` @ 0.05 |
| `CommandBarSuggestionHintPillText` (P3) | `#228CFF` | `#FAFBFF` @ 0.33 |
| `CommandBarTextPrimaryColor` | `#000000` @ 0.8 | `#FFFFFF` @ 0.8 |
| `CommandBarTextSecondaryColor` | `#000000` @ 0.33 | `#FFFFFF` @ 0.33 |
| `SecondaryWindowInputBackground` (P3) | `#FAFBFF` | `#0E0F10` |
| `SecondaryWindowInputBorder` (P3) | `#0E0F10` @ 0.1 | `#FAFBFF` @ 0.2 |
| `TypeTravelCapsuleBackground` | `#EBEBEB` | `#111B31` |

</details>

<details><summary><code>ARC_URLInputter</code> (4)</summary>

| Token | Light | Dark |
|---|---|---|
| `Background` | `#FFFFFF` | `#120F2E` |
| `FontColor` | `#000000` | `#FFFFFF` |
| `PlaceholderBackground` | `#3D3E40` @ 0.33 | `#3D3E40` @ 0.33 |
| `TextFieldBackground` | `#EBEBEC` | `#3139FB` @ 0.15 |

</details>

<details><summary><code>ARC_LittleBrowser</code> (4)</summary>

| Token | Light | Dark |
|---|---|---|
| `DownloadItemBackground` (P3) | `#FFFFFF` | `#0D0D0D` |
| `DownloadItemBackgroundHovered` (P3) | `#F5F5F5` | `#1F1F1F` |
| `LittleBrowserCommandBarPlaceholderBackground` (P3) | `#0E0F10` @ 0.06 | `#FAFBFF` @ 0.1 |
| `LittleBrowserCommandBarPlaceholderBackgroundHovered` (P3) | `#0E0F10` @ 0.1 | `#FAFBFF` @ 0.15 |

</details>

#### Window chrome, sidebar, menus (38)

<details><summary><code>_App</code> (18)</summary>

| Token | Light | Dark |
|---|---|---|
| `AddSpacePlusBackgroundColor` | `#FFFFFF` | `#000000` |
| `AddSpacePlusIconActivatedTintColor` | `#FFFFFF` | `#000000` |
| `AddSpacePlusIconDeactivatedColor` | `#000000` @ 0.45 | `#FFFFFF` @ 0.45 |
| `AddSpacePlusIconTintColor` (P3) | `#2C00CA` | `#FFFFFF` |
| `AddSpacePlusProgressColor` (P3) | `#2C00CA` | `#FFFFFF` |
| `CommandBarIconActiveBackground` (P3) | `#FFFFFF` | `#1A1A1A` |
| `CommandBarPlaceholderIconLockInsecure` (P3) | `#FF0500` | `#FF5067` |
| `CommandBarPlaceholderIconLockSecure` (P3) | `#000000` | `#FFFFFF` |
| `CommandBarPlaceholderPlaceholderText` | `#000000` @ 0.3 | `#FFFFFF` @ 0.3 |
| `CommandBarPlaceholderText` | `#000000` @ 0.6 | `#FFFFFF` @ 0.6 |
| `DragHint` | `#000000` @ 0.2 | `#FFFFFF` @ 0.2 |
| `DragHintHighlighted` | `#000000` @ 0.5 | `#FFFFFF` @ 0.5 |
| `EaselBackground` | `#FFFFFF` @ 0.85 | `#000000` @ 0.5 |
| `NewTabButtonPulsingTextColor` | `#000000` @ 0.3 | `#000000` @ 0.3 |
| `NotesBackground` | `#FFFFFF` @ 0.85 | `#000000` @ 0.5 |
| `PreviewBackgroundColor` | `#FFFFFF` | `#212222` |
| `SidebarBorderColor` | `#FFFFFF` @ 0.3 | `#FFFFFF` @ 0.3 |
| `TabListOverlapBorder` | `#000000` @ 0.05 | `#FFFFFF` @ 0.05 |

</details>

<details><summary><code>ARC_ArcMenu</code> (8)</summary>

| Token | Light | Dark |
|---|---|---|
| `MenuBackground` | `#FAFBFF` | `#393841` |
| `MenuDisabledText` | `#ABABAB` | `#797881` |
| `MenuHoverBackground` | `#B7D1FF` | `#3970C5` |
| `MenuSeparator` | `#C4C4C4` | `#C4C4C4` |
| `MenuSubtitle` | `#ABABAB` | `#797881` |
| `MenuSubtitleHover` | `#797881` | `#FFFFFF` |
| `MenuText` | `#494949` | `#EBEBEC` |
| `MenuTextHover` | `#151515` | `#FFFFFF` |

</details>

<details><summary><code>ARC_AppTray</code> (9)</summary>

| Token | Light | Dark |
|---|---|---|
| `GCalSubtitleBackgroundSecondary` | `#000000` @ 0.07 | `#FFFFFF` @ 0.07 |
| `GCalSubtitleBackgroundSelected` | `#F6F9FE` @ 0.9 | `#F6F9FE` @ 0.9 |
| `GCalSubtitleTextColorSecondary` | `#212121` | `#DEE3EB` @ 0.7 |
| `GCalSubtitleTextColorSelected` | `#212121` | `#212121` |
| `GithubBadgeBlack` | `#000000` | `#000000` |
| `GMailBadgeRed` | `#EA4335` | `#EA4335` |
| `IconViewBackground` | `#FFFFFF` | `#FFFFFF` @ 0.2 |
| `TwitterBadgeGray` | `#444444` | `#FFFFFF` |
| `WhatsAppBadgeRed` | `#EA4335` | `#EA4335` |

</details>

<details><summary><code>ARC_MediaControlsFeature</code> (1)</summary>

| Token | Light | Dark |
|---|---|---|
| `PlaybackControlForeground` | `#000000` @ 0.5 | `#FFFFFF` @ 0.66 |

</details>

<details><summary><code>ARC_PictureInPicture</code> (2)</summary>

| Token | Light | Dark |
|---|---|---|
| `DocumentPiPHairlineColor` | `#FFFFFF` @ 0.2 | `#FFFFFF` @ 0.2 |
| `DocumentPiPTopBarBackgroundColor` | `#212123` | `#212123` |

</details>

#### Home, Library and Archive (22)

<details><summary><code>ARC_HomeButton</code> (18)</summary>

| Token | Light | Dark |
|---|---|---|
| `Background` | `#000017` @ 0.07 | `#FFFFFF` @ 0.1 |
| `Background2` | `#000017` @ 0.12 | `#FFFFFF` @ 0.15 |
| `Background3` | `#000017` @ 0.2 | `#FFFFFF` @ 0.2 |
| `CoolShadow` | `#000014` | `#000014` |
| `EaselTitleText` | `#101118` @ 0.8 | `#FFFFFF` @ 0.8 |
| `Foreground` | `#000017` | `#FFFFFF` |
| `Foreground2` | `#000017` @ 0.6 | `#FFFFFF` @ 0.6 |
| `Foreground3` | `#000017` @ 0.45 | `#FFFFFF` @ 0.45 |
| `LibraryItemOutline` | `#000000` @ 0.03 | `#FFFFFF` @ 0.08 |
| `NoteContentText` | `#000000` @ 0.3 | `#FFFFFF` @ 0.3 |
| `NoteTitleText` | `#1C177A` @ 0.8 | `#FFFFFF` |
| `PreviewToolbarBackground` | `#F8F8F8` @ 0.66 | `#000000` @ 0.66 |
| `PreviewToolbarButtonBackground` | `#596069` @ 0.7 | `#FFFFFF` @ 0.5 |
| `WelcomeGradientBlue` (P3) | `#0048FF` | `#0048FF` |
| `WelcomeGradientPink` (P3) | `#FF9396` | `#FF9396` |
| `WelcomeScreenButtonText` | `#FFFFFF` | `#FFFFFF` |
| `WelcomeScreenCardBackground` | `#FFFFFF` | `#131418` |
| `WelcomeScreenText` | `#704067` | `#E1CEDE` |

</details>

<details><summary><code>ARC_BaseHomeComponents</code> (4)</summary>

| Token | Light | Dark |
|---|---|---|
| `Background` | `#000017` @ 0.07 | `#FFFFFF` @ 0.1 |
| `Background2` | `#000017` @ 0.12 | `#FFFFFF` @ 0.15 |
| `CoolShadow` | `#000014` | `#000014` |
| `Foreground2` | `#000017` @ 0.6 | `#FFFFFF` @ 0.6 |

</details>

#### Auth, onboarding and import (44)

<details><summary><code>ARC_AuthFeature</code> (27)</summary>

| Token | Light | Dark |
|---|---|---|
| `Accent` | `#3139FB` | `#3139FB` |
| `ArcMaxDarkModeBackground` | `#9091AD` | `#9091AD` |
| `AuthPrimaryText` | `#000000` @ 0.733 | `#FFFFFF` @ 0.8 |
| `AuthSecondaryText` | `#000000` @ 0.5 | `#FFFFFF` @ 0.61 |
| `BackButton` | `#C4C4C4` | `#FFFFFF` |
| `ButtonBackground` | `#3139FB` | `#3139FB` |
| `ButtonText` | `#FFFFFF` | `#FFFFFF` |
| `CardBackground` | `#E6E7FF` | `#8C8DAB` |
| `CardInnerBorder` | `#FFFFFF` @ 0 | `#FFFFFF` @ 0.2 |
| `CardOuterBorder` | `#000000` @ 0 | `#000000` @ 0.61 |
| `Error` | `#F25E6B` | `#F25E6B` |
| `FooterText` | `#FFFADD` | `#FFFADD` |
| `Legacy/Accent` | `#3039FA` | `#3039FA` |
| `Legacy/Error` (P3) | `#FF3A30` | `#FF3A30` |
| `Legacy/FooterText` | `#000000` @ 0.66 | `#000000` @ 0.66 |
| `Logo` | `#3139FB` | `#6CBAD9` |
| `MessagingText` | `#767676` | `#FFFFFF` |
| `RecoveryCardBackdrop` | `#F4F4F4` | `#F4F4F4` |
| `RecoveryCardLeftContentBackground 1` | `#202020` | `#202020` |
| `SplitViewLeftBackground` | `#FFFFFF` | `#1E1E1E` |
| `TextFieldBackground` | `#FFFFFF` @ 0 | `#FFFFFF` @ 0.05 |
| `TextFieldBorder` | `#000000` @ 0.2 | `#000000` @ 0.3 |
| `TextFieldFocusedBorder` | `#3139FB` | `#3139FB` |
| `TextFieldPlaceholder` | `#000000` @ 0.5 | `#FFFFFF` @ 0.5 |
| `TextFieldText` | `#000000` | `#FFFFFF` |
| `Title` | `#000000` | `#FFFFFF` |
| `WindowBackground` | `#3139FB` | `#3139FB` |

</details>

<details><summary><code>ARC_ImportFeature</code> (13)</summary>

| Token | Light | Dark |
|---|---|---|
| `AuthFlowDropTargetBackground` | `#E0E1FF` | `#191B4C` |
| `AuthFlowDropTargetBackgroundCompleted` | `#C5E5C0` | `#C5E5C0` |
| `AuthFlowDropTargetBorder` | `#2C33E1` | `#3239FB` |
| `AuthFlowDropTargetError` | `#C93333` | `#C93333` |
| `AuthFlowDropTargetForeground` (P3) | `#2C33E2` | `#FFFFFF` |
| `AuthFlowDropTargetForegroundCompleted` | `#3EA82E` | `#3EA82E` |
| `AuthFlowDropTargetKeyForeground` | `#2C33E2` | `#8488FF` |
| `AuthFlowFolderBackgroundFill` | `#C0C1F4` | `#C0C1F4` |
| `AuthFlowFolderForegroundFill` | `#F0F0EF` | `#F0F0EF` |
| `AuthFlowFolderStrokeColor` | `#3138FC` | `#3138FC` |
| `AuthFlowKeychainHelpText` | `#848484` | `#848484` |
| `AuthFlowKeychainMessagingText` (P3) | `#000000` @ 0.847 | `#FFFFFF` |
| `BrowserSelectionShadowIndicator` | `#FFFFFF` | `#000000` @ 0 |

</details>

<details><summary><code>ARC_SidebarSyncCloudKit</code> (3)</summary>

| Token | Light | Dark |
|---|---|---|
| `FAQTextColor` | `#FFFFFF` | `#E1E1E1` |
| `RecoveryCardBackgroundColor` | `#202020` | `#202020` |
| `RecoveryPhraseTextColor` | `#D3D3D3` | `#D3D3D3` |

</details>

<details><summary><code>ARC_DeleteAccountFeature</code> (1)</summary>

| Token | Light | Dark |
|---|---|---|
| `ErrorMessageForegroundColor` | `#C93333` | `#FF5A5F` |

</details>

#### Notes, Easels and Capture (49)

<details><summary><code>ARC_ArcRichTextEditor</code> (14)</summary>

| Token | Light | Dark |
|---|---|---|
| `BodyText` | `#000000` | `#FFFFFF` |
| `Cursor` | `#2702C2` | `#9380E0` |
| `FormatMenuBackground` | `#FFFFFF` | `#120F2E` |
| `FormatMenuBorder` | `#CDCCDF` | `#34334D` |
| `FormatMenuIcon` | `#6E678D` | `#6E678D` |
| `FormatMenuText` | `#6E678D` | `#8795C1` |
| `HeaderText` | `#6E678D` | `#CDCDFF` |
| `HoveredMenuItemBackground` | `#EBEBEC` | `#FFFFFF` @ 0.15 |
| `Link` | `#220C7F` | `#E6E6FF` |
| `ListMarker` | `#6E678D` | `#CDCDFF` |
| `PlaceholderBodyText` | `#000000` @ 0.4 | `#FFFFFF` @ 0.4 |
| `SelectedMenuItem` | `#2702C2` | `#B6C9FA` |
| `SelectedMenuItemBackground` | `#2702C2` @ 0.1 | `#062E79` |
| `SelectionTextBackground` | `#CDCDFF` | `#5235CE` |

</details>

<details><summary><code>ARC_TextEditor</code> (3)</summary>

| Token | Light | Dark |
|---|---|---|
| `GutterMenuItemSelected` | `#D9D9E0` | `#FFFFFF` @ 0.3 |
| `TitlePlaceholderText` | `#220C7F` @ 0.4 | `#E6E6FF` @ 0.4 |
| `TitleText` | `#220C7F` | `#E6E6FF` |

</details>

<details><summary><code>ARC_EaselUI</code> (18)</summary>

| Token | Light | Dark |
|---|---|---|
| `AvatarIcon` (P3) | `#5F5880` @ 0.3 | `#85878F` |
| `CaptureButtonHovered` | `#F0F1F3` | `#373C4B` |
| `CaptureButtonNormal` | `#FFFFFF` | `#252832` |
| `CaptureButtonPressed` | `#E3E6E7` | `#495064` |
| `CaptureLinkIconBackground` | `#090909` @ 0.07 | `#F6F6F6` @ 0.11 |
| `CommentBackground` | `#F0EFF4` | `#F0EFF4` |
| `EaselLightText` | `#2702C2` @ 0.25 | `#2702C2` @ 0.25 |
| `EaselSelectionColor` | `#6CBAD9` | `#6CBAD9` |
| `EaselUnreadCommentText` | `#2702C2` | `#2702C2` |
| `ErrorBorder` (P3) | `#E32509` | `#DD847E` |
| `FloatingElementBackground` | `#FFFFFF` | `#000000` |
| `HighlightedTextColor` | `#FFFFFF` | `#FFFFFF` |
| `ImageViewFillerBackground` (P3) | `#000000` @ 0.1 | `#676A6B` |
| `LoadingStateForeground` | `#5F5880` | `#FFFFFF` |
| `ModalBackground` | `#FFFFFF` | `#120F2E` |
| `ModalOutline` | `#120F2E` @ 0.03 | `#FCFFFF` @ 0.1 |
| `TextColor` | `#000000` | `#FFFFFF` |
| `ToolbarIcon` (P3) | `#5F5880` | `#85878F` |

</details>

<details><summary><code>ARC_Capture</code> (14)</summary>

| Token | Light | Dark |
|---|---|---|
| `Background` | `#FFFFFF` | `#120F2E` |
| `BlurredBackground` | `#FFFFFF` @ 0.33 | `#000000` @ 0.25 |
| `ButtonText` | `#000000` @ 0.3 | `#FFFFFF` |
| `HoveredAndKeyboardSelectedBackground` (P3) | `#282EC9` | `#282EC9` |
| `HoveredCellBackground` | `#111455` @ 0.1 | `#3A3868` |
| `ImageViewBackground` | `#FFFFFF` | `#151C30` |
| `OverlayBubbleBlue` (P3) | `#0048FF` @ 0.5 | `#0048FF` @ 0.5 |
| `OverlayBubblePink` (P3) | `#FF9396` @ 0.5 | `#FF9396` @ 0.5 |
| `OverlayBubbleText` (P3) | `#3A019A` | `#3A019A` |
| `SeeMoreEaselTextColor` | `#000000` @ 0.45 | `#FFFFFF` @ 0.45 |
| `TextColor` | `#000000` | `#FFFFFF` @ 0.9 |
| `TextColorForSelectedCells` | `#FFFFFF` @ 0.95 | `#FFFFFF` |
| `TextFieldBackground` | `#000000` @ 0.07 | `#FFFFFF` @ 0.07 |
| `ToggleCellTextColor` (P3) | `#2F39FF` | `#D6D7FE` |

</details>

#### Ask Arc (AI) (29)

<details><summary><code>ARC_AskArc</code> (29)</summary>

| Token | Light | Dark |
|---|---|---|
| `AccentColor` (P3) | `#2F39FF` | `#4487FF` |
| `BackgroundColor` | `#FFFFFF` | `#000000` |
| `BackgroundGradientBottomColor` | `#97A6CC` @ 0.2 | `#97A6CC` @ 0.2 |
| `BackgroundGradientTopColor` | `#EED1D1` @ 0.2 | `#EED1D1` @ 0.2 |
| `CloseButtonBackground` | `#767680` @ 0.12 | `#767680` @ 0.12 |
| `ContainerBackground` (P3) | `#000000` @ 0.06 | `#000000` @ 0.06 |
| `DarkAccentColor` (P3) | `#2802B1` | `#4487FF` |
| `FollowUpBottomQuestionBackground` | `#FFFFFF` | `#000000` |
| `FollowUpButtonBackground` | `#E1E1FB` | `#000000` |
| `FooterSectionBackgroundColor` | `#97A6CC` @ 0.2 | `#000000` |
| `ForegroundColor` | `#000000` | `#FFFFFF` |
| `LoadingBackgroundColor` (P3) | `#3700D2` | `#3700D2` |
| `OneBoxBackground` | `#E1E1FB` | `#272727` |
| `PageBackgroundColor` | `#F1F0F5` | `#1F2128` |
| `PrimaryText` (P3) | `#000000` | `#FFFFFF` |
| `QuoteBackgroundColor` | `#F8F8FA` | `#0A0A14` |
| `SearchEngineLinkBackground` | `#F7F7F7` | `#0A0A0F` |
| `SearchEngineLinkStroke` | `#EDEDED` | `#30303B` |
| `SecondaryColor` | `#F0F0F0` | `#FFFFFF` @ 0.941 |
| `SecondarySurfaceColor` | `#F0F0F0` | `#FFFFFF` @ 0.08 |
| `SecondaryText` (P3) | `#000000` @ 0.7 | `#FFFFFF` @ 0.7 |
| `ShareCardColor` | `#FFFFFF` | `#000000` |
| `ShareCardSubtitleColor` | `#3D3D42` @ 0.6 | `#FFFFFF` @ 0.6 |
| `ShareCardTitleColor` | `#000000` | `#FFFFFF` |
| `ShareIconColor` | `#3D3D42` @ 0.6 | `#EBEBF5` @ 0.6 |
| `ShareTextColor` | `#000000` @ 0.5 | `#FFFFFF` @ 0.5 |
| `ShareTitleColor` | `#290A9E` | `#FFFFFF` |
| `SourcesTogglePressedColor` | `#5E5FEA` @ 0.1 | `#272727` |
| `ToastColor` | `#0F17E8` | `#0F17E8` |

</details>

#### Boosts (22)

<details><summary><code>ARC_BoostsEditor</code> (22)</summary>

| Token | Light | Dark |
|---|---|---|
| `BoostsBlue` | `#300EFF` | `#300EFF` |
| `BoostsGreen` (P3) | `#07BC31` | `#07BC31` |
| `BoostsLabel` | `#FFFFFF` | `#000000` @ 0.8 |
| `BoostsMagenta` | `#DD0EFF` | `#DD0EFF` |
| `BoostsOrange` | `#FF560E` | `#FF560E` |
| `BoostsPink` | `#FF0E82` | `#FF0E82` |
| `BoostsPurple` | `#860EFF` | `#860EFF` |
| `BoostsRed` | `#FF0E0E` | `#FF0E0E` |
| `BoostsYellow` (P3) | `#FF9D0D` | `#FF9D0D` |
| `DarkModeBackground` | `#3B3B3C` | `#3B3B3C` |
| `DarkModeForeground` | `#FBFBFF` | `#FBFBFF` |
| `DisabledToolButtonForeground` | `#F3F1FD` @ 0.3 | `#F3F1FD` @ 0.3 |
| `GrayButtonForeground` | `#3A3A3B` | `#3A3A3B` |
| `InterstitialFooter` | `#CEDBFC` | `#CEDBFC` |
| `InterstitialForeground` | `#2E2740` | `#2E2740` |
| `PuckBackground` | `#FAFBFF` | `#FAFBFF` |
| `SegmentedControlBackground` | `#000000` @ 0.07 | `#FFFFFF` @ 0.1 |
| `SegmentedControlSelectionBackdrop` | `#FFFFFF` | `#FFFFFF` @ 0.3 |
| `SliderBackground` | `#3B3746` @ 0.05 | `#3B3746` @ 0.05 |
| `SliderTint` | `#017AFF` | `#017AFF` |
| `WarningBackground` | `#FF5A5F` | `#FF5A5F` |
| `ZapPreviewBackground` | `#D9D9D9` | `#D9D9D9` |

</details>

#### Settings, profiles and misc (34)

<details><summary><code>ARC_PreferencesFeature</code> (25)</summary>

| Token | Light | Dark |
|---|---|---|
| `EmailChangePendingVerificationBackground` | `#FFFFFF` | `#36363A` |
| `EmailChangePendingVerificationOutline` | `#000000` @ 0.3 | `#FFFFFF` |
| `EmailChangePendingVerificationTextForeground` | `#3D3D3D` | `#FFFFFF` |
| `EnableSyncDialogDescriptionTextColor` | `#060E2B` @ 0.75 | `#EEEEF6` @ 0.75 |
| `EnableSyncDialogTitleTextColor` | `#181B1F` | `#FFFFFF` |
| `ErrorMessageBackgroundColor` | `#C93333` @ 0.1 | `#C93333` @ 0.33 |
| `ErrorMessageBorderColor` | `#FFFFFF` @ 0 | `#FFCECE` @ 0.2 |
| `ErrorMessageForegroundColor` | `#C93333` | `#FF5A5F` |
| `FirebaseSidebarSyncBorderColor` | `#6F6F6F` | `#6F6F6F` |
| `FirebaseSyncDialogIconBackgroundColor` | `#10134D` | `#10134D` |
| `FirebaseSyncSecondaryTextColor` | `#8A8A8A` | `#9F9EA0` |
| `InfoMessageBackgroundColor` | `#3EA82E` @ 0.1 | `#000000` @ 0.4 |
| `MakeDefaultViewBackgroundColor` | `#FFFFFF` | `#656068` |
| `MaxBannerColor` | `#484FFF` | `#484FFF` |
| `MemberCardActionButtonColor` | `#6F6F6F` | `#6F6F6F` |
| `PanelFontColor` | `#3D3D3D` | `#FFFFFF` |
| `PreferencesButtonBackgroundColor` | `#000000` @ 0.15 | `#E0DFE0` @ 0.07 |
| `PreferencesButtonForegroundColor` | `#5F5F5F` | `#E0DFE0` |
| `PreferencesIconButtonBackgroundColor` | `#DBDFE5` | `#515671` |
| `PreferencesLinkBackgroundColor` | `#C2D9FF` | `#C2D9FF` @ 0.25 |
| `PreferencesLinkColor` | `#458AFF` | `#458AFF` |
| `PreferencesLoadableButtonBackgroundColor` | `#FFFFFF` | `#FFFFFF` @ 0.15 |
| `PreferencesSectionHighlightBackgroundColor` | `#F5E8C7` | `#FFFFFF` @ 0.077 |
| `PreferencesSectionHighlightTextColor` | `#7D5E0F` | `#FFFFFF` |
| `PreferencesSectionPrimaryForegroundColor` | `#000000` @ 0.66 | `#F3F3F3` |

</details>

<details><summary><code>ARC_ProfilesUI</code> (2)</summary>

| Token | Light | Dark |
|---|---|---|
| `ProfilePicker` | `#3139FB` @ 0.1 | `#3139FB` @ 0.898 |
| `ProfilePickerText` | `#060E2B` | `#E3E2EE` |

</details>

<details><summary><code>ARC_AdBlocking</code> (4)</summary>

| Token | Light | Dark |
|---|---|---|
| `CheckboxColor` | `#3139FB` | `#B0B3FF` |
| `ComponentBackgroundColor` | `#FFFFFF` | `#302F63` |
| `ComponentBorderColor` | `#E5E5E5` | `#6362AE` |
| `ProfileIndicatorBackgroundColor` | `#181B1F` @ 0.07 | `#FFFFFF` @ 0.12 |

</details>

<details><summary><code>ARC_SoftwareUpdaterClient</code> (1)</summary>

| Token | Light | Dark |
|---|---|---|
| `UpdaterButtonBackgroundColor` | `#FFFFFF` | `#000000` |

</details>

<details><summary><code>ARC_Translation</code> (1)</summary>

| Token | Light | Dark |
|---|---|---|
| `Background` (P3) | `#FFFFFF` | `#1A1A1A` |

</details>

<details><summary><code>ARC_CustomInfoPicker</code> (1)</summary>

| Token | Light | Dark |
|---|---|---|
| `CustomizationBackground` (P3) | `#85888E` @ 0.25 | `#FFFFFF` @ 0.25 |

</details>

#### Referrals (11)

<details><summary><code>ARC_ReferralCodeFeature</code> (11)</summary>

| Token | Light | Dark |
|---|---|---|
| `ReferralDaysLeftTextColor` | `#196442` | `#23B573` |
| `ReferralDialogBackgroundColor` | `#FFFFFF` | `#151C30` |
| `ReferralDialogHeaderColor` | `#3139FB` | `#FFFFFF` |
| `ReferralDialogParagraphColor` | `#171717` | `#FCFCFC` |
| `ReferralToastBackgroundColor` | `#F1FCF7` | `#234435` |
| `ReferralToastTextColor` | `#16A563` | `#75E2B0` |
| `TicketBackgroundColor` | `#75E2B0` @ 0.1 | `#75E2B0` @ 0.1 |
| `TicketBottomStubBackgroundColor` | `#75E2B0` | `#75E2B0` |
| `TicketIconColor` | `#24B573` | `#23B573` |
| `TicketStrokeColor` | `#46C88D` | `#46C78D` |
| `TicketTextColor` | `#196442` | `#196442` |

</details>

#### Space style editor (27)

`ARC_SpaceStyleEditor` ships its own copy of the 27 `ColorPickerDrab*`, `ColorPickerGreyscale*` and `ColorPickerPastel*` swatches, identical to the ones in BaseAssets (listed above).


---

## 2. Space theming

Every Space in Arc has its own color theme that tints the sidebar, the window frame, toasts and tooltips. The model is `BaseModels.WindowTheme`, edited by the `SpaceStyleEditor` module and drawn by `WindowThemeUI` on the GPU.

### The model

Reconstructed from the Swift type metadata (field names and enum cases are exact; comments are interpretation):

```swift
struct WindowTheme {
  var background:           AppearanceBased<Background>
  var windowAppearance:     AppearanceBased<Appearance>?      // .light | .dark
  var primaryColorPalette:  PrimaryColorPalette
  var semanticColorPalette: AppearanceBased<SemanticColorPalette>
}

enum AppearanceBased<T> {           // BaseModels.AppearanceBasedConfiguration
  case single(T)
  case appearanceBased(light: T, dark: T)
}

struct Background {
  var style: Style                   // .color(ColorType)
  var contentOverBackgroundAppearance: Appearance?
  var isVibrant: Bool
}

enum ColorType {
  case basicColor(color, translucencyStyle?)                    // one flat color
  case blendedSingleColor(color, translucencyStyle?, modifiers) // one color, textured
  case blendedGradient(baseColors: [StorableColor],
                       overlayColors: [StorableColor],
                       translucencyStyle?, modifiers,
                       wheel: .complimentary | .analogous)
}

struct BlendedBackgroundModifiers {
  var noiseFactor: CGFloat           // strength of the texture overlay
  var intensityFactor: CGFloat       // how saturated / strong the color is
  var overlay: Overlay               // .grain | .sand | .denim | .tweed
}

enum TranslucencyStyle { case light, dark, auto }   // window vibrancy behind the color

struct PrimaryColorPalette {         // four tones of the key color
  var tintedLight, midTone, shaded, shadedDark: StorableColor
}

final class SemanticColorPalette {   // 12 roles, one set for light and one for dark
  let foregroundPrimary, foregroundSecondary, foregroundTertiary
  let maxContrastColor, minContrastColor
  let backgroundExtra, background
  let focus, hover, cutoutColor
  let title, subtitle
}

struct StorableColor { colorSpace: .extendedSRGB; red, green, blue, alpha: CGFloat }
```

### How a theme comes together

1. **Key color(s).** The user picks one or more colors on the color pad. With one color the background is `blendedSingleColor`; with more it is `blendedGradient`, where extra colors are placed on the hue wheel either as **complimentary** or **analogous** partners (`SpaceStyleEditorColorSet { keyColor, numberOfComplimentaryColors, wheel }`).
2. **Primary palette.** From the key color Arc derives four tones: `tintedLight` (lifted toward white, for light-mode surfaces), `midTone` (the color itself), `shaded` and `shadedDark` (pushed toward black, for dark mode). The derivation lives in `BaseModels.WindowThemeUtils` (its only error case is `failedToGeneratePalette`). `ARCUI` ships the color math it builds on: `OKLab`, `SRGB`, `HSBA`, `HSLA`, `RGBA`, `BrightnessPalette { sourceColor, colors }` and `BrightnessProfile.TextColors { light, dark }`. The exact formulas are compiled code and not recoverable from metadata, but the OKLab type suggests perceptual lightness steps.
3. **Semantic palette.** Twelve roles per appearance, consumed through SwiftUI environment values (`_colorPalette`) by the sidebar, toasts, tooltips, the command bar and more:

   | Role | Purpose (from usage) |
   |---|---|
   | `foregroundPrimary` / `Secondary` / `Tertiary` | Text and icon emphasis levels on top of the Space color |
   | `maxContrastColor` / `minContrastColor` | The most / least contrasting color against the background (for example white vs. black) |
   | `background` / `backgroundExtra` | Base fill and an extra-emphasis fill (selected rows, wells) |
   | `focus` / `hover` | Focus and hover state tints |
   | `cutoutColor` | Color of the cut-out around the web content area |
   | `title` / `subtitle` | Text colors for titles and subtitles in themed popovers and toasts |

4. **Texture.** `noiseFactor` and `overlay` choose and blend one of four tiled textures: `grain`, `sand`, `denim`, `tweed`. Each texture has a regular and a `_metal` variant in `WindowThemeUI` (the latter used by the Metal path), plus a matching dial knob image in `SpaceStyleEditor` (`GrainKnob`, `SandKnob`, `DenimKnob`, `TweedKnob`).
5. **Intensity.** `intensityFactor` scales how strong the color is against the window's vibrancy.
6. **Appearance.** Light, dark or automatic per Space. `DarkModeBiasSetting` is either `.value(CGFloat)` (a bias) or `.forceAppearance(.light | .dark)`.

### Rendering

`WindowThemeUI.WindowThemeBackgroundViewMetal` renders the background with a `CAMetalLayer` and one renderer per GPU (`renderers: [UInt64: WindowThemeBackgroundMetalRenderer]`). The shader library (`WindowThemeUI/default.metallib`) has three passes:

| Pass | Functions | Inputs (argument names) |
|---|---|---|
| Gradient | `gradientVertex`, `gradientFragment` | `Gradient`, `GradientLayer`, `GradientRenderConfiguration`: `colors`, `colorCount`, `gradients`, `gradientCount`, `layers`, `layerCount`, `baseStartEnd`, `baseUV` |
| Overlay | `overlayVertex`, `overlayFragment` | `OverlayRenderConfiguration`: `overlayTexture`, `overlayRepetitions`, `overlayStartEnd`, `overlayUV`, `fromOverlay`, `toOverlay`, `fromOverlayAlpha`, `toOverlayAlpha`, `underlayColor`, `progress` |
| Output | `renderVertex`, `renderFragment` | `OutputRenderConfiguration`: `gradientTexture`, `cutoutCoordinates`, `alpha`, `config` |

The `from` / `to` / `progress` arguments implement Space switching: `WindowThemeBackgroundConfiguration` is `.single(background)` or `.transitioning(from:to:progress:shouldCrossfade:)`, so swiping between Spaces crossfades both the gradient and the texture. `cutoutCoordinates` punch out the web content rectangle. When Metal is unavailable (`noAvailableDevices`, `unsupportedDueToExternalGPU`) a SwiftUI fallback (`WindowThemeBackgroundStyleView`) draws a `Rectangle` filled with the color, or a `LinearGradient` plus the texture image with a blend mode inside a `drawingGroup`.

### The Space style editor

`SpaceStyleEditor` is a Composable Architecture feature presented either during Space setup or from the sidebar (`Presentation.setup | .sidebar`).

| Part | Type | What it does |
|---|---|---|
| Color pad | `SpaceStyleColorPadView`, `PadWheel` | 2D pad with draggable color knobs (`Knob { id, color, position, isSelected }`). Position maps to hue and lightness; `saturation` and `lightnessRange` bound the pad. Add / remove color buttons (`EditColorButtonsView`) and `didDeleteAllColors`. |
| Presets | `SpaceStyleColorPickerView`, `ColorPillButtonStyle` | Paged rows of preset color sets; a pill can add complimentary colors. |
| Texture dial | `SpaceStyleDialView` | A rotary dial for `noiseFactor`. Five input styles are tracked: `slider`, `rotation`, `dialClick`, `scrollWheel`, `drag`. Clicking the center knob (`didTapNoiseKnob`) cycles the overlay texture. |
| Intensity slider | `SineSlider`, `SineWave { strength, frequency, phase }` | In "advanced options": a slider drawn as a sine wave whose amplitude grows with the value. |
| Light / dark / auto | `LightDarkToggleView`, `LoopingToggleView` | Three buttons with looping Lottie icons `sun`, `moon` and `automatic`. |
| Undo | `undoStack: CappedStack<State>` | Each gesture registers an undo step. Escape key is handled. |

Preset swatches (also in `design-tokens.json` under `spaceTheme.pickerPresetGroups`):

| Row | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| Brand | `#F2EAE4` | `#F29BBB` | `#A6729D` | `#F25E6B` | `#FF8558` | `#F8D558` | `#34E895` | `#6CBAD9` | `#666789` |
| Pastel | `#FEFBFA` | `#FFE9F3` | `#F1D1EC` | `#FFCBD1` | `#FFE0D3` | `#FFF9E5` | `#DEFDEB` | `#DCF3FC` | `#C5C6E5` |
| Drab | `#4E3A5A` | `#693558` | `#8F4042` | `#B16D40` | `#D7B35D` | `#CDCCA4` | `#7AA982` | `#226149` | `#26456B` |
| Greyscale | `#FFFFFF` | `#E6E6E6` | `#CCCCCC` | `#B2B2B2` | `#808080` | `#666666` | `#333333` | `#1A1A1A` | `#000000` |

### Theme-aware views and derived palettes

- `BaseModels.ThemeAwareView` / `ThemeAwareHostingView` inject the Space's semantic palette into any SwiftUI view.
- `ArcTooltip.TooltipColorPalette` (`titleColor`, `keyForegroundColor`, `keyBackgroundColor`, `backgroundColor`, `keyTitleColor`, each light/dark) is derived from the theme, so tooltips match the Space.
- `Toasts.ToastColorPalette` (`foreground`, `background`, `accessoryForeground`, `accessoryBackground`, `particles: [NSColor]`) and `ShinyToastBackgroundBasedPalette` come from the semantic and background palettes. Toast particles can be `standard` or a custom list of semantic-palette key paths.
- A developer dashboard (`ColorPaletteDashboard`) shows the live semantic palette.

### Space and tab icons

`BaseModels.SidebarCustomIcon` is `emoji(Character)`, `icon(SidebarIconType)` or `symbol(String)` (an SF Symbol name). `SidebarIconType` has 61 cases (`star`, `bookmark`, `heart`, `flag`, `flash`, `bulb`, `planet`, `leaf`, `paw`, `pizza`, `skull`, `github`, `linear`, `figma`, ...), drawn from the bundled Ionicons font. The `CustomInfoPicker` shows them in a grid (icon sets `folderPicker` and `tabAndSpacePicker`) next to an emoji page backed by a bundled 1,870-entry emoji list with categories, aliases, tags and a skin tone picker.

---

## 3. Typography

### UI font

The browser chrome uses the system font (SF Pro). Text roles in `ARCUI` are `header`, `subtitle`, `largeLabel`, `smallLabel`, `microLabel`; there is also a `KerningModifier` and `ArcButtonStyle.CustomFontInfo { size, weight }`. Sizes and weights are compiled into code.

`FontsManager` contains a feature-flagged experiment for swapping the chrome font: `FontsOptions` = `system`, `national`, `sohne`, `chalkboard`, `inconsolata`, conforming to the feature flag protocols so it can be set remotely. A `FontSet` assigns a font to 12 roles: `label`, `subLabel`, `listHeader`, `sectionHeader`, `boldSectionHeader`, `sectionEntry`, `sectionHeaderButton`, `title`, `smallCaps`, `searchHeader`, `chatStatusText`, `chatTimestamp`. National 2 and Söhne ship as Klim's **"Test"** (trial) cuts, which fits an internal experiment rather than a released option.

### Bundled font files

All in the `ARCClients_FontsManager` bundle (83 files). Each family has a generated `FontsManager.FontFamily.<Name>` accessor (`FontConvertible { name, family, path }`).

| Family | Files (style, OS/2 weight) | Foundry / license |
|---|---|---|
| ABC Favorit | Regular 400, Regular Italic 400, Bold 700 | Dinamo |
| ABC Favorit Lining | Medium 500, Bold 700 | Dinamo |
| ABC Favorit Mono | Regular, Regular Italic 400; Medium, Medium Italic 500; Bold, Bold Italic 700 | Dinamo |
| ABC Oracle | Book 350 | Dinamo |
| EB Garamond | Regular (variable `wght`), Italic (variable `wght`) | OFL |
| GT Ultra VF | one variable file; named instances run Thin to Black in Fine, Median and regular cuts, with italics | Grilli Type (Noël Leu) |
| GT Ultra Ultra VF | one variable file (instances Fine, Median, Ultra) | Grilli Type |
| Inconsolata | Light 300, Regular 400, Medium 500, Bold 700 | OFL |
| Inter | Regular 400, Medium 500, SemiBold 600, Bold 700 | OFL |
| Marlin Soft | Medium 500, Extra Black 950 (file `MarlinBold.otf`) | Fontmesa |
| Marlin Soft SQ | Regular 400, Medium 500, Bold 700, Bold Italic, Extra Bold 800, Extra Bold Italic, Black 900 | Fontmesa |
| National 2 Test | Light 350, Regular 400, Bold 700 | Klim (trial) |
| Nunito | ExtraLight 200 to Black 900, every weight with italic (14 files) | OFL |
| Pitch | Light, Regular, Medium, Semibold, Bold, each with italic (10 files) | Klim |
| Pitch Sans | Light, Regular, Medium, Semibold, Bold, each with italic (10 files) | Klim |
| Söhne Breit | Buch, Dreiviertelfett, Extrafett, each with Kursiv (6 files) | Klim |
| Söhne Test | Leicht 300, Buch 400, Halbfett 600 | Klim (trial) |
| Space Mono | Regular, Italic, Bold, Bold Italic | OFL |

Two icon fonts live in `ARCClients_Icons`: `icomoon.ttf` (286 glyphs, the Feather set, `Icons.FeatherIcon`) and `ionicons.ttf` (1,181 glyphs, `Icons.Ionicon`). `Icons.IconFontType` is `feather | ionicons | emoji | mobileEmoji`, rendered to images through an `IconFontImageCache`.

### Which UI uses which font

- **Directly referenced in code:** `GTUltraVF-Black`, `GTUltraVF-Bold`, `GTUltraVF-Light`, `Inter-Bold`, `Nunito-Bold`. These are display faces, so they most likely serve expressive surfaces (onboarding, membership card, banners) rather than the chrome.
- **Easels** use four families, one per text style (`EaselClient.EaselFontFamily`), each with five paragraph sizes (`EaselParagraphStyle`). The Easel export viewer, which says it mirrors `EaselTextView.swift`, gives these values (Easel points, document = 1,000 points wide):

  | Family | Font | Line height | ultra | h0 | h1 | h2 | body |
  |---|---|---:|---|---|---|---|---|
  | `mono` | Space Mono | 1.48 | 80 bold | 60 bold | 44 bold | 24 bold | 15 |
  | `fancy` | EB Garamond | 1.32 | 80 | 60 | 48 | 28 | 16 |
  | `hip` | Inter | 1.28 | 80 / 900 | 60 / 900 | 44 / 900 | 21 bold | 18 |
  | `clean` | System (SF Pro) | 1.2 | 80 / 800 | 60 / 800 | 44 / 800 | 24 bold | 15 |

  Text boxes also have a fill style (`none`, `contentHugging`). The Easel toolbar shows matching `FontStyleFancy/Hip/Mono/System` and `FontSizeH1/H2/Body` icons.
- **Boosts** let users restyle a site with `BoostFontOption` = `system | custom(String)` and `BoostTextZoomOption` = `small, normal, medium, large, larger`.
- **Notes** (`ArcRichTextEditor`) have `TextEditorFontConstants` and `TextEditorParagraphConstants`, compiled into code.
- The remaining families (Favorit, Oracle, Pitch, Pitch Sans, Marlin Soft, Söhne Breit) are registered through `FontsManager` but no direct call site is visible in the strings, so their exact surfaces are not attributable from the binary alone.

---

## 4. Iconography

### Inventory

414 named image assets across 36 bundles (excluding the asset catalog's internal packed atlases). 118 are **template** images (single-color masks tinted at runtime), 252 are vector-backed (PDF or preserved vector data), and 46 have a separate dark-appearance rendition. Exported, that is 874 PNG renditions (1x and 2x) and 41 PDFs.

| Bundle | Assets | Template | Vector (PDF) | Dark variant | Names |
|---|---:|---:|---:|---:|---|
| `ARCClients_BaseAssets` | 130 | 21 | 79 | 9 | `AmplitudeIcon`, `AppIconCanary`, `AppIconCanaryPreview`, `AppIconCandy`, `AppIconCandyPreview`, `AppIconColorful`, `AppIconColorfulPreview`, `AppIconDev`, `AppIconDevPreview`, `AppIconEarlyBirds`, `AppIconEarlyBirdsPreview`, `AppIconFlutedGlass`, `AppIconFlutedGlassPreview`, `AppIconHologram`, `AppIconHologramPreview`, `AppIconNeon`, `AppIconNeonPreview`, `AppIconOriginal`, ... |
| `ARCUI_ARCUI` | 27 | 15 | 16 | 1 | `animatingOrbBlob1`, `animatingOrbBlob2`, `AppIconBorderless`, `AppIconBorderlessSmall`, `AppIconFilled`, `ArcUpdatesArcLogo`, `ArcUpdatesGradient`, `AskOnPagePreview`, `box`, `ChatGPTSiteSearchPreview`, `circle`, `DownloadRenamePreview`, `glow`, `grain-1`, `grain-2`, `grain-3`, `grain-4`, `HoverCardPreview`, ... |
| `ARC_AdBlocking` | 1 | 0 | 0 | 0 | `ArchieDialogIcon` |
| `ARC_ArcRichTextEditor` | 3 | 3 | 3 | 0 | `OrderedList`, `ShareIcon`, `UnorderedList` |
| `ARC_AskArc` | 7 | 1 | 1 | 1 | `AppLogo`, `ArcLogoOutline`, `GradientBackdrop`, `grain`, `LoadingArcLogoBlur`, `OneBoxGradient`, `ShareCardBackground` |
| `ARC_AuthFeature` | 14 | 0 | 2 | 2 | `Brave`, `ChromeLogo`, `ContentIntro1`, `ContentIntro2`, `Edge`, `FirefoxLogo`, `grain`, `LogoWithBackdrop`, `Opera`, `SafariLogo`, `SystemPreferencesMonterey`, `SystemPreferencesVentura`, `Vivaldi`, `WelcomeLogo` |
| `ARC_BoostsDialog` | 5 | 4 | 4 | 0 | `heart-ripple`, `library-icon`, `signature`, `squiggle-mask`, `squiggle-thin` |
| `ARC_BoostsEditor` | 7 | 3 | 6 | 0 | `AnalogousColorScheme`, `ComplementaryColorScheme`, `DotGrid`, `FontSizeIcon`, `HueRing`, `InterstitialIcon`, `SquigglyFooter` |
| `ARC_Capture` | 2 | 0 | 2 | 0 | `camera-cross-cursor`, `camera-cursor` |
| `ARC_CommandBar` | 2 | 2 | 2 | 0 | `LinearIconTemplate`, `OpenAIIconTemplate` |
| `ARC_ContentPanel` | 3 | 3 | 3 | 0 | `ExtensionsIcon`, `window-screenshot-watermark-off`, `window-screenshot-watermark-on` |
| `ARC_ContextMenus` | 17 | 1 | 17 | 15 | `icon-separate-from-split`, `icon-separate-from-split-menu-bottom`, `icon-separate-from-split-opaque`, `icon-split-add-bottom`, `icon-split-add-left`, `icon-split-add-right`, `icon-split-add-top`, `icon-split-close`, `icon-split-horizontal`, `icon-split-move-bottom`, `icon-split-move-left`, `icon-split-move-right`, `icon-split-move-top`, `icon-split-share-horizontal`, `icon-split-share-vertical`, `icon-split-vertical`, `icon-split-x` |
| `ARC_EaselUI` | 53 | 13 | 44 | 0 | `Archie`, `Arrow`, `bliss`, `Circle`, `Circle-Fill`, `Cursor`, `Cursor-Fill`, `EaselIconArrow`, `EaselIconEllipse`, `EaselIconFreehand`, `EaselIconImage`, `EaselIconLine`, `EaselIconPointer`, `EaselIconRectangle`, `EaselIconShapes`, `EaselIconText`, `EaselIconTriangle`, `EaselLoadingStateSquiggle`, ... (+8 portrait photos) |
| `ARC_Favicons` | 4 | 3 | 4 | 0 | `DocumentFaviconLeft`, `DocumentFaviconRight`, `EaselFavicon`, `FaviconBackground` |
| `ARC_HomeButton` | 4 | 1 | 4 | 2 | `boost`, `BoostLarge`, `easel`, `note` |
| `ARC_ImportFeature` | 12 | 0 | 0 | 4 | `Brave`, `ChromeLogo`, `Edge`, `FirefoxLogo`, `Opera`, `OperaGX`, `SafariKeychainImportMonterey`, `SafariKeychainImportVentura`, `SafariLogo`, `SystemPreferencesMonterey`, `SystemPreferencesVentura`, `Vivaldi` |
| `ARC_ImportMenuFeature` | 1 | 0 | 0 | 1 | `password-import-prompt-icon` |
| `ARC_MembershipCard` | 16 | 7 | 6 | 0 | `AnimatingCardBlob`, `BrowserCompany`, `fallback-gradient-1`, `fallback-gradient-2`, `fallback-gradient-3`, `fallback-gradient-4`, `fallback-gradient-5`, `fallback-gradient-6`, `fallback-gradient-7`, `fallback-gradient-8`, `Lines`, `Shape1`, `Shape2`, `Shape3`, `Shape4`, `stamp` |
| `ARC_PictureInPicture` | 4 | 4 | 4 | 0 | `GoBack`, `GoForward`, `meet-pip-chat-selected`, `meet-pip-chat-unselected` |
| `ARC_PreferencesFeature` | 6 | 2 | 3 | 1 | `grain`, `LinksPrefPaneIcon`, `LittleArcHeroImage`, `MaxBanner`, `NewLittleBrowserImage`, `PrefsGeneral` |
| `ARC_ProfilesUI` | 7 | 1 | 7 | 6 | `archie`, `icon-archie`, `icon-archie-add`, `icon-archie-delete`, `icon-archie-move`, `icon-archie-question`, `icon-archie-space` |
| `ARC_ReferralCodeFeature` | 3 | 2 | 2 | 0 | `archibald+arcenio`, `giftIcon`, `logoIcon` |
| `ARC_SadTab` | 1 | 1 | 1 | 0 | `SadTab` |
| `ARC_SharableObjectsFeature` | 1 | 1 | 1 | 0 | `Arc Mail` |
| `ARC_SidebarBanner` | 3 | 2 | 1 | 0 | `maxFeatureBannerIcon`, `newArcIconUnlockedIcon`, `windowsBuddyDayIcon` |
| `ARC_SidebarPlusButton` | 11 | 5 | 5 | 0 | `add-space`, `add-tab`, `boost`, `boost_legacy`, `easel`, `folder`, `note`, `space`, `split-add-bottom`, `split-add-right`, `tab` |
| `ARC_SidebarSyncCloudKit` | 1 | 1 | 0 | 0 | `arcOutlineIcon` |
| `ARC_SiteControlCenter` | 9 | 9 | 5 | 0 | `boost.fill`, `boost.sparkle`, `boost.sparkle.fill`, `capture-full-page`, `copy-url`, `icon-control-center`, `icon-control-center-fill`, `share`, `window-screenshot-icon` |
| `ARC_SpaceCreation` | 1 | 1 | 1 | 0 | `smiley` |
| `ARC_SpaceStyleEditor` | 5 | 1 | 1 | 0 | `DenimKnob`, `DotGrid`, `GrainKnob`, `SandKnob`, `TweedKnob` |
| `ARC_StorableSidebar` | 7 | 0 | 0 | 0 | `GettingStartedFavicon`, `GoogleFavicon`, `ImportFavicon`, `ResourcesFavicon`, `SubstackFavicon`, `WikipediaFavicon`, `YouTubeFavicon` |
| `ARC_TextEditor` | 1 | 0 | 0 | 0 | `GutterButton` |
| `ARC_WelcomeToArcFeature` | 3 | 1 | 0 | 0 | `glow`, `glow-video`, `grain-no-blend` |
| `ARC_WindowThemeUI` | 8 | 0 | 0 | 0 | `denim`, `denim_metal`, `grain`, `grain_metal`, `sand`, `sand_metal`, `tweed`, `tweed_metal` |
| `_App` | 25 | 10 | 18 | 4 | `AppIcon`, `ArcCaptureWatermark`, `BoostIcon`, `CellDropShadow`, `cmd-t`, `ConfluenceIcon`, `cursor`, `FigmaIcon`, `gmailIcon`, `gradient`, `icon-arc`, `icon-browser-navigation-clear-cookies`, `icon-browser-navigation-force-reload`, `icon-browser-navigation-reload`, `icon-browser-navigation-sidebar`, `icon-dialog-easel`, `icon-dialog-note`, `icon-dialog-share`, ... |
| `_DockTilePlugIn` | 10 | 0 | 10 | 0 | `AppIconCanary`, `AppIconCandy`, `AppIconColorful`, `AppIconDev`, `AppIconEarlyBirds`, `AppIconFlutedGlass`, `AppIconHologram`, `AppIconNeon`, `AppIconOriginal`, `AppIconSchoolbook` |
| **Total** | **414** | **118** | **252** | **46** | |

### Template vs. full color

- **Template** (`Template Mode: template`): glyph-style UI icons that take the current foreground color: Easel tools (`EaselIcon*`), split-view actions, rich text list icons, site control center actions (`share`, `copy-url`, `capture-full-page`, `boost.sparkle`), navigation (`icon-browser-navigation-reload`, `-force-reload`, `-clear-cookies`, `-sidebar`), `SadTab`, textures meant to be tinted (`grain-1` to `grain-4`, `grain-no-blend`), membership card shapes and the `stamp`.
- **Full color** (`automatic`): app icons, third-party logos and favicons, onboarding illustrations, previews, textures (`denim`, `sand`, `tweed`, `grain`), gradients, and photos.
- **Dark variants** are used where a template would not do: split-view icons (19 of 21 in `ContextMenus`), the Archie profile faces, Home/Library icons, browser logos in import.

### Icon families

- **App icons.** Ten alternate app icons, each with a preview: `Original`, `Candy`, `Colorful`, `Neon`, `Hologram`, `FlutedGlass`, `Schoolbook`, `EarlyBirds`, `Canary`, `Dev`, plus `AppIconPreviewDisabled`. The `DockTilePlugIn` bundle carries the same ten so the Dock icon can change while Arc is not running.
- **Dia.** `BaseAssets` also ships `DiaAppIcon`, `DiaAppIconBeta`, `-Canary`, `-Dev` and `-Prototype`, and `ArcTooltip.ProductContext` is `arc | dia`: shared code with The Browser Company's next browser.
- **Third-party marks.** App tray and favicons for Google apps, Slack, Notion, Linear, Figma, Jira, Confluence, Spotify, YouTube, X/Twitter, WhatsApp, Zoom, Teams, Outlook, ChatGPT, Claude and more, used by the app tray, command bar integrations and sidebar suggestions. Browser logos (Chrome, Safari, Firefox, Edge, Brave, Opera, Opera GX, Vivaldi) for import.
- **Split view.** A complete `icon-split-*` system: add (top, bottom, left, right), move (four directions), share (horizontal, vertical), close, separate-from-split, layout (horizontal, vertical).
- **Easel.** Tool icons, multiplayer cursors in plain and `-Fill` variants (`Cursor`, `Pencil`, `Movable`, `Moving`, `Interactable-Hover`, `Interactable-Down`, `Shape`), resize cursors, a loading squiggle, eight portrait photos (presumably sample collaborator avatars), and the Windows XP "Bliss" landscape as a sample image.
- **Archie.** Arc's smiley mascot appears as `ArchieDialogIcon`, the `archie` / `icon-archie-*` profile faces (`add`, `delete`, `move`, `question`, `space`), Easel's `Archie`, and the `smiley` used for Space creation.
- **Membership card.** Shapes (`Shape1` to `Shape4`, `Lines`, `stamp`, `BrowserCompany` wordmark), an `AnimatingCardBlob`, and eight `fallback-gradient-*` images.

### SF Symbols

- `ARCUI.SFSymbol { name, source: .system | .custom(bundle), font: { size, weight }?, offset }` wraps both system symbols and custom symbols stored in Arc's bundles (for example `boost.fill`, `boost.sparkle`, `boost.sparkle.fill`).
- At least 141 system symbol names of six characters or more appear in the binary, for example `arrow.uturn.backward`, `checkmark.circle.fill`, `exclamationmark.triangle.fill`, `puzzlepiece.extension`, `rectangle.split.2x1`, `speaker.wave.2.fill`, `sparkles`, `square.and.arrow.up`, `wrench.and.screwdriver`, `xmark.circle.fill`. Shorter names (`plus`, `xmark`, `star`, ...) are not counted.
- `ARCFoundationBase` ships `SFSymbolEmojiLookupTable.json`, mapping **4,491** SF Symbol names to a single emoji (`tag.fill` to a label emoji, `figure.hockey` to a hockey stick). It most likely lets an icon chosen as an SF Symbol fall back to an emoji wherever symbols are not available, such as Space and tab icons synced to other platforms.
- A few small vector logos ship as SVG in `BaseAssets` (`EmptyFavicon`, `figma`, `github-black`, `github-white`, `linear`).

### Animated icons

`ARCUI.TranslucentButtonIconAnimation` draws animated toolbar glyphs in code: `arrow(direction)`, `crossOrHyphen`, `moreMenu(isOpen)`, `plusMenu(isOpen)`, `speaker(isMuted)` (with three sound-wave shapes), `reload(isReloading)`, `forceReload`, `copyLink`, `cross`, `things`. `MusicalIcon` animates `MusicSprite1/2` notes for tabs playing audio.

---

## 5. Motion

### Lottie animations

12 Lottie files, all exported with Bodymovin 5.9.4. Durations are `(op - ip) / fr`.

| Animation | Bundle | Canvas | FPS | Frames | Duration | Purpose |
|---|---|---|---:|---:|---:|---|
| `logo-wave` | ARCUI | 225 x 225 | 60 | 180 | 3.0 s | Animated Arc logo stroke (`AnimatedLogoView`, loop or play once) |
| `archive` | HomeButton | 128 x 128 | 60 | 120 | 2.0 s | Home / Library icon: Archive |
| `boosts` | HomeButton | 128 x 128 | 60 | 60 | 1.0 s | Home / Library icon: Boosts |
| `downloads` | HomeButton | 128 x 128 | 60 | 60 | 1.0 s | Home / Library icon: Downloads |
| `easels` | HomeButton | 128 x 128 | 60 | 60 | 1.0 s | Home / Library icon: Easels and notes |
| `screenshots` | HomeButton | 128 x 128 | 60 | 60 | 1.0 s | Home / Library icon: Screenshots |
| `spaces` | HomeButton | 128 x 128 | 60 | 60 | 1.0 s | Home / Library icon: Spaces |
| `smiley` | PreferencesFeature | 100 x 100 | 30 | 150 | 5.0 s | Archie smiley (eyes and smile layers), `SmileyView` |
| `update-heart-animation` | SidebarBanner | 350 x 350 | 60 | 120 | 2.0 s | Heart with a ring for the update banner |
| `sun` | SpaceStyleEditor | 500 x 500 | 60 | 60 | 1.0 s | Light appearance toggle (circle and rays) |
| `moon` | SpaceStyleEditor | 500 x 500 | 60 | 90 | 1.5 s | Dark appearance toggle (moon and two stars) |
| `automatic` | SpaceStyleEditor | 500 x 500 | 60 | 90 | 1.5 s | Automatic appearance toggle (stars) |

The six Home icons share one structure: markers `hover-start` (frame 1), `hover-end` (frame 11) and `selection-end` (frame 35, or 45 for Boosts), which suggests frames 1 to 11 play on hover and the rest on selection. Their layers are literally named `primaryColor` and `secondaryColor`, which lets the app recolor them through Lottie key paths to match the Space.

Easing used inside these files, by frequency: `cubic-bezier(0.167, 0.167, 0.833, 0.833)` (80, After Effects default), `cubic-bezier(0.333, 0, 0.667, 1)` (38, "easy ease"), and a handful of custom curves including an overshoot `cubic-bezier(0.441, 0, 0.415, 1.835)`.

### Springs and the Motion engine

- **Named springs.** `ARCUI.SpringAnimationStyle` has seven presets: `firm`, `firmSlow`, `firmExtraSlow`, `firmFast`, `springy`, `springyFast`, `springyExtraFast`. Each resolves to `Properties { dampingRatio, frequencyResponse }`, the same two-parameter form as SwiftUI's `spring(response:dampingFraction:)`. The names suggest that "firm" presets settle without visible bounce and "springy" ones overshoot. The numbers are compiled into code and are not in the metadata.
- **`Motion` module.** Arc's own animation engine, independent of Core Animation timing:
  - `Animator` driven by a `CoreVideoDriver` (`CVDisplayLink`, `preferredFramesPerSecond`), one animator per display (`animatorsByDisplayID`), so animations run at each screen's refresh rate.
  - `SpringAnimation` over a `SpringFunction { stiffness, damping, response, dampingRatio, w0, wD }`: a damped harmonic oscillator with natural frequency `w0` and damped frequency `wD`. Supports a clamping range and `resolvesUponReachingToValue`.
  - `DecayAnimation` over `DecayFunction { decayConstant, roundingFactor }` for momentum after a flick.
  - `BasicAnimation` with `duration` and an `EasingFunction` wrapping a cubic `Bezier` (control points plus precomputed polynomial coefficients).
  - Values are SIMD vectors, so position, size and color animate as one; animations resolve within a `resolvingEpsilon` and can be emitted as `CAKeyframeAnimation`.
  - Used by: space swiping (`PageSwipeController`), sidebar transitions, content panel, split view, window expansion (`WindowExpansionAnimator.AnimationConfiguration { response, dampingRatio }`), capture focus rectangle, downloads flying into the Library, Easel text, modal hosting, and the loading indicators below.
- **Reduced motion.** `AnimationRespectingReduceMotionModifier` and `OnAnimatedHover(respectReduceMotion:)` skip animations when the system setting is on.

### Other motion components

| Component | Configurable |
|---|---|
| `ConfettiView` / `ConfettiConfig` | `num`, `shapes`, `colors`, `confettiSize`, `rainHeight`, `fadesOut`, `opacity`, `openingAngle`, `closingAngle`, `radius`, `explosionAnimationDuration`, `rainAnimationDuration`, `opacityFadeOutRange` |
| `ParticlesView` (Core Animation emitter) | per particle: `birthRate`, `lifetime(Range)`, `scale(Range/Speed)`, `color`, `alphaRange/Speed`, emission longitude / latitude / range, `spin(Range)`, acceleration x/y, `velocity(Range)` |
| `SparklesView`, `SparklingIconView` | sparkles `{ size, offset, animationDelay }`, `animationPeriod`, `hasStillSparkles` |
| `ShimmerModifier` | `duration`, `isActive`, `shouldFadeOut` (skeleton loading) |
| `ScrimLoadingIndicatorView` | phases `hidden`, `grabber`, `opacityPulse`, `progressCarousel`; spring-driven track scale |
| `FlipTransitionView` | speed `fast`, `slow` |
| `StreamingTextView` | style `ticker`, `crossDissolve` (streaming AI text) |
| `MarqueeText` | masking distances, `cycleSpacing`, `scrollDelay`, `scrollSpeed` |
| `ShinyHoverEffect` | follows the mouse position; scale `none`, `small`, `large` |
| `ScaleHoverEffect`, `ScaleButtonStyle` | `scaleAmount`; pressed / not pressed opacity |
| Toasts | `ShinyToastAnimationState`: `preShowing`, `showing`, `postShowing`; hover state is tracked (`ShinyToastHoverState`) |
| `AnimatedGrainView`, `AnimatedOrbView`, `WindowBackgroundView` | onboarding background: cycling grain frames, a looping orb video, animated mask radius, orb scale / rotation / opacity |

### Video loops

| File | Bundle | Size | Duration | Use |
|---|---|---|---:|---|
| `background.mp4`, `orb.mp4` | ARCUI | 100 x 100 | 8 s, 6 s | Tiny looping color fields scaled up behind onboarding (`BackgroundVideoView`, `AnimatedOrbView`) |
| `new_tab.mp4`, `pinning.mp4`, `space_swiping.mp4`, `split_view.mp4` | WelcomeToArcFeature | 1920 x 1200 | 8.5 s each | "Welcome to Arc" feature tour |
| `demo.mov` | AuthFeature | 1920 x 1280 | 18.3 s | Sign-up / intro demo |

### Glow progress indicator

`GlowProgressLoadingIndicatorView` is a Metal view (`MTKView`) that draws a soft glowing progress bar. It keeps `progress`, `primaryColor`, `secondaryColor` and `horizontalInset`, and animates progress, intensity and inset with three `Motion.SpringAnimation`s. Its shader (`GlowProgressLoadingIndicator/default.metallib`) has `progressLoadingIndicatorVertex` and `progressLoadingIndicatorFragment`, with uniforms `progress`, `intensity`, `inset`, `cycleProgress`, `primaryColor`, `secondaryColor` (the fragment mixes the two colors and shapes the glow with `pow`, `sqrt` and distance math). The `LoadingPageBorder` color (`#0C50FF` / `#2AB6F6`) is the matching static token for page loading.

### Metal shader libraries

| Library | Size | Functions | Feature |
|---|---:|---|---|
| `ARC_WindowThemeUI/default.metallib` | 33 KB | `gradientVertex/Fragment`, `overlayVertex/Fragment`, `renderVertex/Fragment` | Space theme backgrounds (gradient, texture, cut-out, transitions) |
| `ARC_GlowProgressLoadingIndicator/default.metallib` | 10 KB | `progressLoadingIndicatorVertex/Fragment` | Glowing progress bar |

`ARCUI.MetalHelpers` provides shared setup. A `useMetalByDefault` setting exists in the binary.

---

## 6. Sound

Arc is almost silent. Three audio files ship:

| File | Bundle | Format | Duration | Use |
|---|---|---|---:|---|
| `capture.wav` | SoundEffects | WAV, 48 kHz, 24-bit, stereo | 0.63 s | Screenshot shutter for Arc's Capture tool. `SoundEffects.SoundEffect` has a single case, `capture`. |
| `event.m4a` | SoundEffects | AAC, 44.1 kHz, stereo | 3.52 s | A second sound in the same bundle. It is not a case of the `SoundEffect` enum, so it is either loaded by name elsewhere or unused. |
| `intro-music.mp3` | AuthFeature | MP3, 320 kbps | 21.3 s | Music for the onboarding intro, alongside `demo.mov`. |

`SoundEffectClient` exposes `isEnabled`, `setIsEnabled`, `preload` and `play(SoundEffect)`. The implementation caches `NSSound`s by file name and reads the on/off setting from user defaults.

---

## 7. Components

Most shared UI lives in `ARCUI` (668 types), with feature-level components in `ArcTooltip`, `Toasts`, `BaseAssets`, `CustomInfoPicker` and `SpaceStyleEditor`. Field names below come from the type metadata.

### Buttons

| Component | Configurable properties |
|---|---|
| `ArcButtonStyle` | `variant` (`translucent`), `tone` (`neutral`), `size` (`_46`, `_32`, `_32thin`, `_28`, `_24`, `_16`), `customFontInfo { size, weight }`, `isSquare`, `padding`, `overrideProperties` |
| `ArcButtonStyle.Properties` | `background`, `hoveredBackground`, `pressedBackground`, `foreground`, `pressedForeground`, `disabledBackground`, `disabledForeground` |
| `TranslucentButtonItem` / `TranslucentButton` | `buttonType` (`icon(name)` or `animatedIcon(...)`), `size`, `weight`, `customFontInfo`, `properties`, `action`, `isEnabled`, `accessibilityLabel`, `isSquare`, `sendActionOnMouseDown`. Used for the toolbar navigation buttons and the sidebar dock. |
| `HoverableButtonStyle` | `cornerRadius`, `visualStatus` (`default`, `alwaysSelected`, `alwaysShowBackground`), `font`, `hoverTrackingMode`, `fillContainer`, `fillColorOverride` |
| `BackgroundHighlightButtonStyle` | `cornerRadius` |
| `ScaleButtonStyle` | `scaleAmount`, `opacityConfiguration { pressed, notPressed }` |
| `ScrimButtonStyle` | `accentColor`, `backgroundColor`, `foregroundColor` |
| `GradientButtonStyle` | `gradientColor1`, `gradientColor2`, `foreground` |
| `SkeuPrimaryButtonStyle`, `SkeuSecondaryButtonStyle` | `borderShape` (`roundedRectangle`, `circle`) |
| `CustomSwitchToggleStyle` | `dotColor`, `fillColor` |
| `RadioGroupButton` | `size` (`fullSize`, `mini`, `list`, `condensedList`), appearance (`left`, `leftFlushed`, `right`), options `showBorder`, `scaleOnHover`, `roundedCorners`, `hideContent`, `selectionColor`, `backgroundColor`, `checkboxBackgroundColor`, `height`, `preferredOption` |
| `LongPressButton`, `ControlButton` | `action` + `onLongPressAction`; `onClick`, `onMouseDown`, `onRightClick`, `onDragBegin`, `dragHysteresis` |
| `StatefulButton`, `PrimaryActionButton` | `Config { icon, tooltip }` |
| `BaseAssets.DropdownMenuButton` | `frameHeight`, `backgroundColor`, `foregroundColor`, `shadow`, `icon`, `cornerRadius`, `trailingIconPadding` |

Button colors come from `ARCUI` tokens, in four tones with face / hovered / pressed / foreground / border / shadow / icon slots: **Primary** (`#3139FB`), **Neutral** (white with `#DBDBDB` border; dark `#302F63` with `#6362AE` border), **Destructive** (`#F53714`), **Contrasting** (`#F36672` with a `#D34955` drop shadow), plus **Disabled** states.

### Text input

| Component | Configurable properties |
|---|---|
| `BorderedTextFieldView` | `placeholder`, `text`, `inputTransform`, `onReturn`, `useSecureTextField`, `contentType`, `font`, `usesSingleLineMode`, `color`, `caretColor`, `cornerRadius`, `truncationMode`, `focusLoopKey`, `onFocused`, `onMoveUp`, `onMoveDown` |
| `BorderlessTextFieldView` | Same, without border; joins a manual keyboard focus loop |
| `FocusRingSettableTextField`, `MultilineTextEditorWithPlaceholder`, `TextViewWithPlaceholder` | Focus ring control, multi-line with placeholder |
| `DropdownSelector` | Options, display value, search field, clearing behavior, panel direction |
| `MenuSearchField`, `CustomInsetSearchField` | Search inside menus |

Tokens: `InputFieldBackgroundColor` (`#FFFFFF` / white @ 0.15), `InputFieldBorderColor` (`#DBDBDB` / white @ 0.3), `FocusRing` `#228CFF`.

### Popovers, dialogs and prompts

| Component | Configurable properties |
|---|---|
| `PopoverBackgroundView` | `BackgroundStyle`: `translucent { material, state, blendingMode, isEmphasized }` or `color(NSColor)`; `BorderStyle`: `decorative(outer, inner)` or `emphasized(color, width)` |
| `PopoverPromptView` | `icon` (SF Symbol), `title`, `primaryAction`, `secondaryAction`, optional `tertiaryAction`, `needsDoubleClickProtection` |
| `HostingPopover`, `CustomPopoverRootView` | SwiftUI content in an `NSPopover` |
| `DialogSheetOptions` | `mode` (`text(default)`, `alert`, `confirm`), `title`, `message`, `okText`, `cancelText`, `displaySuppressionCheckbox` |
| `CalloutShape`, `RoundedCornersShape`, `CornerType` | Shapes with per-corner radii |

Popover tokens: `PopoverBackground` `#FAFBFF` / `#151C30`, `PopoverTitle` `#181B1F` / white, `PopoverMessage` `#060E2B` @ 0.75, `PopoverBorder` clear / `#D3CEED` @ 0.2, `PopoverShadow` `#131C34` @ 0.3 / 0.8.

### Tooltips (`ArcTooltip`)

`ArcTooltipConfiguration`:

- `content`: `standard(AnyView)` or `custom(AnyView)`; standard content is `ArcTooltipLabel { title, subtitle }`
- `keyboardShortcut`: shown as key caps (`TooltipKeyboardShortcutView`)
- `preferredAnchor`: `view(edge)` with eight edges (`top`, `bottom`, `leading`, `trailing`, and the four corners) or `cursor`
- `appearanceConfiguration`: `clippingShape`, a list of `shadowConfigurations { color, radius, offset, opacity, blendMode }`, an optional light/dark `borderConfiguration`
- `presentationBehavior`: `onMouseIdle(delay)` or `immediate`
- `maxWidth`, `allowedModifierKeys`, `colorPalette` (Space-derived, see above)

Tooltips render in their own window (`TooltipWindow`). `ARCUI.TooltipCardContainerView` provides the card with a pointer (`disclosureSize { baseLength, pointLength }`, `disclosureDirection`), two shadow layers, `cardCornerRadius`, `backgroundColor` and `borderColor`.

### Toasts (`Toasts`)

- 74 toast types (`ToastType`), for example `copyTabURL`, `tabPinned(toSpaceName)`, `undo`, `screenshotCopied`, `translateComplete`, `newSpaceCreated`, `archivedTabs(numTabs)`, `batterySaverMode`, `downloadRenamed`, `boosts(.installed)`.
- Levels: `exciting`, `neutral`, `success`, `error`.
- Content: `default { icon, label, subLabel, buttons }`, `undoable { text, showShortcutHint }`, `downloadRenamed`, `tracing { duration }`, `shortcut { leadingLabel, shortcut, trailingLabel }`, `empty`. Buttons are `shareButton(items)`, `confirmButton(title, confirmationTitle, action)` or `actionButton(title, role: primary | secondary, action)`.
- Positions: `fromTopRight`, `fromTopCenter`, `fromLeadingEdgeAtBottom`, `floatingTopRight`. Locations: a window content pane, the whole window, or the Library.
- Display options include `duration`, an optional `accessory { text, image }`, a light/dark `ToastColorPalette` and the Space background palette (the "shiny" toast draws the Space background behind itself, with particles).

### Menus

`ArcContextMenu` / `ArcContextMenuItem` (title style, checked state, alternate item when holding a modifier), `CallbackMenuItem`, and `ViewMenuKeyboardSelectionHandler`. Custom menu tokens in `ArcMenu`: `MenuBackground` `#FAFBFF` / `#393841`, `MenuHoverBackground` `#B7D1FF` / `#3970C5`, `MenuText` `#494949` / `#EBEBEC`.

### Feedback, status and decoration

| Component | Configurable properties |
|---|---|
| `CircularProgressView` | `icon`, `iconTintColor`, `activatedIconTintColor`, `backgroundColor`, `progressColor`, `progressLineWidth`, `shadowConfiguration` |
| `EdgeFeedbackView` | `gradientKeyColor`, `edge` (`leading`, `trailing`), progress configuration; used by the sidebar view for edge gesture feedback |
| `RecordingDotIndicator` | `dimension`, `stroke`, `padding`, `displayShadow`, `color` |
| `UnreadPipView` | `pipColor` with gradient and border layers |
| `KeyboardShortcutView`, `KeyboardKeyCapView` | `KeyCapSize`: `small`, `medium`, `large(minSize, maxSize)` |
| `GradientBorderGlowView` | `gradientType` (`peachBlue`) |
| `GradientCard` | `gradientColor1`, `gradientColor2`, `background` |
| `EmptyStateBackgroundView` | `strokeStyle` (`solid`, `dashed`), colors for `background`, `innerStroke`, `outerStroke` |
| `ShadowView`, `ShadowConfiguration` | `color`, `opacity`, `radius`, `offset`, `spread` |
| `AnimatedEllipsisView`, `IconWithProgressIndicatorView`, `SmileyView`, `AnimatedLogoView` | Loading ellipsis, icon with progress ring, Archie smiley, logo animation |

### Layout and windows

`SplitViewController` (panes, dragger handles, drop targets, resize styles), `FlowLayout`, `GridStack`, `ExpandingScrollView`, `ScrollViewWithTopDivider`, `GroupWithDividers`, `FeatheredContainerView` (soft edge fades), `HStacking` / `VStacking`, `MovableWindow` (floating panels with resize anchors), `WindowStandardButtons` (custom traffic lights) and `WindowDraggableView` (title bar double-click behavior).

### Spacing, radii and shadows

`BaseAssets.ViewConstant` defines `Space`, `Radii`, `BorderWidth` and `Shadow` namespaces, with `ShadowStyle { radius, offset }`, `ScrimConstants` and `WebViewConstants`. Other constant enums exist per feature (`TooltipConstants.Animation` / `.Layout`, `ToastConstants`, `DialogViewConstants`, `SplitViewConstants`, `SidebarUIConstants`, `ModalConstants`, `EaselConstants`). Their values are static properties compiled into code and do not survive in the type metadata, so this document cannot list them. What is recoverable:

- Button heights from `ArcButtonStyle.Size`: 46, 32, 28, 24, 16 (plus a thin 32).
- Lottie canvases: 128 pt for Home icons, 500 for the appearance toggles.
- Easel export radii (in Easel points): 6, 8, 10; Easel document width 1,000 points.

---

## 8. Reproducing the extraction and the contact sheet

`scripts/extract-app.sh [/Applications/Arc.app]` copies the app into `vault/app/` and writes everything this document is based on to `vault/extracted/`:

- `bundles/<Bundle>/assets/colors.json` (light/dark colors per bundle), `assets/images/` (PNG and PDF renditions), `assets-info.json` (raw `assetutil --info`), `raw/` (fonts, Lottie, sounds, videos, Metal libraries, HTML/CSS/JS)
- `swift/Arc.swift` (reconstructed Swift types), `strings/Arc.txt` (binary strings)

`vault/` is gitignored and never committed. For a quick visual index, a local contact sheet at `vault/extracted/contact-sheet.png` shows all 460 PNG image assets in a labeled grid, grouped by bundle, with template images drawn dark and marked `[T]`. It was made with a small Pillow script outside the repository and, like everything in `vault/`, stays on your machine.

## 9. Method and limits

- **Exact:** color values (from compiled asset catalogs), color space, template mode, image names and counts, font files and their name tables, Lottie timing and markers, audio and video metadata, Metal function and argument names, Swift type names, fields and enum cases.
- **Interpreted:** what a token or type is for, based on its name, module, and where it is referenced. Such statements are worded as interpretation above.
- **Not recoverable from metadata:** numeric constants in code (spring parameters, spacing, radii, font sizes in the chrome) and the exact palette derivation math. Those would need disassembly.
- **Source:** Arc for macOS 1.174.0 (build 91305).

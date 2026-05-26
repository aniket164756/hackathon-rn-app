---
description: "File naming, extension, and folder placement rules for this React Native project. Load when creating, renaming, or reviewing files under src/."
---

# Project File Structure Conventions

## `src/core-components/`
- **Folder name**: lowercase kebab-case (e.g. `my-button/`)
- **Component file**: `IBL-<PascalCase>.component.tsx`
- **Style file**: `IBL-<PascalCase>.style.ts`
- **Test file**: `IBL-<PascalCase>.test.tsx`

## `src/core-constants/`
- **Filename**: lowercase kebab-case
- **Extension**: `.constant.ts`

## `src/core-navigations/`
- **Filename**: lowercase kebab-case
- **Extension**: `.navigation.tsx`
- No other file types permitted without justification.

## `src/modules/<module-name>/`
Module folder names are lowercase kebab-case.

| Subfolder | Extension | Notes |
|---|---|---|
| `navigations/` | `.navigation.tsx` | Every screen in `screens/` must be registered here |
| `screens/` | `.screen.tsx` | One file per screen |
| `styles/` | `.style.ts` | One per screen, name must match screen (e.g. `home.style.ts` for `home.screen.tsx`) |
| `utils/` | `.utils.ts` | Module-specific shared functions |

## Summary Table

| Folder | Naming | Extension |
|---|---|---|
| `core-components/<name>/` | `IBL-<PascalCase>` | `.component.tsx` / `.style.ts` / `.test.tsx` |
| `core-constants/` | lowercase-kebab | `.constant.ts` |
| `core-navigations/` | lowercase-kebab | `.navigation.tsx` |
| `modules/<name>/navigations/` | lowercase-kebab | `.navigation.tsx` |
| `modules/<name>/screens/` | lowercase-kebab | `.screen.tsx` |
| `modules/<name>/styles/` | lowercase-kebab | `.style.ts` |
| `modules/<name>/utils/` | lowercase-kebab | `.utils.ts` |

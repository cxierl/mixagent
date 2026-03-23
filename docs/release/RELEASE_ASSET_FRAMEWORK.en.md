# Release Asset Framework

## Goal

Define a stable desktop release structure for MixAgent that supports clean distribution and auto updates.

## Recommended Repository Layout

```text
mixagent/
  electron/
  docs/
    release/
      RELEASE_ASSET_FRAMEWORK.zh-CN.md
      RELEASE_ASSET_FRAMEWORK.en.md
      v0.1.2.zh-CN.md
      v0.1.2.en.md
  index.html
  package.json
  package-lock.json
  README.md
  CHANGELOG.md
  ISSUE_LOG.md
```

## GitHub Release Asset Classes

Each version should publish three kinds of assets:

### 1. Installer asset

- `MixAgent Setup x.y.z.exe`

Purpose:

- one-click install for end users
- standard NSIS Windows installation

### 2. Differential update asset

- `MixAgent Setup x.y.z.exe.blockmap`

Purpose:

- supports efficient delta downloads for desktop auto update
- reduces update bandwidth

### 3. Update metadata

- `latest.yml`

Purpose:

- tells the desktop app what the latest version is
- tells the app which files should be downloaded

## Release Notes

Each version should ship with:

- Chinese release notes
- English release notes

Recommended files:

- `docs/release/v0.1.2.zh-CN.md`
- `docs/release/v0.1.2.en.md`

## Recommended Release Flow

1. bump version
2. package desktop build
3. verify generated assets
4. commit code
5. create tag
6. push to GitHub
7. create GitHub Release
8. upload `.exe`, `.blockmap`, and `latest.yml`
9. paste bilingual release notes

## Auto Update Requirements

Auto update only works when all of these are true:

1. the released version is newer than the installed one
2. assets are uploaded to the correct GitHub Release
3. `latest.yml` matches the release version
4. the configured GitHub `owner/repo` is correct

## Current Version

The current desktop release version is `v0.1.2`.

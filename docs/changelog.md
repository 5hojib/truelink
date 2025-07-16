### V1.1.0

New Features:
- Add MIME type guessing module for Python<3.14 and integrate mime_type field across LinkResult and FileItem
- Introduce configurable timeout and retry logic in TrueLinkResolver
- Add support for Ranoz.gg resolver

Bug Fixes:
- Correct maintainer email in pyproject.toml
- Ensure error messages and password prompts format consistently
- Handle missing href and invalid URLs more robustly

Enhancements:
- Refactor BaseResolver session management and add helpers for filename extraction
- Unify HTTP content fetching in MediaFire, LinkBox, GoFile, and YandexDisk resolvers and streamline API call patterns
- Standardize mime_type handling and signature of _fetch_file_details in all resolvers
- Remove deprecated HxFile and Qiwi resolvers and tidy supported domains list

Build:
- Add flake8-annotations to lint configuration

Documentation:
- Update README to include mime_type field example and bump version to 1.1.0

Chores:
- Bump package version to 1.1.0
- Mark remaining unimplemented resolvers as TODO

### V1.0.0

Initial Release
- Initial release of TrueLink library

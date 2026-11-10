# locales

Shared i18n strings for the web UI and agent communications: `en.json` (default) and `es.json`.

Keys are nested by area (`severity.critical`, `date_type.committed`); key naming is Proposed. Both files must have exactly the same keys (checked by the tests). No user-facing string is hardcoded in code.

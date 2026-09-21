# Migrating authentication state

Use when the source persists profiles, cookies, browser storage, or managed login.
Reviewed against [Notte profiles](https://docs.notte.cc/features/sessions/browser-profiles)
and the four provider references on 2026-09-21.

## Choose the state path

1. **Fresh login:** create a Notte profile, use the existing login workflow or
   authorized human login, then save the profile. Prefer this when complete state
   export/import is unavailable or identity changes invalidate existing tokens.
2. **Supported state transfer:** where authorized, export only required cookies
   and storage from the source, map the schema, import into the intended Notte
   context, and validate authenticated behavior. Export from live-only APIs before
   releasing the source session. Record which state types were actually transferred.
3. **Full profile transfer:** use only when an explicit compatible import/export
   path is documented and tested. Provider profile IDs and archives are not
   interchangeable, even when both providers use Chromium.

Do not promise zero-login migration. An IP/fingerprint change, MFA, token expiry,
passkeys, device binding, or missing storage may require reauthentication. A
Profile persists state; it does not recreate a provider's managed-auth service,
credential vault, account identity, or token-refresh policy.

## Map persistence intent

| Source | Notte |
|---|---|
| Kernel profile `save_changes` | `profile: {id: newNotteProfileId, persist: ...}` |
| Browserbase persistent Context `persist` | Same intent; map to a new Notte profile, not a Playwright context ID. |
| Hyperbrowser `persistChanges` / `persist_changes` | Map write intent to `persist`. |
| Steel `profileId` + `persistProfile` | Map source ID to new Notte profile ID, and write intent to `persist`. |
| Steel `sessionContext` | Explicit supported-state transfer; not a full profile or a Notte start option. |

Notte documents `persist=False` as the default. With `persist=True`, it saves the
session's state when the session ends. Python profile creation returns
`profile.profile_id`; inspect the selected SDK for other languages. Maintain the
source-to-Notte ID mapping in the application's existing tenant/account storage.
Never assign every account to one shared profile.

## Storage and isolation

- Use the default context associated with the profile. Creating a new incognito
  context can discard the identity you intended to restore.
- Inspect cookie domains, paths, expiry units, SameSite, secure/HttpOnly, and
  partitioning. Do not drop fields silently just to make a schema validate.
- Cookies are only part of authentication. Inventory localStorage, IndexedDB,
  sessionStorage, and any device-bound state. Playwright storage-state support
  depends on version/options; do not assume it exports every storage class.
- Provider context JSON is not automatically Playwright `storage_state`. Validate
  the structure and supported import API before applying it. Do not inject
  localStorage at the wrong origin or navigate authenticated state to an unrelated
  host while testing.
- Preserve reader/writer intent and account isolation. Until concurrent writes
  are documented and tested, serialize profile writers or give workers separate
  profiles. Never assume snapshots merge updates.
- Treat exported state as credentials. Use the existing secret storage or a
  restricted temporary location, never a committed fixture or tool transcript.
  Remove migration exports when no longer needed; do not delete the source
  profile or revoke working credentials as part of the test.

## Two-session acceptance check

Use an authorized account and a read-only application assertion. In session A,
restore/login, verify the expected account, and save the Notte profile on stop.
Wait for documented save readiness, with a bounded deadline. In a separate
session B, load that profile without writing and verify the same authenticated
account and required workflow state. An HTTP 200, a login-page title, or a cookie
count does not establish authenticated success. Test tenant isolation when the
application is multi-account. Report state types not migrated and any required
interactive login.

Fetch [Notte cookies](https://docs.notte.cc/features/sessions/cookies) for cookie
operations and the source provider's profile/context links for export semantics.
Use the [Playwright authentication guide](https://playwright.dev/docs/auth) for
version-appropriate storage-state handling. Fetch vault/managed-auth documentation
only when the source actually uses those services.

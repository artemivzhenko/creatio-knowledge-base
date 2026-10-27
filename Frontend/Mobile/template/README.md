# Creatio Mobile SDK module template

A Creatio Mobile (8.2+) remote module: TypeScript + webpack, bundled into `main.js` and
shipped inside a package as file content. The mobile app loads it on synchronization and
registers the request handlers declared in `@CrtModule`.

`tsconfig.json`, `webpack.config.js` and `tools/{common,inject-on-device,prepare-for-debug}.js`
are the official `ts_sdk_template_module` files, unchanged.

## Make it yours

1. Copy this folder next to your packages, e.g. `projects/UsrMobileModule`.
2. Rename the module in three places that must stay identical:
   - `moduleName` in `creatio-mobile-config.json`
   - the class and the string in `bootstrapCrtModule(...)` in `src/index.ts`
   - (derived) the output folder `Files/src/mobile/<moduleName>/` - created by `npm run deploy`
3. Point `targetPackagePath` in `creatio-mobile-config.json` at your package folder.
4. Put the real page schema name(s) into `src/config/scopes.ts` (see "Scopes" below).
5. Replace `usr.MyRequest` / `UsrMyRequestHandler` with your request and logic.

```bash
npm install
npm run build:deploy      # webpack + copy main.js into <package>/Files/src/mobile/<moduleName>/
```

Then load the package into Creatio and re-synchronize the mobile app
(Settings -> Synchronization). Without a re-sync the device keeps the old `main.js`.

## What is inside

| Path | What it is |
|---|---|
| `src/index.ts` | entry point: `@CrtModule` + `bootstrapCrtModule` |
| `src/config/scopes.ts` | the page schemas the handlers run in |
| `src/requests/my-request.ts` | a custom request raised from a page button |
| `src/handlers/my-request.handler.ts` | handles that request: read/set attributes, run a process |
| `src/handlers/attribute-change.handler.ts` | intercepts a platform request and passes it on |
| `src/handlers/scope-probe.handler.ts` | diagnostic: prints the real scope value (not registered) |
| `tools/copy-to-package.js` | `npm run deploy` |
| `tools/inject-on-device.js` | `npm run inject-on-device`: adb push `main.debug.js` to Android |
| `tools/dump-sdk-surface.js` | `npm run sdk:surface -- <regex>`: public API of the installed SDK |

## Scopes

A handler only runs in the scopes listed in `@CrtRequestHandler`. The value is a Freedom UI
mobile page schema name (`SchemaType: "MobileSchema"`, e.g. `UsrMyEntity_MobileFormPage`).
An empty array fires on every page of the app - never ship that.

Classic mobile schemas (`settingsType: "RecordPage"`, no `viewConfigDiff`) cannot host handlers.

What the platform actually puts into `request.scopes` is undocumented. To learn it: register
`UsrScopeProbeRequestHandler` in `src/index.ts`, `npm run build:inject-on-device`, restart the
app, open the page, read the `[UsrMobileModule] scopes on crt.LoadDataRequest: [...]` line in
`chrome://inspect`, copy the value into `scopes.ts`, remove the probe again.

## Page side

Add a button to the mobile form page (take `parentName` from the designer):

```json
{
  "operation": "insert",
  "name": "UsrMyButton",
  "parentName": "GridContainer_a1b2c3d",
  "propertyName": "items",
  "index": 0,
  "values": {
    "type": "crt.Button",
    "caption": "Do the thing",
    "size": "medium",
    "clicked": {
      "request": "usr.MyRequest",
      "params": { "attributeName": "PDS_UsrName_a1b2c3d" }
    }
  }
}
```

`clicked.params` delivery on mobile pages is undocumented - the handler works without them.

## Traps

- **The page attribute is not the column.** The designer generates a suffix
  (`PDS_UsrField_a1b2c3d`). That name is what arrives in `request.attributeName` and what
  `$context.getAttribute()` expects. Re-creating the field changes the suffix.
- **`EnableMobileSDK` must be on for all users.** The toggle on the features page adds a rule
  for the current user only, which does not reach the account the device logs in with.
- **Pass requests on** with `return this.next?.handle(request)` unless you fully replaced the
  platform behaviour; calling `next` after handling a platform request yourself runs the stock
  logic a second time.
- `@creatio/mobile-common` is a webpack external (`crtSdk`). Any other runtime dependency has
  to fit inside `main.js`.
- No unit tests: the SDK only runs inside the mobile runtime. Verification is a clean build
  plus a run on a device or emulator. `Logger.console()` is the only logging that reaches
  `chrome://inspect`.

| Symptom | Check |
|---|---|
| Handler never fires | `EnableMobileSDK`; folder name = `moduleName` = bootstrap name; app re-synced |
| Fires on every page | `scopes` empty or wrong page name |
| Platform logic runs twice | `this.next` called after handling the request yourself |
| Attribute not found | generated suffix differs from the one in the code |
| TypeScript does not build | `npm update @creatio/mobile-common` |

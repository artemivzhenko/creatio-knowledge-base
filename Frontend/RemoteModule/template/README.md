# Freedom UI remote module template

An Angular remote module for Creatio Freedom UI with two kinds of customization:

- a **custom view element** (`usr.Input`) that appears in the Freedom UI Designer;
- **request handlers** that run in Freedom UI pages: one for a custom request raised by a
  button, one that intercepts page initialization.

Based on the official Academy example (Angular 15, `@creatio-devkit/common` 0.808).

## Build

```bash
npm install          # the lock file of the Academy example is out of sync, so not `npm ci`
npm run build
```

`outputPath` in `angular.json` points into the package file content. Set it to
`<Package>/Files/src/js/<module_name>`, then re-register the file content in Creatio
(compile, or "Update packages from file system"). Copying files alone changes nothing.

## Make it yours

1. Rename the module: `name`/`uniqueName` in `webpack.config.js`, the first argument of
   `bootstrapCrtModule()` in `src/app/app.module.ts`, and the folder in `outputPath`.
   All three must be identical.
2. Rename or delete the example element in `src/app/view-elements/input/`.
3. Put your page schema codes into `src/app/handlers/scopes.ts`.

## What is inside

| Path | What it is |
| --- | --- |
| `src/app/app.module.ts` | `@CrtModule`: `viewElements` and `requestHandlers` |
| `src/app/view-elements/input/` | example custom view element |
| `src/app/requests/my.request.ts` | custom request `usr.MyRequest` |
| `src/app/services/my-data.service.ts` | Angular service calling a configuration web service |
| `src/app/handlers/my-request.handler.ts` | handles `usr.MyRequest`, writes the result into a page attribute |
| `src/app/handlers/page-init.handler.ts` | intercepts `crt.HandleViewModelInitRequest` and raises `usr.MyRequest` on page load |
| `src/app/handlers/scopes.ts` | the pages the handlers run in |

## Page side

```jsonc
// viewModelConfigDiff: the attribute the handler writes
{ "operation": "merge", "path": ["attributes"], "values": { "UsrMyValue": {} } }

// viewConfigDiff: a button raising the custom request
"clicked": { "request": "usr.MyRequest", "params": { "recordId": "$Id" } }
```

## Traps

- **Empty `scopes` makes a handler global.** It runs on every Freedom UI page.
- **The decorator alone registers nothing.** A handler must be listed in `requestHandlers`.
- **Constructor injection needs `resolveDependency`** in `bootstrapCrtModule()`. Without
  it the injected service is undefined.
- **Undeclared attributes are ignored.** Writing `$context['X']` does nothing unless the
  page declares `X` in `viewModelConfigDiff`.
- **Call `this.next`** unless you replace the platform behaviour on purpose. Skipping it
  disables the stock handler and every handler after yours.

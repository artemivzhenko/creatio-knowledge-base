// --- How to load an external JavaScript library in Creatio FreedomUI --------
//
// Creatio uses RequireJS as its module loader. To use a third-party library
// (charting, date formatting, API clients, etc.) you must:
//   1. Add the .js file to your package (e.g. under src/js/).
//   2. Register it with requirejs.config so RequireJS knows where to find it.
//   3. Declare it as a dependency in the define() call of the page that uses it.
//
// This file is a standalone loader module - place it in a separate schema
// (e.g. "UsrMyLibLoader") and load it from the page's SCHEMA_DEPS if needed.
//
// Content Security Policy (CSP):
//   If the library makes requests to external domains, add those domains to the
//   relevant CSP directives (connect-src, frame-src, etc.) in System settings.
//   Docs: https://academy.creatio.com/docs/8.x/setup-and-administration/administration/security-settings/content-security-policy

requirejs.config({
	paths: {
		// Map a short alias to the file inside your Creatio package.
		// Terrasoft.getFileContentUrl resolves the correct URL at runtime.
		"MyExternalLib": Terrasoft.getFileContentUrl("YourPackageName", "src/js/my-lib.js")
	}
});

// This define wraps the loader module itself - it has no exports.
// The library is now available as a RequireJS dependency by the alias above.
define("UsrMyLibLoader", ["MyExternalLib"], function(MyLib) {
	// MyLib is now the loaded library object (whatever it exports or attaches to window).
	// For Angular components that need the library on window, assign it here:
	// window.MyLib = MyLib;
	return {};
});


// --- Using the library inside a FreedomUI page -------------------------------
//
// Add the alias as a dependency and argument in the page define:
//
// define("MyPage_FormPage", /**SCHEMA_DEPS*/["MyExternalLib"]/**SCHEMA_DEPS*/,
//     function/**SCHEMA_ARGS*/(MyLib)/**SCHEMA_ARGS*/ {
//     return {
//         handlers: /**SCHEMA_HANDLERS*/[
//             {
//                 request: "crt.HandleViewModelInitRequest",
//                 handler: async (request, next) => {
//                     await next?.handle(request);
//                     // MyLib is available here as a closure variable
//                     const result = MyLib.doSomething();
//                 }
//             }
//         ]/**SCHEMA_HANDLERS*/
//     };
// });

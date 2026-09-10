// --- How to create a shared helper (singleton / constants module) ------------
// SOURCE: _SalesUp_Base/Schemas/SuFreedomMessageUtils (singleton) and the
// SuBaseJSConstants / SuJSConstants_DT / SuRejestrSync_JSConstants family
// (plain constant modules).
//
// TWO SHAPES, both schemas of type "Module".
//
// 1. CONSTANTS MODULE - the simplest and the one you should reach for first.
//    Return a frozen object of ids and codes, then add the module to the
//    dependency list of every schema that needs them. This is how you stop
//    GUID literals from being copy-pasted across pages: a lookup id changes in
//    one place instead of twenty.
//
// 2. Ext SINGLETON - a class registered in the Terrasoft namespace, reachable
//    from anywhere as Terrasoft.<AlternateClassName> WITHOUT a dependency
//    declaration. Use it only when the helper must hold mutable state shared by
//    modules that cannot see each other (a registry, a cross-module cache).
//    The global reach is exactly what makes it risky: state survives page
//    transitions and leaks between records opened in one session.
//
//    Ext.define("Terrasoft.configuration.<Name>", {
//        alternateClassName: "Terrasoft.<Name>",
//        singleton: true,
//        ...
//    });
//
// Prefer shape 1. Reach for shape 2 only when a plain module return value
// cannot travel where you need it.

// ======================= 1. CONSTANTS MODULE =================================
define("QSBaseJSConstants", [], function() {

	// Object.freeze turns an accidental write into a silent no-op rather than a
	// change every other page sees.
	return Object.freeze({

		OrderStatus: Object.freeze({
			InWork:    "f6c25e34-63f3-4b6d-9769-db0f37d42f0e",
			Processed: "e0382e9c-e5ae-4cb8-ae08-5e4ef061830c",
			Canceled:  "ac84a45a-8bc2-496b-be63-2f45aeb58db3"
		}),

		Service: Object.freeze({
			Import: "04d3af7b-0c97-4504-9368-ea1a5359c341",
			Export: "3a923be7-51ac-4712-8e7b-2b2ee21657b2"
		}),

		// Lookup-shaped constants are handy when you assign them with set().
		YesNo: Object.freeze({
			Yes: { value: "c92c530c-027a-48ae-ba5c-93e7dcbed661", displayValue: "Yes" },
			No:  { value: "d5b0df38-08d9-48a0-b25f-929ddb513713", displayValue: "No" }
		})
	});
});

// Consuming it:
//
// define("QSMyEntity1Page", ["QSBaseJSConstants"], function(constants) {
//     return {
//         entitySchemaName: "QSMyEntity",
//         methods: {
//             isInWork: function() {
//                 var status = this.get("QSStatus");
//                 return !!status && status.value === constants.OrderStatus.InWork;
//             },
//             markAsUrgent: function() {
//                 this.set("QSIsUrgent", constants.YesNo.Yes);
//             }
//         },
//         diff: []
//     };
// });

// ======================= 2. Ext SINGLETON ====================================
// define("SuFreedomMessageUtils", [], function() {
//
//     Ext.define("Terrasoft.configuration.SuFreedomMessageUtils", {
//         // The global name: Terrasoft.SuFreedomMessageUtils
//         alternateClassName: "Terrasoft.SuFreedomMessageUtils",
//         singleton: true,
//
//         items: {},
//         config: {},
//
//         addItem: function(config) {
//             this.config = config;
//         }
//     });
//
//     // Returning it also allows the usual dependency-injected access.
//     return Terrasoft.SuFreedomMessageUtils;
// });
//
// Used from any schema, with or without declaring the dependency:
//     Terrasoft.SuFreedomMessageUtils.addItem({ text: "hello" });

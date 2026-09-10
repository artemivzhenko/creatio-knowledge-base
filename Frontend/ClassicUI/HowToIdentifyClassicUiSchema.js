// --- How to recognise a Classic UI schema on the file system -----------------
// A Creatio package stores every client schema in its own folder under
// <Package>/Schemas/<SchemaName>/. The folder always contains:
//
//   <SchemaName>.js   - the schema source (this is what you edit)
//   properties.json   - schema kind marker
//   descriptor.json   - package/schema descriptor
//   metadata.json     - designer metadata (generated, do not hand-edit)
//
// properties.json tells you WHICH kind of client schema it is:
//
//   { "Properties": { "CreatedInVersion": "8.0.5.2483",
//                     "SchemaType": "EditViewModelSchema" } }
//
// SchemaType values and what they mean:
//
//   "EditViewModelSchema"       - Classic UI record page (edit page) or mini page.
//                                 Has entitySchemaName, attributes, details,
//                                 businessRules, methods, diff.
//   "GridDetailViewModelSchema" - Classic UI detail (grid embedded in a page).
//   "ModuleViewModelSchema"     - Classic UI section schema (SectionV2) / workplace.
//   "Module"                    - standalone AMD module: custom view element,
//                                 helper, or a CSS-only module (empty .js + .css).
//   "AngularSchema"             - Freedom UI page. NOT Classic UI, different API.
//
// Localizable strings and images do NOT live in the schema folder. They live in
//   <Package>/Resources/<SchemaName>.ClientUnit/resource.<culture>.xml
// See HowToUseLocalizableStrings.js.
//
// Practical rule: if the .js is define("Name", [deps], function(...)) returning
// an object with diff / attributes / methods, it is Classic UI. If it returns
// viewConfigDiff / handlers / converters, it is Freedom UI.

define("QSMyEntity1Page", [], function() {
	return {

		// The Entity (object) this page edits.
		entitySchemaName: "QSMyEntity",

		// Plain non-observable fields on the view model instance.
		properties: {
			lastActionsDashboardClick: 0
		},

		// Observable view model columns (see Attributes/).
		attributes: {},

		// Nested detail schemas rendered on this page (see Details/).
		details: /**SCHEMA_DETAILS*/{}/**SCHEMA_DETAILS*/,

		// Modules embedded into the page.
		modules: /**SCHEMA_MODULES*/{}/**SCHEMA_MODULES*/,

		// Designer-generated declarative rules (see BusinessRules/).
		businessRules: /**SCHEMA_BUSINESS_RULES*/{}/**SCHEMA_BUSINESS_RULES*/,

		// Sandbox message contract (see Messaging/).
		messages: {},

		// Reusable behaviour mixed into the view model.
		mixins: {},

		// All page logic.
		methods: {},

		dataModels: /**SCHEMA_DATA_MODELS*/{}/**SCHEMA_DATA_MODELS*/,

		// Declarative view modifications applied on top of the parent schema.
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});

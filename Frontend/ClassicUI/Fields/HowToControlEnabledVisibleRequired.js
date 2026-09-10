// --- How to enable / hide / require a field at runtime ------------------------
// The declarative pattern: the control property in `diff` binds to a VIRTUAL
// BOOLEAN attribute, and page code flips that attribute. Never reach into the
// DOM to disable a control, and never rebuild diff at runtime.
//
//   diff  ->  "enabled":  { "bindTo": "MyButtonEnabled" }
//             "visible":  { "bindTo": "MyBlockVisible" }
//             "required": { "bindTo": "MyFieldRequired" }
//   code  ->  this.set("MyButtonEnabled", false);
//
// `visible` also accepts a METHOD name; the framework calls it and uses the
// returned value. Base pages expose ready-made ones, e.g. "isAddMode".
//
// For `required` there are three levels, from most to least preferred:
//   1. A business rule of type BINDPARAMETER on the `required` property
//      (see BusinessRules/) - no code at all.
//   2. "required": { "bindTo": "<virtual boolean>" } plus this.set(...).
//   3. this.columns.QSField.isRequired = true - imperative, does not always
//      refresh a control that is already rendered; use only as a last resort.
//
// A field hidden with `visible: false` still takes part in validation. If a
// mandatory field must be skipped in some scenario, clear its required flag too.

define("QSMyEntity1Page", [], function() {

	const StatusInWork = "f6c25e34-63f3-4b6d-9769-db0f37d42f0e";

	return {
		entitySchemaName: "QSMyEntity",
		attributes: {
			"CreateFreightKPButtonEnabled": {
				"dataValueType": Terrasoft.DataValueType.BOOLEAN, "value": false
			},
			"ShipmentInfoVisible": {
				"dataValueType": Terrasoft.DataValueType.BOOLEAN, "value": false
			},
			"QSSellerRequired": {
				"dataValueType": Terrasoft.DataValueType.BOOLEAN, "value": false
			},
			// Host attribute: recompute the flags whenever the driving columns move.
			"FieldRequirementsManager": {
				"dependencies": [
					{ "columns": ["QSStatus", "QSMethodRegistration"], "methodName": "setFieldRequirements" }
				]
			}
		},
		methods: {

			onEntityInitialized: function() {
				this.callParent(arguments);
				this.setFieldRequirements();
			},

			setFieldRequirements: function() {
				var status = this.get("QSStatus");
				var isInWork = !!status && status.value === StatusInWork;

				// Required only after the record reaches the working status.
				this.set("QSSellerRequired", isInWork);

				// Enable the action button under the same condition.
				this.set("CreateFreightKPButtonEnabled", isInWork);
			},

			onToggleShipmentInfoClick: function() {
				this.set("ShipmentInfoVisible", !this.get("ShipmentInfoVisible"));
			}
		},
		diff: /**SCHEMA_DIFF*/[
			{
				// Enabled state driven by a virtual attribute.
				"operation": "merge",
				"name": "CreateFreightKPButton",
				"values": {
					"enabled": { "bindTo": "CreateFreightKPButtonEnabled" }
				}
			},
			{
				// Required state driven by a virtual attribute.
				"operation": "merge",
				"name": "QSSeller",
				"values": {
					"required": { "bindTo": "QSSellerRequired" }
				}
			},
			{
				// Visibility driven by a virtual attribute.
				"operation": "merge",
				"name": "ShipmentInfoTextArea",
				"values": {
					"visible": { "bindTo": "ShipmentInfoVisible" }
				}
			},
			{
				// Visibility driven by a base-page method: shown only while the
				// record is being created.
				"operation": "merge",
				"name": "QSTemplateBlock",
				"values": {
					"visible": { "bindTo": "isAddMode" }
				}
			},
			{
				// Statically disabled control (read-only field).
				"operation": "merge",
				"name": "QSOrganization",
				"values": {
					"enabled": false
				}
			}
		]/**SCHEMA_DIFF*/
	};
});

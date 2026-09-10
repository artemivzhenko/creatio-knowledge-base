// --- Anatomy of a detail schema (GridDetailViewModelSchema) ------------------
// properties.json -> "SchemaType": "GridDetailViewModelSchema"
// Naming: <Something>Detail. The designer generates QSSchema<8-hex>Detail.
//
// A detail is a separate module with its own view model, its own sandbox id and
// its own entity. It renders a grid of records filtered by the master record.
//
// Sections of a detail schema:
//   entitySchemaName  the entity whose rows the grid shows
//   attributes        virtual columns driving the detail UI
//   messages          the sandbox contract with the page (see Messaging/)
//   mixins            ConfigurationGridUtilitiesV2 for inline editing
//   details           nested details, normally empty
//   diff              view modifications: DataGrid, AddRecordButton, toolbar
//   methods           detail logic
//
// Elements you will merge in diff:
//   "DataGrid"                    the grid itself
//   "AddRecordButton"             the plus button
//   "SeparateModeAddRecordButton" the plus button of the expanded mode
//   "DetailWrapperContainer"      the outer container
//
// Base methods worth knowing:
//   this.addRecord()          create a row (override to gate it)
//   this.getGridData()        the loaded rows
//   this.reloadGridData()     re-fetch the rows
//   this.onActiveRowAction()  row button dispatcher, when the grid is editable
//   this.destroyed            true once the detail has been disposed
//
// What a detail CANNOT do: read page columns directly. Everything about the
// master record arrives over the sandbox.
//
// The master filter is configured on the PAGE, in its `details` section
// (detailColumn / masterColumn) - not here. See HowToAddDetailToPage.js.

define("QSMySchemaDetail", ["ProcessModuleUtilities", "ConfigurationEnums",
	"css!QSMySchemaDetailCSS"], function(ProcessModuleUtilities, enums) {

	// Module-level constants shared by the detail logic.
	const SpecialServiceIds = ["daff79a0-c5b3-48b2-84cd-1006dce6c4e7",
		"28313eb4-6c24-4e7b-8da7-d29db64659a0"];
	const OrderProcessedStatus = "e0382e9c-e5ae-4cb8-ae08-5e4ef061830c";

	return {
		entitySchemaName: "QSAdditionalServices",

		details: /**SCHEMA_DETAILS*/{}/**SCHEMA_DETAILS*/,

		messages: {
			"GetColumnsValues":     { mode: Terrasoft.MessageMode.PTP,
									  direction: Terrasoft.MessageDirectionType.PUBLISH },
			"SetDetailButtonState": { mode: Terrasoft.MessageMode.PTP,
									  direction: Terrasoft.MessageDirectionType.SUBSCRIBE }
		},

		attributes: {
			"IsAddButtonVisible": { dataValueType: Terrasoft.DataValueType.BOOLEAN, value: true },
			"IsAddButtonEnabled": { dataValueType: Terrasoft.DataValueType.BOOLEAN, value: true },
			"ButtonBlockMessage": { dataValueType: Terrasoft.DataValueType.TEXT,    value: "" }
		},

		diff: /**SCHEMA_DIFF*/[
			{
				"operation": "merge",
				"name": "AddRecordButton",
				"values": {
					"visible": { "bindTo": "IsAddButtonVisible" },
					"enabled": { "bindTo": "IsAddButtonEnabled" }
				}
			}
		]/**SCHEMA_DIFF*/,

		methods: {

			init: function() {
				this.callParent(arguments);
				// Defer: the page has not finished subscribing yet.
				setTimeout(function() {
					this.sandbox.subscribe("SetDetailButtonState", this.onSetButtonState, this);
				}.bind(this), 50);
			},

			onSetButtonState: function(state) {
				if (this.destroyed) {
					return;
				}
				this.set("IsAddButtonEnabled", !!state.enabled);
				this.set("ButtonBlockMessage", state.message || "");
			},

			addRecord: function() {
				if (!this.get("IsAddButtonEnabled")) {
					this.showInformationDialog(this.get("ButtonBlockMessage"));
					return;
				}
				this.callParent(arguments);
			},

			onDestroy: function() {
				// Clear timers and observers here.
				this.callParent(arguments);
			}
		}
	};
});

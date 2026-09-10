// --- How to debug a Classic UI page (trace column values) --------------------
// There is no dev-friendly state inspector for a Classic UI view model, so the
// practical technique is to override the lifecycle methods that surround the
// save pipeline and dump the columns you care about.
//
// Useful facts:
//   this.columns[name]                - column metadata of the view model.
//   column.dataValueTypeName          - readable type name, when present.
//   column.dataValueType              - numeric Terrasoft.DataValueType.
//   this.get(name)                    - current value; for LOOKUP columns this
//                                       is an object { value, displayValue },
//                                       for scalars it is the raw value.
//   this.changedValues                - map of columns modified since load.
//   this.isNew                        - true while the record is not persisted.
//
// Hook points worth logging, in call order:
//   init                       - view model created, no entity data yet.
//   onEntityInitialized        - entity loaded, all columns readable.
//   validate                   - synchronous validation before save.
//   asyncValidate              - asynchronous validation before save.
//   saveEntity                 - the save request is issued.
//   validateSaveEntityResponse - server answered; response.success tells the
//                                outcome, response.errorInfo carries the error.
//
// Always call this.callParent(arguments) in an override, otherwise the base
// behaviour (and the save) silently stops.

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",
		properties: {
			// Columns to dump on every traced hook.
			columnsToTrack: ["QSStatus", "QSAccount", "QSAmount"]
		},
		methods: {

			validate: function() {
				this._logTrackedColumns("QSMyEntity1Page validate");
				return this.callParent(arguments);
			},

			validateSaveEntityResponse: function(response, callback, scope) {
				this._logTrackedColumns("QSMyEntity1Page validateSaveEntityResponse");
				this.callParent(arguments);
			},

			// Lookup values print as objects; flatten them for readable logs.
			_normalizeValue: function(raw) {
				if (typeof raw === "object" && raw !== null) {
					return "displayValue - " + raw.displayValue + ", value - " + raw.value;
				}
				return String(raw);
			},

			_getDataValueType: function(columnName) {
				const column = this.columns && this.columns[columnName] ? this.columns[columnName] : {};
				return column.dataValueTypeName != null ? column.dataValueTypeName : column.dataValueType;
			},

			_getColumnDebugInfo: function(columnName) {
				return {
					value: this._normalizeValue(this.get(columnName)),
					dataValueType: this._getDataValueType(columnName)
				};
			},

			_logTrackedColumns: function(context) {
				(this.columnsToTrack || []).forEach(function(columnName) {
					const info = this._getColumnDebugInfo(columnName);
					console.log(context + " | " + columnName + " = " + info.value +
						" (type " + info.dataValueType + ")");
				}, this);
			}
		},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});

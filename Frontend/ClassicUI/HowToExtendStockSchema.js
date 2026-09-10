// --- How to extend a stock Creatio schema (replacing schema) -----------------
// SOURCE: _SalesUp_Base/Schemas/SystemNotificationsSchema (the notification
// panel item), _SalesUp_DT_ITSM/Schemas/MailBoxForIncidentRegistrationEditPage,
// _SalesUp_DT_ITSM/Schemas/BaseLookupSection.
//
// A replacing schema carries the SAME NAME as the stock schema and lives in your
// package. Creatio merges it over the original, so:
//   - you do NOT restate entitySchemaName, attributes or diff you are not
//     changing; only the delta belongs in your file
//   - every method you declare OVERRIDES the stock one, so almost all of them
//     must start (or end) with this.callParent(arguments)
//   - your diff is applied on top of the stock view, which is why "merge" and
//     "remove" operate on element names you did not create
//
// FINDING THE NAMES you can target: read the stock schema in the configuration
// designer, or inspect the rendered element ids - they follow
// <SchemaName><ElementName>. Names seen in stock schemas:
//   "GeneralInfoBlock"              mailbox / settings pages
//   "NotificationItemTopContainer"  notification panel item
//   "Header", "ProfileContainer", "Tabs", "ESNTab", "NotesAndFilesTab"
//   "SeparateModeAddRecordButton", "CombinedModeAddRecordButton"
//
// EXTENDING A QUERY. Module schemas that read their own data expose hooks such
// as addColumns(select): call the parent first, then add what you need. This is
// how you get an extra column into a stock list without touching its query.
//
// Ext.callback(callback, scope || this) is the stock way to invoke an optional
// callback argument - it tolerates callback being undefined, so it replaces the
// usual if (Ext.isFunction(callback)) dance.
//
// HIDING rather than removing a stock field is safer: "visible": false keeps the
// element in the view tree, so other stock code that references it by name
// still works, while a "remove" can break a base method that expects it.

define("SystemNotificationsSchema", ["css!SuSystemNotificationsSchemaCss"], function() {
	return {
		methods: {

			// Stock hook: extend the query the base module runs.
			addColumns: function(select) {
				this.callParent(arguments);
				select.addColumn("IsRead");
			},

			// Neutralise a stock behaviour by overriding it with a no-op that
			// still honours the callback contract.
			_serviceMarkNewNotificationAsRead: function(isSkipUpdateCounters, callback, scope) {
				Ext.callback(callback, scope || this);
			},

			onSuIsReadButtonClick: function() {
				this.markItemAsRead();
				this.updateRemindingIsRead(this.onRemindingUpdated, this);
			},

			markItemAsRead: function() {
				this.set("IsRead", true);
			},

			updateRemindingIsRead: function(callback, scope) {
				var update = Ext.create("Terrasoft.UpdateQuery", {
					rootSchemaName: this.entitySchemaName
				});
				// Reuse the base filter set, then narrow to this record.
				this.initUpdateFilters(update);
				update.filters.add("CurrentRecord", Terrasoft.createColumnFilterWithParameter(
					Terrasoft.ComparisonType.EQUAL, "Id", this.get("Id")));
				update.setParameterValue("IsRead", true, Terrasoft.DataValueType.BOOLEAN);

				update.execute(function() {
					this._resetNotificationCounters();
					this.sendResetCountersEvent();
					Ext.callback(callback, scope || this);
				}, this);
			},

			onRemindingUpdated: function() {}
		},

		diff: [
			{
				// Insert into a STOCK container of the stock schema.
				"operation": "insert",
				"name": "SuIsReadButton",
				"parentName": "NotificationItemTopContainer",
				"propertyName": "items",
				"values": {
					"itemType": Terrasoft.ViewItemType.BUTTON,
					"style": Terrasoft.controls.ButtonEnums.style.TRANSPARENT,
					"click": { "bindTo": "onSuIsReadButtonClick" },
					"controlConfig": {
						"imageConfig": { "bindTo": "Resources.Images.SuNotReadIcon" }
					},
					"classes": { "wrapperClass": ["su-right-panel-reminding-wrap"] },
					"hint": { "bindTo": "Resources.Strings.SuMarkAsReadHint" },
					"visible": {
						"bindTo": "IsRead",
						"bindConfig": { converter: function(value) { return !value; } }
					}
				}
			},
			{
				// Prefer hiding a stock field over removing it.
				"operation": "merge",
				"name": "Name",
				"values": {
					"layout": { "colSpan": 12, "column": 0, "row": 10 },
					"visible": false
				}
			}
		]
	};
});

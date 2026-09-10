// --- controlConfig, bindConfig converters, classes and hints -----------------
// SOURCE: _SalesUp_Base/SystemNotificationsSchema, SuRequestPageV2 and
// _SalesUp_DT_ITSM/SuChangeLogCaseSettingPageV2.
//
// `values` in a diff entry has two levels:
//
//   values.<prop>              properties the FRAMEWORK understands
//                              (bindTo, layout, enabled, visible, caption...)
//   values.controlConfig.<prop> properties passed straight to the CONTROL
//                              instance - this is how you reach control-specific
//                              options that have no diff-level equivalent
//
// Useful controlConfig keys seen in production schemas:
//   className          swap the control class entirely, e.g.
//                      "Terrasoft.SuCaseExtendableLookupEdit"
//                      (see Modules/HowToCreateCustomControl.js)
//   imageConfig        image of a button, bound to Resources.Images.<Name>
//   rightIconClasses   CSS classes for the icon on the right of an edit
//   rightIconClick     method bound to the right-icon click
//   cleariconclick     method bound to the clear ("x") icon - note the all
//                      lowercase spelling, it is not camelCase
//   imageLoaded/images rich-text notes image handling; bind to the base methods
//                      insertImagesToNotes and NotesImagesCollection
//
// Diff-level companions:
//   hasClearIcon: true          show the clear icon on an edit
//   labelConfig: {visible:false} hide the field label (full-width notes)
//   classes: { wrapperClass: ["my-class"] }  attach CSS classes; pair it with a
//                               CSS module (Modules/HowToUseCssAndCustom...)
//   hint: { bindTo: "Resources.Strings.<Name>" }  tooltip on a button
//
// CONVERTERS. Classic UI can transform a bound value inline, which is the
// equivalent of a Freedom UI converter:
//
//   "visible": {
//       "bindTo": "IsRead",
//       "bindConfig": { converter: function(value) { return !value; } }
//   }
//
// The converter runs with the view model as `this`, so it can read other
// columns. Keep it pure and cheap - it is called on every change. Anything
// heavier belongs in a virtual attribute recomputed by a dependency.

define("QSMyEntity1Page", ["SuCaseExtendableLookupEdit"], function() {
	return {
		entitySchemaName: "QSMyEntity",
		methods: {
			openColumnExplorer: function() {},
			onMarkAsReadClick: function() {}
		},
		diff: /**SCHEMA_DIFF*/[
			{
				// Field rendered by a CUSTOM control, with right and clear icons.
				"operation": "insert",
				"name": "SuBpmColumnCaption",
				"values": {
					"layout": { "colSpan": 12, "rowSpan": 1, "column": 0, "row": 0, "layoutName": "Header" },
					"bindTo": "SuBpmColumnCaption",
					"hasClearIcon": true,
					"controlConfig": {
						"className": "Terrasoft.SuCaseExtendableLookupEdit",
						"rightIconClasses": ["custom-right-item", "lookup-edit-right-icon"],
						"rightIconClick": { "bindTo": "openColumnExplorer" },
						// Base method of the edit page.
						"cleariconclick": { "bindTo": "clearField" }
					}
				},
				"parentName": "Header",
				"propertyName": "items",
				"index": 0
			},
			{
				// Icon-only button with a hint, custom wrapper class, and a
				// converter that inverts the bound boolean.
				"operation": "insert",
				"name": "SuIsReadButton",
				"parentName": "NotificationItemTopContainer",
				"propertyName": "items",
				"values": {
					"itemType": Terrasoft.ViewItemType.BUTTON,
					"style": Terrasoft.controls.ButtonEnums.style.TRANSPARENT,
					"click": { "bindTo": "onMarkAsReadClick" },
					"controlConfig": {
						"imageConfig": { "bindTo": "Resources.Images.SuNotReadIcon" }
					},
					"classes": {
						"wrapperClass": ["su-right-panel-reminding-wrap"]
					},
					"hint": { "bindTo": "Resources.Strings.SuMarkAsReadHint" },
					// Show the button only while the item is UNREAD.
					"visible": {
						"bindTo": "IsRead",
						"bindConfig": {
							converter: function(value) {
								return !value;
							}
						}
					}
				}
			},
			{
				// Full-width rich text notes with image support.
				"operation": "insert",
				"name": "Notes",
				"values": {
					"bindTo": "SuNotes",
					"dataValueType": 1,   // TEXT
					"contentType": 4,     // RICH_TEXT
					"layout": { "column": 0, "row": 0, "colSpan": 24 },
					"labelConfig": { "visible": false },
					"controlConfig": {
						"imageLoaded": { "bindTo": "insertImagesToNotes" },
						"images": { "bindTo": "NotesImagesCollection" }
					}
				},
				"parentName": "NotesControlGroup",
				"propertyName": "items",
				"index": 0
			}
		]/**SCHEMA_DIFF*/
	};
});

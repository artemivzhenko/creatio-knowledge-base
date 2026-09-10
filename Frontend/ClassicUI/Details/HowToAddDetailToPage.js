// --- How to put a detail on a page -------------------------------------------
// Two coordinated parts are required.
//
// 1. `details` declares the DATA binding:
//
//      "<UniqueDetailKey>": {
//          "schemaName":       "<detail schema name>",       // the .js schema
//          "entitySchemaName": "<entity behind the detail>",
//          "filter": {
//              "detailColumn": "<column on the DETAIL entity pointing to master>",
//              "masterColumn": "Id"                          // column on THIS page
//          }
//      }
//
//    The key is an arbitrary unique id. The designer generates
//    "<SchemaName><8-hex>" so the same detail schema can be placed twice on one
//    page against different entities.
//
// 2. `diff` declares WHERE it is rendered: an insert with itemType 2 (DETAIL).
//    The diff element `name` MUST equal the key used in `details`.
//
// The detail is filtered automatically: detailColumn = masterColumn value. For
// an unsaved master record Id is empty, so the detail shows nothing until the
// first save - that is expected, not a bug.

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",

		details: /**SCHEMA_DETAILS*/{

			// Services of this order.
			"QSSchema2d707869Detailacdf157e": {
				"schemaName": "QSSchema2d707869Detail",
				"entitySchemaName": "QSServicesInOrder",
				"filter": {
					"detailColumn": "QSOrder",
					"masterColumn": "Id"
				}
			},

			// The same schema reused for another entity on the same page.
			"QSSchema8cd6525fDetail9f9a854d": {
				"schemaName": "QSSchema8cd6525fDetail",
				"entitySchemaName": "QSUntilExecution",
				"filter": {
					"detailColumn": "QSOrder",
					"masterColumn": "Id"
				}
			}
		}/**SCHEMA_DETAILS*/,

		diff: /**SCHEMA_DIFF*/[
			{
				// Render the detail inside a tab.
				"operation": "insert",
				"name": "QSSchema2d707869Detailacdf157e",
				"values": {
					"itemType": 2,                 // Terrasoft.ViewItemType.DETAIL
					"markerValue": "added-detail"
				},
				"parentName": "QSLogisticsTab",
				"propertyName": "items",
				"index": 0
			},
			{
				// Rename the detail caption shown on the page. The caption is a
				// resource string named <DetailKey>CaptionOnPage.
				"operation": "merge",
				"name": "QSSchema8cd6525fDetail9f9a854d",
				"values": {
					"caption": { "bindTo": "Resources.Strings.QSSchema8cd6525fDetail9f9a854dCaptionOnPage" }
				}
			},
			{
				// Remove an inherited detail you do not want.
				"operation": "remove",
				"name": "FileDetailV2"
			}
		]/**SCHEMA_DIFF*/
	};
});

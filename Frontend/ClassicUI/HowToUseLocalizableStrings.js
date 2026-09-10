// --- How to use localizable strings and images -------------------------------
// Classic UI does not hardcode captions in diff. It binds them to schema
// resources, which live OUTSIDE the schema folder:
//
//   <Package>/Resources/<SchemaName>.ClientUnit/resource.en-US.xml
//   <Package>/Resources/<SchemaName>.ClientUnit/resource.ru-RU.xml
//   <Package>/Resources/<SchemaName>.ClientUnit/resource.uk-UA.xml
//
// Each file looks like this:
//
//   <Resources Culture="en-US">
//     <Group Type="String">
//       <Items>
//         <Item Name="Caption" Value="Order edit page" />
//         <Item Name="LocalizableStrings.CreateComplexKPButtonCaption.Value"
//               Value="Create complex quote" />
//         <Item Name="LocalizableStrings.QSOwnerTip.Value"
//               Value="Taken from the order" />
//         <Item Name="Images.78654029-8617-4e27-a262-fcbc2f162c1a.Image"
//               Type="Image" Value="&lt;base64 png&gt;" />
//       </Items>
//     </Group>
//   </Resources>
//
// Naming: the XML item is "LocalizableStrings.<Name>.Value" and the schema
// references it as "Resources.Strings.<Name>". Images are "Resources.Images.<Name>".
//
// Two ways to consume a string:
//   1. Declaratively in diff -> { "bindTo": "Resources.Strings.MyCaption" }
//   2. Imperatively in code  -> this.get("Resources.Strings.MyCaption")
//
// Add the same Item to EVERY culture file in the package, otherwise the string
// falls back to the primary culture and shows untranslated text.

define("QSMyEntity1Page", [], function() {
	return {
		entitySchemaName: "QSMyEntity",
		methods: {

			onShowMessageClick: function() {
				// Imperative read of a localizable string.
				var message = this.get("Resources.Strings.NoDataFoundMessage");
				this.showInformationDialog(message);
			}
		},
		diff: /**SCHEMA_DIFF*/[
			{
				"operation": "insert",
				"name": "CreateComplexKPButton",
				"values": {
					"itemType": 5,   // Terrasoft.ViewItemType.BUTTON
					"layout": { "colSpan": 6, "rowSpan": 1, "column": 17, "row": 10, "layoutName": "Header" },
					// Declarative binding to the resource string.
					"caption": { "bindTo": "Resources.Strings.CreateComplexKPButtonCaption" },
					"click":   { "bindTo": "onCreateComplexKPButtonClick" },
					"style":   "green"
				},
				"parentName": "Header",
				"propertyName": "items",
				"index": 26
			},
			{
				// A tip (hint icon next to a field) is a resource string too.
				// The designer names it <Column><guid>Tip.
				"operation": "merge",
				"name": "QSOwner",
				"values": {
					"tip": { "content": { "bindTo": "Resources.Strings.QSOwnerTip" } }
				}
			}
		]/**SCHEMA_DIFF*/
	};
});

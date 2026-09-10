define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		// --- How to lay out a Freedom UI page --------------------------------
		// Freedom UI uses CSS grid and flexbox, not the 24-column grid of
		// Classic UI. Two containers do the work.
		//
		// crt.GridContainer - a CSS grid.
		//   rows      "minmax(max-content, 32px)"  a CSS grid-template-rows value
		//   columns   ["minmax(64px, 1fr)"]        array of column definitions;
		//             the number of entries IS the number of columns
		//   gap       { columnGap, rowGap }        "none" | "extra-small" |
		//                                          "small" | "medium" | "large"
		//   padding   { top, right, bottom, left } same size tokens
		//   color     "primary" | "transparent" | ...
		//   borderRadius  "none" | "medium" | ...
		//   alignItems    "stretch" | "start" | "center" | "end"
		//   items     []                           children
		//
		// crt.FlexContainer - a flex row or column.
		//   direction "column" | "row"
		//   fitContent  true shrinks to content instead of filling the parent
		//
		// CHILD POSITION. Every child of a GridContainer carries its own
		// layoutConfig:
		//   { "column": 1, "row": 1, "colSpan": 1, "rowSpan": 1 }
		// Columns and rows are 1-BASED, unlike the 0-based Classic UI layout.
		// Two children with the same column/row overlap.
		//
		// STOCK CONTAINERS you will merge into rather than create:
		//   CardContentWrapper        the whole card body
		//   SideAreaProfileContainer  the left profile column
		//   MainContainer / Tabs      the main area and the tab panel
		//   CardToolsContainer        the header command area
		//
		// TABS. crt.TabPanel is the panel; each tab is a crt.TabContainer
		// inserted into it with propertyName "items". Inside a tab you normally
		// place another GridContainer and put the fields there.
		//
		// A note on sizes: Freedom UI takes design tokens ("large", "medium"),
		// not pixel values, for gap and padding. Raw CSS lengths belong in
		// rows/columns only.

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[

			// Adjust a stock container instead of replacing it.
			{
				"operation": "merge",
				"name": "CardContentWrapper",
				"values": {
					"padding": { "top": "none", "right": "small", "bottom": "none", "left": "small" },
					"color": "transparent",
					"borderRadius": "none",
					"alignItems": "stretch",
					"visible": true
				}
			},

			// A one-column grid block.
			{
				"operation": "insert",
				"name": "DetailsGridContainer",
				"values": {
					"type": "crt.GridContainer",
					"rows": "minmax(max-content, 32px)",
					"columns": ["minmax(64px, 1fr)"],
					"gap": { "columnGap": "large", "rowGap": "none" },
					"padding": { "top": "medium", "right": "large", "bottom": "medium", "left": "large" },
					"layoutConfig": { "basis": "fit-content" },
					"color": "primary",
					"borderRadius": "medium",
					"alignItems": "stretch",
					"visible": true,
					"items": []
				},
				"parentName": "CardContentWrapper",
				"propertyName": "items",
				"index": 0
			},

			// A two-column grid: two entries in `columns`.
			{
				"operation": "insert",
				"name": "TwoColumnContainer",
				"values": {
					"type": "crt.GridContainer",
					"rows": "minmax(max-content, 32px)",
					"columns": ["minmax(64px, 1fr)", "minmax(64px, 1fr)"],
					"gap": { "columnGap": "large", "rowGap": "small" },
					"alignItems": "stretch",
					"items": []
				},
				"parentName": "DetailsGridContainer",
				"propertyName": "items",
				"index": 0
			},

			// Children pick their cell. Both sit on row 1, in columns 1 and 2.
			{
				"operation": "insert",
				"name": "LeftField",
				"values": {
					"layoutConfig": { "column": 1, "row": 1, "colSpan": 1, "rowSpan": 1 },
					"type": "crt.Input",
					"label": "$Resources.Strings.PDS_Left_a1b2c3d",
					"control": "$PDS_Left_a1b2c3d"
				},
				"parentName": "TwoColumnContainer",
				"propertyName": "items",
				"index": 0
			},
			{
				"operation": "insert",
				"name": "RightField",
				"values": {
					"layoutConfig": { "column": 2, "row": 1, "colSpan": 1, "rowSpan": 1 },
					"type": "crt.Input",
					"label": "$Resources.Strings.PDS_Right_d4e5f6g",
					"control": "$PDS_Right_d4e5f6g"
				},
				"parentName": "TwoColumnContainer",
				"propertyName": "items",
				"index": 1
			},

			// A flex column - stack children without a grid.
			{
				"operation": "insert",
				"name": "ActionsFlexContainer",
				"values": {
					"layoutConfig": { "column": 1, "row": 2, "colSpan": 1, "rowSpan": 1 },
					"type": "crt.FlexContainer",
					"direction": "column",
					"fitContent": true,
					"items": []
				},
				"parentName": "DetailsGridContainer",
				"propertyName": "items",
				"index": 1
			},

			// A collapsible block.
			{
				"operation": "insert",
				"name": "AdditionalInfoPanel",
				"values": {
					"type": "crt.ExpansionPanel",
					"title": "#ResourceString(AdditionalInfoPanel_title)#",
					"toggleType": "default",
					"togglePosition": "before",
					"expanded": true,
					"labelColor": "auto",
					"fullWidthHeader": false,
					"titleWidth": 20,
					"padding": { "top": "small", "right": "none", "bottom": "extra-small", "left": "none" },
					"fitContent": true,
					"alignItems": "stretch",
					"visible": true,
					"tools": [],
					"items": []
				},
				"parentName": "CardContentWrapper",
				"propertyName": "items",
				"index": 1
			},

			// Tab panel and one tab inside it.
			{
				"operation": "merge",
				"name": "Tabs",
				"values": {
					"type": "crt.TabPanel",
					"mode": "tab",
					"styleType": "default",
					"bodyBackgroundColor": "primary-contrast-500",
					"tabTitleColor": "auto",
					"selectedTabTitleColor": "auto",
					"headerBackgroundColor": "auto",
					"underlineSelectedTabColor": "auto",
					"fitContent": true
				}
			},
			{
				"operation": "insert",
				"name": "LogisticsTabContainer",
				"values": {
					"type": "crt.TabContainer",
					"caption": "#ResourceString(LogisticsTabContainer_caption)#",
					"items": []
				},
				"parentName": "Tabs",
				"propertyName": "items",
				"index": 0
			}

		]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,
		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,
		handlers: /**SCHEMA_HANDLERS*/[]/**SCHEMA_HANDLERS*/,
		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});

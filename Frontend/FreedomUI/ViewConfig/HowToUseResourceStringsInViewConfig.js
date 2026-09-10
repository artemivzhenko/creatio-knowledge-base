define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		// --- How to use localizable strings on a Freedom UI page ---------------
		// THREE FORMS, and they are not interchangeable.
		//
		// 1. "#ResourceString(<Key>)#"
		//    Used inside viewConfigDiff for CAPTIONS and TITLES of view elements
		//    - button captions, tab captions, expansion panel titles, grid column
		//    captions. The platform substitutes the string at render time.
		//
		//      "caption": "#ResourceString(ExportButton_caption)#"
		//      "title":   "#ResourceString(ExpansionPanel_7ecjlq7_title)#"
		//
		// 2. "$Resources.Strings.<Key>"
		//    A BINDING to a resource string. This is the form used for the
		//    `label` of an input, because a label participates in the binding
		//    system like any other value.
		//
		//      "label": "$Resources.Strings.PDS_Name_a1b2c3d"
		//
		// 3. await request.$context.Resources.Strings.<Key>
		//    Reading a string from a handler, for a dialog or a message. It is
		//    ASYNCHRONOUS - forgetting the await puts a Promise into the dialog
		//    and the user sees "[object Promise]".
		//
		// WHERE THE STRINGS LIVE. Not in the schema. They are resources of the
		// page schema, edited in the designer, and stored per culture in the
		// package Resources folder. Add every key to every culture the solution
		// ships, otherwise the page falls back to the primary culture.
		//
		// NAMING. The designer generates keys from the element name, so
		// "ExportButton_caption" belongs to the element named "ExportButton".
		// Hand-written keys are fine; keep the element-name prefix so the key is
		// findable from the view config.

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[

			// Form 1: caption of a button.
			{
				"operation": "insert",
				"name": "ExportButton",
				"values": {
					"type": "crt.Button",
					"caption": "#ResourceString(ExportButton_caption)#",
					"iconPosition": "only-text",
					"clicked": { "request": "usr.ExportRequest", "params": {} }
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 0
			},

			// Form 1: title of a collapsible block.
			{
				"operation": "insert",
				"name": "AdditionalInfoPanel",
				"values": {
					"type": "crt.ExpansionPanel",
					"title": "#ResourceString(AdditionalInfoPanel_title)#",
					"expanded": true,
					"items": [],
					"tools": []
				},
				"parentName": "MainContainer",
				"propertyName": "items",
				"index": 1
			},

			// Form 2: label of an input.
			{
				"operation": "insert",
				"name": "NameInput",
				"values": {
					"layoutConfig": { "column": 1, "row": 1, "colSpan": 1, "rowSpan": 1 },
					"type": "crt.Input",
					"label": "$Resources.Strings.PDS_Name_a1b2c3d",
					"labelPosition": "auto",
					"control": "$PDS_Name_a1b2c3d"
				},
				"parentName": "AdditionalInfoPanel",
				"propertyName": "items",
				"index": 0
			}

		]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,
		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		handlers: /**SCHEMA_HANDLERS*/[
			{
				request: "usr.ExportRequest",
				handler: async (request, next) => {

					// Form 3: reading a string in code. The await is required.
					const message = await request.$context.Resources.Strings.ExportStartedMessage;

					await request.$context.executeRequest({
						type: "crt.ShowDialogRequest",
						$context: request.$context,
						message: message,
						actions: [
							{ key: "OK", config: { color: "primary", caption: "OK" } }
						]
					});

					return next?.handle(request);
				}
			}
		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});

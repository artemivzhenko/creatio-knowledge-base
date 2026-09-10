define("MyPage_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {

		// --- How to react to an attribute change with the "change" key --------
		// An attribute can name the request to run whenever its value changes:
		//
		//   "AttributeName": {
		//       "modelConfig": { "path": "PDS.Type" },
		//       "change": { "request": "usr.OnTypeChange" }
		//   }
		//
		// The request is a normal custom request handled in `handlers`. Nothing
		// else is needed - no attributeName check, no dispatch.
		//
		// TWO WAYS TO REACT TO A CHANGE, and they solve different problems:
		//
		//   "change" on the attribute (this file)
		//       One handler per attribute, wired declaratively. The handler runs
		//       ONLY for that attribute, so it needs no filtering and stays
		//       readable. Prefer this whenever you know the attribute up front.
		//
		//   crt.HandleViewModelAttributeChangeRequest
		//       One handler for EVERY attribute of the page; you branch on
		//       request.attributeName. Use it when the reaction is generic - a
		//       dirty-tracker, logging, a rule driven by a list of columns - or
		//       when the attribute set is not known at design time.
		//       See HowToReactToFieldChange.js.
		//
		// Both can coexist on the same page. If both are wired for one attribute,
		// both run - which is usually a mistake, so pick one per attribute.
		//
		// WHAT THE HANDLER RECEIVES. The `change` config observed in this
		// codebase carries only `request`; no params are passed. Read the new
		// value from the context yourself:
		//
		//   const value = await request.$context.AttributeName;
		//
		// Values are read asynchronously - the await is required, and a missing
		// one silently yields a Promise instead of the value.
		//
		// IT ALSO WORKS ON A COLLECTION ATTRIBUTE. Wiring `change` on a grid
		// attribute makes the request fire when the collection changes, which is
		// how a page recalculates totals or re-applies read-only state after the
		// user edits a detail.
		//
		// TWO TRAPS
		//
		// 1. It fires during page LOAD too, while the model is being filled, not
		//    only on user edits. A handler that shows a dialog or writes data
		//    will do so on every open. Guard it - the codebase checks
		//    request.$context.attributes.HasUnsavedData to tell a user edit from
		//    initialisation.
		//
		// 2. Writing another attribute from a change handler triggers THAT
		//    attribute's change handler. Two fields that recalculate each other
		//    loop forever. Write only when the value actually differs, which
		//    breaks the cycle after one pass.

		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[]/**SCHEMA_VIEW_CONFIG_DIFF*/,

		viewModelConfigDiff: /**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/[
			{
				"operation": "merge",
				"path": ["attributes"],
				"values": {

					// Simple case: a lookup drives a virtual flag.
					"TypeField": {
						"modelConfig": { "path": "PDS.Type" },
						"change": { "request": "usr.OnTypeChange" }
					},

					// The flag the handler writes. No `change` here, so writing
					// it does not start another round.
					"IsJobRequired": {},

					// Two numeric fields that recalculate each other.
					"PDS_Amount_jdptfrx": {
						"modelConfig": { "path": "PDS.Amount" },
						"change": { "request": "usr.RecalculateShares" }
					},
					"PDS_FirstShare_n7omdku": {
						"modelConfig": { "path": "PDS.FirstShare" },
						"change": { "request": "usr.RecalculateShares" }
					},
					"PDS_FirstSharePercent_9a5adoy": {
						"modelConfig": { "path": "PDS.FirstSharePercent" },
						"change": { "request": "usr.RecalculateShares" }
					}
				}
			},
			{
				// `change` on a COLLECTION attribute: fires when the grid
				// contents change. Note the path - it merges into one attribute.
				"operation": "merge",
				"path": ["attributes", "GridDetail_4ye8sy6"],
				"values": {
					"change": { "request": "usr.OnDetailRowsChanged" }
				}
			}
		]/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/,

		modelConfigDiff: /**SCHEMA_MODEL_CONFIG_DIFF*/[]/**SCHEMA_MODEL_CONFIG_DIFF*/,

		handlers: /**SCHEMA_HANDLERS*/[

			// Straightforward: read the new value, set a flag.
			{
				request: "usr.OnTypeChange",
				handler: async (request, next) => {
					const typeField = await request.$context.TypeField;
					const typeId = typeField?.value;

					const typesRequiringJob = [
						"00783ef6-f36b-1410-a883-16d83cab0980",
						"60733efc-f36b-1410-a883-16d83cab0980"
					];
					request.$context.IsJobRequired = typesRequiringJob.includes(typeId);

					return next?.handle(request);
				}
			},

			// Mutually dependent fields - both guards applied.
			{
				request: "usr.RecalculateShares",
				handler: async (request, next) => {

					// GUARD 1: skip the initial load, react to user edits only.
					if (!request.$context.attributes.HasUnsavedData) {
						return next?.handle(request);
					}

					const AMOUNT  = "PDS_Amount_jdptfrx";
					const SHARE   = "PDS_FirstShare_n7omdku";
					const PERCENT = "PDS_FirstSharePercent_9a5adoy";

					const toNumber = (v) =>
						(v !== null && v !== undefined && v !== "" && !isNaN(+v)) ? +v : null;

					// GUARD 2: write only when the value really changes, so the
					// paired handler does not bounce the change back.
					const setIfChanged = (attributeName, currentValue, newValue) => {
						if (currentValue !== newValue) {
							request.$context[attributeName] = newValue;
						}
					};

					const amount  = toNumber(await request.$context[AMOUNT]);
					const share   = toNumber(await request.$context[SHARE]);
					const percent = toNumber(await request.$context[PERCENT]);

					if (amount === null || amount === 0) {
						return next?.handle(request);
					}

					// Negative input: normalise and stop this pass.
					if (share !== null && share < 0) {
						request.$context[SHARE] = 0;
						return next?.handle(request);
					}

					if (share !== null) {
						const computed = parseFloat(((share / amount) * 100).toFixed(2));
						setIfChanged(PERCENT, percent, computed);
					}

					return next?.handle(request);
				}
			},

			// Collection change: recalculate a total from the grid rows.
			{
				request: "usr.OnDetailRowsChanged",
				handler: async (request, next) => {
					const rows = await request.$context.GridDetail_4ye8sy6;

					const total = (rows || []).reduce(
						(sum, row) => sum + (row.GridDetail_4ye8sy6DS_Amount || 0), 0);

					if (await request.$context.PDS_Total_x1y2z3 !== total) {
						request.$context.PDS_Total_x1y2z3 = total;
					}
					return next?.handle(request);
				}
			}

		]/**SCHEMA_HANDLERS*/,

		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/

	};
});

// --- How to disable or remove a business rule the parent page declares --------
// A rule of a platform page (or of another package's page) lives in THAT
// schema's body; editing it there is not possible - the schema is installed
// from its package, and a change to it is lost or blocks the next update. The
// way is a REPLACING schema of the page in your package that overrides the rule
// BY ITS UId under the same column in `businessRules`:
//
//   "enabled": false   the rule stays in the chain but no longer runs
//   "removed": true    the rule is dropped from the merged page
//
// The merge works on the keys: column -> rule key -> properties, so the override
// must sit under the same column name and the same rule key as the parent's
// (the key is the rule's UId for designer rules). A different column or a typo in
// the key adds a new, empty rule and the parent's one keeps running - no error.
// Read the parent's businessRules first (clio get-page / pull, or the schema in
// the configuration), copy the rule key, then override.
//
// Before relying on it, check which copies of the page the environment applies:
// a replacing copy in the Custom package is applied LAST and overrides yours
// (describe.py layers <Page> -e <env>).
//
// Package files: `python classicui.py replace <pkg> <Page> --parent-uid <uid>`
// creates the replacing schema; `python classicui.py set-rule <pkg> <Page> <UId>
// --enabled false --column <Column>` writes the override (no-code/tools).
//
// Old-style `rules` (keyed by a readable rule name, not by UId) are overridden
// the same way under `rules`, by that name.

define("ContactPageV2", [], function() {
	// The UId of the parent's rule, read off the parent schema - invented here.
	return {
		entitySchemaName: "Contact",
		businessRules: /**SCHEMA_BUSINESS_RULES*/{
			"Owner": {
				// Disabled: still declared, does not run.
				"0b7c2c9e-4c1d-4b8e-9f3a-1d2e3f4a5b6c": {
					"uId": "0b7c2c9e-4c1d-4b8e-9f3a-1d2e3f4a5b6c",
					"enabled": false
				}
			},
			"Account": {
				// Removed from the merged page.
				"5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b": {
					"uId": "5e6f7a8b-9c0d-4e1f-8a2b-3c4d5e6f7a8b",
					"enabled": true,
					"removed": true
				}
			}
		}/**SCHEMA_BUSINESS_RULES*/,
		methods: {},
		diff: /**SCHEMA_DIFF*/[]/**SCHEMA_DIFF*/
	};
});

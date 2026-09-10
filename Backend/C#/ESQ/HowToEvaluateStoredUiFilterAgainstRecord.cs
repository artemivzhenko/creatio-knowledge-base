using System;
using System.Collections.Generic;
using Newtonsoft.Json;
using Terrasoft.Common;
using Terrasoft.Core;
using Terrasoft.Core.DB;
using Terrasoft.Core.Entities;

/// <summary>
/// Demonstrates how to take a filter that was BUILT IN THE UI and stored as JSON, and decide
/// on the backend whether a given record matches it.
///
/// THE USE CASE. A configuration record holds "which records does this rule apply to?" as a
/// filter the business user composed in the filter designer. The backend then has to pick the
/// matching rule for a record — for example choosing the right conversation script for a call,
/// or the right SLA for a case. Reimplementing the filter in C# is not an option: the user can
/// change it at any time.
///
/// THE TECHNIQUE. The stored JSON is the same contract the frontend sends, so it deserialises
/// into Terrasoft.Nui.ServiceModel.DataContract.Filters. Wrap it in a SelectQuery, call
/// BuildEsq(userConnection), then add one more condition restricting the query to the single
/// record you are testing. If the query returns a row, the record matches.
///
/// WHY THE WRAPPER GROUP. The stored value is one filter group; SelectQuery expects a root
/// group whose Items hold the filters. Deserialising straight into SelectQuery.Filters loses
/// the grouping, so build an empty root group with LogicalOperation = And and add the
/// deserialised object as its single item.
///
/// PERFORMANCE. This is one database round trip per record per rule. Testing many records
/// against many rules this way is slow — fetch the candidate rules once, and keep the
/// per-record loop as short as you can. RowCount = 1 is important: you only need existence.
///
/// SECURITY. Set UseAdminRights = false so the evaluation sees what the user sees; otherwise a
/// rule can match on a record the caller has no access to. See HowToControlAdminRights.
///
/// UseLocalization = true makes localised columns resolve in the current culture, which matters
/// when the stored filter compares against a localised text column.
/// </summary>
namespace Terrasoft.Configuration
{

	public class UsrRuleMatcher
	{

		protected UserConnection UserConnection;

		public UsrRuleMatcher(UserConnection userConnection) {
			UserConnection = userConnection;
		}

		/// <summary>
		/// Does <paramref name="entity"/> satisfy the serialised filter?
		/// </summary>
		/// <param name="filters">The filter JSON as stored by the filter designer.</param>
		protected virtual bool SuitsByFilters(Entity entity, string filters) {

			// No filter configured means "applies to everything".
			if (string.IsNullOrEmpty(filters)) {
				return true;
			}

			// 1. Build the root group the SelectQuery contract expects.
			var deserializedFilters = new Terrasoft.Nui.ServiceModel.DataContract.Filters {
				Key = Guid.NewGuid().ToString(),
				FilterType = Terrasoft.Nui.ServiceModel.DataContract.FilterType.FilterGroup,
				IsEnabled = true,
				LogicalOperation = LogicalOperationStrict.And,
				Items = new Dictionary<string, Terrasoft.Nui.ServiceModel.DataContract.Filter>()
			};

			// 2. Put the stored filter inside it.
			deserializedFilters.Items.Add(
				deserializedFilters.Key,
				JsonConvert.DeserializeObject<Terrasoft.Nui.ServiceModel.DataContract.Filters>(filters));

			// 3. Turn the contract into a real ESQ.
			var select = new Terrasoft.Nui.ServiceModel.DataContract.SelectQuery {
				RootSchemaName = entity.SchemaName,
				Filters = deserializedFilters
			};
			var esq = select.BuildEsq(UserConnection);

			esq.UseAdminRights = false;
			esq.UseLocalization = true;
			// Existence check only.
			esq.RowCount = 1;
			esq.PrimaryQueryColumn.IsAlwaysSelect = true;

			// 4. Narrow it to the one record under test.
			esq.Filters.Add(esq.CreateFilterWithParameters(
				FilterComparisonType.Equal, "Id", entity.PrimaryColumnValue));

			var entityCollection = esq.GetEntityCollection(UserConnection);
			return entityCollection != null && entityCollection.Count > 0;
		}

		/// <summary>
		/// Typical caller: fetch the rules once, then test the record against each in order.
		/// </summary>
		public virtual Guid FindMatchingRule(Entity entity) {
			var esq = new EntitySchemaQuery(UserConnection.EntitySchemaManager, "UsrConversationScript") {
				UseAdminRights = false
			};
			esq.AddColumn("Id");
			esq.AddColumn("UsrFilters");
			esq.AddColumn("UsrPosition");
			esq.AddOrderByAsc("UsrPosition");

			var rules = esq.GetEntityCollection(UserConnection);
			foreach (var rule in rules) {
				if (SuitsByFilters(entity, rule.GetTypedColumnValue<string>("UsrFilters"))) {
					return rule.GetTypedColumnValue<Guid>("Id");
				}
			}
			return Guid.Empty;
		}

		/// <summary>
		/// Writing the result back WITHOUT raising entity events - useful when this runs
		/// inside a listener for the same entity and a normal Save would re-enter it.
		/// See Events/HowToPreventEventListenerRecursion.
		/// </summary>
		protected virtual void SaveSilent(Entity entity, Guid ruleId) {
			new Update(UserConnection, entity.SchemaName)
				.Set("UsrConversationScriptId", Column.Parameter(ruleId))
				.Where("Id").IsEqual(Column.Parameter(entity.PrimaryColumnValue))
			.Execute();
		}
	}
}

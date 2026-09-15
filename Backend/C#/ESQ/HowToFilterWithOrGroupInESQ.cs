using System;
using Terrasoft.Common;
using Terrasoft.Core;
using Terrasoft.Core.Entities;

/// <summary>
/// Demonstrates how to build OR filter groups in ESQ.
/// By default, every call to esq.Filters.Add() combines conditions with AND.
/// To combine conditions with OR, create an EntitySchemaQueryFilterCollection with
/// LogicalOperationStrict.Or and add your filters into that group.
/// Groups can be nested to express any boolean logic: (A OR B) AND (C OR D).
/// </summary>
class HowToFilterWithOrGroupInESQ {

    // 1. Simple OR: records where StatusId = A OR StatusId = B
    public EntityCollection FilterWithOr(UserConnection userConnection, Guid statusAId, Guid statusBId) {
        var esq = new EntitySchemaQuery(userConnection.EntitySchemaManager, "Activity");
        esq.AddColumn("Title");
        esq.PrimaryQueryColumn.IsAlwaysSelect = true;

        // All filters inside this group are combined with OR
        var orGroup = new EntitySchemaQueryFilterCollection(esq, LogicalOperationStrict.Or);
        orGroup.Add(esq.CreateFilterWithParameters(FilterComparisonType.Equal, "StatusId", statusAId));
        orGroup.Add(esq.CreateFilterWithParameters(FilterComparisonType.Equal, "StatusId", statusBId));

        // The OR group itself is added to the root AND collection
        esq.Filters.Add(orGroup);

        return esq.GetEntityCollection(userConnection);
    }

    // 2. Mixed AND + OR: (StatusId = A OR StatusId = B) AND CreatedOn > N days ago
    public EntityCollection FilterMixed(UserConnection userConnection, Guid statusAId, Guid statusBId, int daysBack) {
        var esq = new EntitySchemaQuery(userConnection.EntitySchemaManager, "Activity");
        esq.AddColumn("Title");
        esq.PrimaryQueryColumn.IsAlwaysSelect = true;

        // AND condition — added directly to root (default AND collection)
        esq.Filters.Add(esq.CreateFilterWithParameters(
            FilterComparisonType.Greater, "CreatedOn", DateTime.UtcNow.AddDays(-daysBack)));

        // OR group for two status values
        var statusOrGroup = new EntitySchemaQueryFilterCollection(esq, LogicalOperationStrict.Or);
        statusOrGroup.Add(esq.CreateFilterWithParameters(FilterComparisonType.Equal, "StatusId", statusAId));
        statusOrGroup.Add(esq.CreateFilterWithParameters(FilterComparisonType.Equal, "StatusId", statusBId));
        esq.Filters.Add(statusOrGroup);

        // Resulting SQL: WHERE CreatedOn > @date AND (StatusId = @a OR StatusId = @b)
        return esq.GetEntityCollection(userConnection);
    }
}

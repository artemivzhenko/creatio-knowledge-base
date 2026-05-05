using System;
using System.Collections.Generic;
using Terrasoft.Core;
using Terrasoft.Core.Entities;

/// <summary>
/// Demonstrates how to iterate over large result sets using EntitySchemaQueryOptions
/// with PageableSelectDirection.
/// Use this approach instead of RowCount + SkipRowCount when processing hundreds of thousands
/// of records in batches — it uses an internal server-side cursor and avoids the growing
/// OFFSET cost of offset-based paging.
/// Pattern:
///   1. Start with PageableDirection = First.
///   2. After each batch, switch to Next and advance RowsOffset by the batch size.
///   3. Call esq.ResetSelectQuery() before re-executing to clear the cached query.
///   4. Stop when the returned batch is smaller than the page size.
/// </summary>
class HowToPaginateWithEntitySchemaQueryOptions {

    // Process all Contact records in batches of 5000 without loading everything into memory
    public void ProcessAllRecordsInBatches(UserConnection userConnection) {
        const int batchSize = 5000;

        var esq = new EntitySchemaQuery(userConnection.EntitySchemaManager, "Contact");
        esq.AddColumn("Name");
        esq.AddColumn("Email");
        esq.PrimaryQueryColumn.IsAlwaysSelect = true;

        // Optional: add filters before iterating
        esq.Filters.Add(esq.CreateFilterWithParameters(
            FilterComparisonType.Equal, "IsActive", true));

        var options = new EntitySchemaQueryOptions {
            PageableDirection       = PageableSelectDirection.First,
            PageableConditionValues = new Dictionary<string, object>(),
            PageableRowCount        = batchSize,
            RowsOffset              = 0
        };

        EntityCollection batch;
        do {
            batch = esq.GetEntityCollection(userConnection, options);

            foreach (var entity in batch) {
                var name  = entity.GetTypedColumnValue<string>("Name");
                var email = entity.GetTypedColumnValue<string>("Email");
                // custom logic per record
            }

            // Advance the cursor to the next page
            options.PageableDirection = PageableSelectDirection.Next;
            options.RowsOffset += batch.Count;

            // Required: clears the internally cached SELECT before the next execution
            esq.ResetSelectQuery();

        } while (batch.Count == batchSize); // stop when the last batch is a partial page
    }

    // Collect all Ids from a large table into a list using the same pattern
    public List<Guid> GetAllIds(UserConnection userConnection, string schemaName) {
        const int batchSize = 5000;

        var esq = new EntitySchemaQuery(userConnection.EntitySchemaManager, schemaName);
        esq.PrimaryQueryColumn.IsAlwaysSelect = true;

        var options = new EntitySchemaQueryOptions {
            PageableDirection       = PageableSelectDirection.First,
            PageableConditionValues = new Dictionary<string, object>(),
            PageableRowCount        = batchSize,
            RowsOffset              = 0
        };

        var allIds = new List<Guid>();
        EntityCollection batch;

        do {
            batch = esq.GetEntityCollection(userConnection, options);
            foreach (var entity in batch) {
                allIds.Add(entity.GetTypedColumnValue<Guid>("Id"));
            }
            options.PageableDirection = PageableSelectDirection.Next;
            options.RowsOffset += batch.Count;
            esq.ResetSelectQuery();
        } while (batch.Count == batchSize);

        return allIds;
    }
}

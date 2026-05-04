using System;
using Terrasoft.Core;
using Terrasoft.Core.Entities;

/// <summary>
/// Demonstrates how to query records using EntitySchemaQuery (ESQ).
/// ESQ is the primary way to read records in Creatio — it respects column and row-level permissions.
/// Use FetchFromDB instead when you need a single record by a known key or column value.
/// </summary>
class HowToReadRecordsWithESQ {

    // 1. Read a collection of records with filters
    public void ReadCollection(UserConnection userConnection, Guid filterId) {
        var esq = new EntitySchemaQuery(userConnection.EntitySchemaManager, "Contact");

        // Select only the columns you need — reduces DB load
        esq.AddColumn("Name");
        esq.AddColumn("Email");

        // Always select Id explicitly if you need it; IsAlwaysSelect guarantees
        // it is included even when AddAllSchemaColumns() is not used
        esq.AddColumn("Id");
        esq.PrimaryQueryColumn.IsAlwaysSelect = true;

        // Limit the number of records loaded per DB round-trip (default is no limit)
        esq.ChunkSize = 5000;

        // --- Filter examples (add as many as needed — combined with AND by default) ---

        // Filter by Guid
        esq.Filters.Add(esq.CreateFilterWithParameters(
            FilterComparisonType.Equal, "CountryId", filterId));

        // Filter by date range
        esq.Filters.Add(esq.CreateFilterWithParameters(
            FilterComparisonType.Greater, "CreatedOn", DateTime.UtcNow.AddDays(-30)));

        // Filter by string
        esq.Filters.Add(esq.CreateFilterWithParameters(
            FilterComparisonType.Equal, "Email", "john.doe@example.com"));

        EntityCollection entities = esq.GetEntityCollection(userConnection);

        foreach (var entity in entities) {
            var name  = entity.GetTypedColumnValue<string>("Name");
            var email = entity.GetTypedColumnValue<string>("Email");
            var id    = entity.GetTypedColumnValue<Guid>("Id");

            // custom logic
        }
    }

    // 2. Read a single record — take the first match from the collection
    public void ReadSingleRecord(UserConnection userConnection, Guid recordId) {
        var esq = new EntitySchemaQuery(userConnection.EntitySchemaManager, "Contact");

        esq.AddColumn("Name");
        esq.AddColumn("Email");
        esq.PrimaryQueryColumn.IsAlwaysSelect = true;

        esq.Filters.Add(esq.CreateFilterWithParameters(
            FilterComparisonType.Equal, "Id", recordId));

        EntityCollection entities = esq.GetEntityCollection(userConnection);

        if (entities.Count == 0) {
            // Record not found — handle accordingly
            return;
        }

        var entity = entities[0];
        var name   = entity.GetTypedColumnValue<string>("Name");
        var email  = entity.GetTypedColumnValue<string>("Email");
    }
}

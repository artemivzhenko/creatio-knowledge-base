using System;
using Terrasoft.Core;
using Terrasoft.Core.Entities;

/// <summary>
/// Demonstrates how to create a new record in any Creatio entity using the Entity model.
/// Use this approach when you need to insert a single record from server-side C# code
/// (business process, web service, event handler, etc.).
/// Does NOT use ESQ for querying — ESQ is only used here to get the entity schema.
/// </summary>
class HowToCreateRecordViaESQ {

    public bool CreateRecord(UserConnection userConnection) {
        // Get the entity schema by object name (the name in Creatio, not the DB table name)
        var schema = userConnection.EntitySchemaManager.GetInstanceByName("MyEntity");
        var entity = schema.CreateEntity(userConnection);

        // Fills system columns with default values (Id, CreatedOn, CreatedById, etc.)
        // Always call this before setting your own values
        entity.SetDefColumnValues();

        // Override the auto-generated Id if you need a known Guid upfront (optional)
        entity.SetColumnValue("Id", Guid.NewGuid());

        // --- String field ---
        entity.SetColumnValue("Name", "Some text value");

        // --- DateTime field ---
        entity.SetColumnValue("StartDate", DateTime.UtcNow);

        // --- Integer field ---
        entity.SetColumnValue("SortOrder", 10);

        // --- Decimal field ---
        entity.SetColumnValue("Amount", 99.99m);

        // --- Boolean field ---
        entity.SetColumnValue("IsActive", true);

        // --- Lookup field (pass the Guid of the related record) ---
        var relatedRecordId = Guid.Parse("00000000-0000-0000-0000-000000000000");
        entity.SetColumnValue("ContactId", relatedRecordId);

        // Save to DB; returns true on success, false on failure
        bool saveResult = entity.Save();

        if (!saveResult) {
            // Handle failure: log, throw, or return false to the caller
        }

        return saveResult;
    }
}
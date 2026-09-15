using System;
using Terrasoft.Core;
using Terrasoft.Core.Entities;

/// <summary>
/// Demonstrates how to update records using EntitySchemaQuery (ESQ).
/// The pattern: query → loop → SetColumnValue → Save.
/// Each Save() triggers entity event handlers (Saving, Saved) and business processes —
/// use the Insert/Update query builder from SQLClasses if you need to bypass them.
/// </summary>
class HowToUpdateRecordWithESQ {

    public int UpdateRecentRecords(UserConnection userConnection, int daysBack, string newValue) {
        var esq = new EntitySchemaQuery(userConnection.EntitySchemaManager, "MyEntity");

        // AddAllSchemaColumns is mandatory when you plan to call Save() on entities —
        // saving with only partial columns will NULL out every unselected field
        esq.AddAllSchemaColumns();

        // Filter: only records created within the last X days
        esq.Filters.Add(esq.CreateFilterWithParameters(
            FilterComparisonType.Greater, "CreatedOn", DateTime.UtcNow.AddDays(-daysBack)));

        EntityCollection entities = esq.GetEntityCollection(userConnection);

        int updatedCount = 0;

        foreach (Entity entity in entities) {
            // --- Set the fields you want to change ---
            entity.SetColumnValue("MyField1", newValue);
            entity.SetColumnValue("ModifiedOn", DateTime.UtcNow);
            entity.SetColumnValue("ModifiedById", userConnection.CurrentUser.Id);

            // Save to DB; returns true on success, false on failure
            bool saveResult = entity.Save();

            if (!saveResult) {
                // Handle failure: log, throw, or continue to next record
            }
            else {
                updatedCount++;
            }
        }

        return updatedCount;
    }
}

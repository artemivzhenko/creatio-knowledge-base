using System;
using Terrasoft.Core;
using Terrasoft.Core.Entities;

/// <summary>
/// Demonstrates how to attach a file (binary data) to an existing record using the Entity model.
/// Use this approach when uploading files to entities that have a file detail
/// (e.g. LeadFile, ContactFile, AccountFile, etc.).
/// The file entity must have the standard columns: Name, Data, Size, TypeId, and the parent FK.
/// </summary>
class HowToCreateFileRecordViaESQ {

    public bool CreateFile(UserConnection userConnection, string fileName, byte[] fileBytes, Guid parentRecordId) {
        var schema = userConnection.EntitySchemaManager.GetInstanceByName("LeadFile");
        var fileEntity = schema.CreateEntity(userConnection);

        // Fills system columns with default values (Id, CreatedOn, CreatedById, etc.)
        // Always call this before setting your own values
        fileEntity.SetDefColumnValues();

        // Override the auto-generated Id if you need a known Guid upfront (optional)
        fileEntity.SetColumnValue("Id", Guid.NewGuid());

        // --- File-specific columns ---
        fileEntity.SetColumnValue("Name", fileName);
        fileEntity.SetColumnValue("Data", fileBytes);
        fileEntity.SetColumnValue("Size", fileBytes.Length);

        // TypeId: hardcoded Guid for the default "File" type from the FileType lookup
        fileEntity.SetColumnValue("TypeId", new Guid("529bc2f8-0ee0-df11-971b-001d60e938c6"));

        // --- Parent record FK (the record this file is attached to) ---
        fileEntity.SetColumnValue("LeadId", parentRecordId);

        // Save to DB; returns true on success, false on failure
        bool saveResult = fileEntity.Save();

        if (!saveResult) {
            // Handle failure: log, throw, or return false to the caller
        }

        return saveResult;
    }
}

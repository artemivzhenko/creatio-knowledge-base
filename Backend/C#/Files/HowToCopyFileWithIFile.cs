using System;
using Terrasoft.Core;
using Terrasoft.File;
using Terrasoft.File.Abstractions;

/// <summary>
/// Demonstrates how to copy a file from one entity record to another using IFile.Copy().
/// Use this when you need to duplicate an attachment across different entity types
/// (e.g. copy a file from LeadFile to ContactFile when a lead is qualified).
/// The copy operation transfers binary content — the source file is not modified.
/// SetAttribute() links the new file entity to its parent record before saving.
/// The file entity must be saved (Save()) before Copy() is called —
/// Copy() transfers the binary content into the already-created entity row.
/// </summary>
class HowToCopyFileWithIFile {

    // Copy a single file from one entity to another
    public bool CopyFile(UserConnection userConnection,
        string sourceSchemaName, Guid sourceFileId,
        string targetSchemaName, string targetParentColumnName, Guid targetParentId) {

        // 1. Resolve the source file
        var sourceLocator = new EntityFileLocator(sourceSchemaName, sourceFileId);
        IFile sourceFile = userConnection.GetFile(sourceLocator);

        // 2. Create a new file entity in the target schema
        Guid newFileId = Guid.NewGuid();
        var targetLocator = new EntityFileLocator(targetSchemaName, newFileId);
        IFile targetFile = userConnection.CreateFile(targetLocator);

        // 3. Copy metadata from the source
        targetFile.Name = sourceFile.Name;

        // 4. Set the FK column that links the file to its parent record
        //    e.g. "LeadId", "ContactId", "AccountId" — must match the file detail column name
        targetFile.SetAttribute(targetParentColumnName, targetParentId);

        // 5. Save the file entity row (creates the DB record without binary content yet)
        try {
            targetFile.Save();
        }
        catch (Exception ex) {
            // File entity row could not be saved — abort before attempting binary copy
            return false;
        }

        // 6. Copy the binary content from source into the saved target entity
        try {
            sourceFile.Copy(targetFile);
        }
        catch (Exception ex) {
            // Binary copy failed — the entity row exists but has no content; handle as needed
            return false;
        }

        return true;
    }

    // Copy all files from a list to the same target record
    public void CopyFiles(UserConnection userConnection,
        string sourceSchemaName, System.Collections.Generic.List<Guid> fileIds,
        string targetSchemaName, string targetParentColumnName, Guid targetParentId) {

        foreach (Guid fileId in fileIds) {
            CopyFile(userConnection,
                sourceSchemaName, fileId,
                targetSchemaName, targetParentColumnName, targetParentId);
        }
    }
}

using System;
using System.Collections.Generic;
using Terrasoft.Core;
using Terrasoft.File;
using Terrasoft.File.Abstractions;

/// <summary>
/// Demonstrates how to move a file between entities and how to delete it, using IFile.
/// Use this when an attachment has to follow a record through a conversion — a file on a
/// Lead moving to the Contact it qualified into — or when a file must be removed for real.
///
/// MOVE DOES NOT REMOVE THE SOURCE. IFile.Move() transfers content and metadata into the
/// target and updates the source row in place; the source record survives, now empty. A
/// "move" that skips the final Delete() leaves a stray attachment on the old record,
/// which is the trap this recipe exists for.
///
/// The target must be Save()d BEFORE Move() — Move() needs an existing row to move into,
/// the same rule that governs Write() and Copy() across the whole File API.
///
/// MOVE VS COPY. Move relocates and empties the source; Copy duplicates and leaves the
/// source intact (HowToCopyFileWithIFile). Pick Copy when the original must remain
/// readable — an audit trail, a document referenced from somewhere else.
///
/// Delete() removes the entity row AND the stored binary content, in whichever storage
/// holds it. It is not a soft delete and there is no undo: a custom storage's DeleteAsync
/// runs too (see HowToImplementCustomFileStorage). Check access rights before calling it
/// on data the current user did not upload — see HowToControlAdminRights.
/// </summary>
class HowToMoveAndDeleteFileWithIFile {

    // Move a file to another entity schema, leaving nothing behind on the source
    public Guid MoveFile(UserConnection userConnection,
        string sourceSchemaName, Guid sourceFileId,
        string targetSchemaName, string targetParentColumnName, Guid targetParentId) {

        // 1. Resolve the source file
        var sourceLocator = new EntityFileLocator(sourceSchemaName, sourceFileId);
        IFile sourceFile = userConnection.GetFile(sourceLocator);

        // 2. Create the destination row — empty for now
        Guid targetFileId = Guid.NewGuid();
        var targetLocator = new EntityFileLocator(targetSchemaName, targetFileId);
        IFile targetFile = userConnection.CreateFile(targetLocator);

        // 3. Carry the name over and link the file to its new parent record
        targetFile.Name = sourceFile.Name;
        targetFile.SetAttribute(targetParentColumnName, targetParentId);

        // 4. Save before moving — Move() writes into an existing row
        targetFile.Save();

        // 5. Move content and metadata across; the source row is updated in place
        sourceFile.Move(targetFile);

        // 6. Remove the now-empty source row — skip this and the old record keeps a
        //    contentless attachment
        sourceFile.Delete();

        return targetFileId;
    }

    // Delete a file record together with its stored content
    public void DeleteFile(UserConnection userConnection, string schemaName, Guid fileId) {
        var locator = new EntityFileLocator(schemaName, fileId);
        IFile file = userConnection.GetFile(locator);

        // Removes both the entity row and the binary content — no undo
        file.Delete();
    }

    // Delete several files, isolating failures so one bad row does not stop the rest
    public void DeleteFiles(UserConnection userConnection, string schemaName, List<Guid> fileIds) {
        foreach (Guid fileId in fileIds) {
            try {
                DeleteFile(userConnection, schemaName, fileId);
            }
            catch (Exception) {
                // Already deleted, or the storage rejected it — log and continue
                // (see HowToLogWithTelemetry)
            }
        }
    }
}

using System;
using System.IO;
using Terrasoft.Core;
using Terrasoft.File;
using Terrasoft.File.Abstractions;

/// <summary>
/// Demonstrates how to create a file record and write its binary content using IFile.
/// Use this to attach a file to a record from code — an integration that receives a
/// document, a report generated on the server, a file rebuilt from another system.
///
/// IFile is storage-agnostic: the same code works whether the binaries live in the
/// database or in a custom store (see HowToImplementCustomFileStorage), because the
/// storage is resolved from configuration rather than named here.
///
/// THE ORDER MATTERS. Metadata first, content second:
///   CreateFile() -> Name -> SetAttribute() -> Save() -> Write()
/// Write() streams bytes into an existing row, so calling it before Save() has nothing
/// to write into. This is the same rule IFile.Copy() follows in HowToCopyFileWithIFile.
///
/// Name must be set before Save() — the platform throws NullOrEmptyException without it.
/// The name is what the user sees in the attachment list; it is not a path.
///
/// SetAttribute() takes the FK COLUMN NAME of the file schema, not the parent schema:
/// "ActivityId" on ActivityFile, "LeadId" on LeadFile. Get it wrong and the row saves
/// cleanly but the file appears on no record — a silent failure, the expensive kind.
///
/// FileWriteOptions.SinglePart sends the whole stream in one call. Use it for files you
/// hold in memory; a chunked write is what the UI uploader does for large files, and a
/// custom storage has to handle both (see the append trap in HowToImplementCustomFileStorage).
/// </summary>
class HowToCreateAndWriteFileWithIFile {

    // Create a file record under a parent record and write its content
    public Guid CreateAndWriteFile(UserConnection userConnection,
        string schemaName, Guid parentRecordId, string parentColumnName,
        string fileName, byte[] content) {

        // 1. The file record Id is generated here, not by the platform — keep it if the
        //    caller needs to reference the file later
        Guid fileRecordId = Guid.NewGuid();

        // 2. The locator identifies a file by its schema and record Id
        //    e.g. ("ActivityFile", fileRecordId)
        var fileLocator = new EntityFileLocator(schemaName, fileRecordId);

        // 3. Create the file entity — this writes nothing yet
        IFile file = userConnection.CreateFile(fileLocator);

        // 4. Display name — required, throws NullOrEmptyException if missing
        file.Name = fileName;

        // 5. Link the file to its parent record through the FK column of the FILE schema
        file.SetAttribute(parentColumnName, parentRecordId);

        // 6. Persist the metadata row
        file.Save();

        // 7. Write the binary content into the saved row
        using (var stream = new MemoryStream(content)) {
            file.Write(stream, FileWriteOptions.SinglePart);
        }

        return fileRecordId;
    }

    // Write content read from disk, streaming instead of buffering the whole file
    public Guid CreateAndWriteFileFromPath(UserConnection userConnection,
        string schemaName, Guid parentRecordId, string parentColumnName,
        string sourcePath) {

        Guid fileRecordId = Guid.NewGuid();
        var fileLocator = new EntityFileLocator(schemaName, fileRecordId);

        IFile file = userConnection.CreateFile(fileLocator);
        file.Name = Path.GetFileName(sourcePath);
        file.SetAttribute(parentColumnName, parentRecordId);
        file.Save();

        // A FileStream keeps a large file off the heap — do not read it into a byte[] first
        using (var stream = File.OpenRead(sourcePath)) {
            file.Write(stream, FileWriteOptions.SinglePart);
        }

        return fileRecordId;
    }
}

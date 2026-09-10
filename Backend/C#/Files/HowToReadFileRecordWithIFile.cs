using System;
using System.IO;
using Terrasoft.Core;
using Terrasoft.File;
using Terrasoft.File.Abstractions;

/// <summary>
/// Demonstrates how to read a file using the IFile abstraction and EntityFileLocator.
/// Use this approach when files may be stored outside the database (S3, filesystem, Azure Blob, etc.).
/// EntityFileLocator resolves the correct physical storage provider transparently — your code does not
/// need to know where the file actually lives.
/// For files stored directly in the entity Data column, use FetchFromDB + GetStreamValue instead —
/// see HowToReadFileRecordWithESQ.
/// </summary>
class HowToReadFileRecordWithIFile {

    // Read file content by schema name and file record Id — storage-location agnostic
    public byte[] ReadFileByLocator(UserConnection userConnection, string schemaName, Guid fileId) {
        // EntityFileLocator identifies a file by its parent schema name and record Id
        var locator = new EntityFileLocator(schemaName, fileId);

        // GetFile resolves the correct storage provider (DB, S3, filesystem, etc.)
        IFile file = userConnection.GetFile(locator);

        // Read() returns a stream regardless of where the file is physically stored
        using (var stream = file.Read()) {
            using (var memoryStream = new MemoryStream()) {
                stream.CopyTo(memoryStream);
                return memoryStream.ToArray();
            }
        }
    }
}

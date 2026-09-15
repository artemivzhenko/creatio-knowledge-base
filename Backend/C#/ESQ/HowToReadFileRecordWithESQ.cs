using System;
using System.IO;
using Terrasoft.Core;
using Terrasoft.Core.Entities;

/// <summary>
/// Demonstrates how to read a file record (binary content) from the database using the Entity model.
/// Use this approach when the file binary data is stored directly in the entity's Data column (default Creatio setup).
/// Suitable for standard file details: LeadFile, ContactFile, AccountFile, etc.
/// For files stored via the file storage abstraction (S3, filesystem), use EntityFileLocator instead — see HowToReadFileRecordWithIFile.
/// </summary>
class HowToReadFileRecordWithESQ {

    // Read file name and binary content by the file record Id
    public (string fileName, byte[] fileData) ReadFileById(UserConnection userConnection, Guid fileId) {
        var entity = userConnection.EntitySchemaManager
            .GetInstanceByName("LeadFile")
            .CreateEntity(userConnection);

        if (!entity.FetchFromDB(fileId)) {
            // File record not found — handle accordingly
            return (string.Empty, Array.Empty<byte>());
        }

        string fileName = entity.GetTypedColumnValue<string>("Name");

        // GetStreamValue opens the binary content stored in the Data column as a stream
        using (var fileStream = entity.GetStreamValue("Data")) {
            if (fileStream == null) {
                // Column exists but contains no binary data
                return (fileName, Array.Empty<byte>());
            }
            using (var memoryStream = new MemoryStream()) {
                fileStream.CopyTo(memoryStream);
                return (fileName, memoryStream.ToArray());
            }
        }
    }
}

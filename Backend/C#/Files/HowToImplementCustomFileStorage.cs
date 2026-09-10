using System;
using System.IO;
using System.Threading.Tasks;
using Terrasoft.File.Abstractions;
using Terrasoft.File.Abstractions.Metadata;

/// <summary>
/// Demonstrates how to store file binaries outside the database by implementing IFileContentStorage.
/// Use this when attachments must live on a file share, on S3, or anywhere the database
/// should not grow — the metadata row stays in Creatio, only the bytes move.
///
/// Nothing above this layer changes: IFile.Write(), Copy(), Move() and Delete() keep
/// working exactly as in HowToCreateAndWriteFileWithIFile, because they resolve the
/// storage from configuration rather than naming one.
///
/// REGISTER IT OR NOTHING HAPPENS. After deploying the class, add it to the
/// SysFileContentStorage lookup in Creatio. Without that row the platform never resolves
/// the implementation, files keep going to the default storage, and there is no error to
/// tell you why — the most common way this task is "finished" without working.
///
/// THE APPEND TRAP. WriteAsync is called ONCE per SinglePart write, but ONCE PER CHUNK for
/// a chunked upload — which is what the UI does for large files. Opening the target with
/// OpenOrCreate on every chunk rewrites from offset zero, so a large file silently ends up
/// holding only its last chunk. Append for anything that is not SinglePart. The same
/// distinction is visible from the other side in HowToOverrideFileUploader.
///
/// FileMetadata must be cast to EntityFileMetadata to reach EntitySchemaName and RecordId.
/// Build the storage key from those plus the name: the name alone is not unique, and two
/// records with an attachment called "contract.pdf" would otherwise overwrite each other.
///
/// Every method is on the hot path of an upload request. Keep them streaming — never buffer
/// a file into memory — and let exceptions propagate: swallowing one leaves a metadata row
/// pointing at content that does not exist.
/// </summary>
public class FsFileBlobStorage : IFileContentStorage {

    private const string BaseFsPath = @"C:\FsStore\";

    // Key layout: <schema>\<recordId>_<name> — schema and record id keep the key unique
    private static string GetPath(FileMetadata fileMetadata) {
        var md = (EntityFileMetadata)fileMetadata;
        string key = $@"{md.EntitySchemaName}\{md.RecordId}_{fileMetadata.Name}";
        return Path.Combine(BaseFsPath, key);
    }

    // The target directory may not exist yet — every write path has to ensure it
    private static void EnsureDirectory(string filePath) {
        string dirPath = Path.GetDirectoryName(filePath);
        if (!Directory.Exists(dirPath)) {
            Directory.CreateDirectory(dirPath);
        }
    }

    public Task<Stream> ReadAsync(IFileContentReadContext context) {
        string filePath = GetPath(context.FileMetadata);
        Stream stream = File.OpenRead(filePath);
        return Task.FromResult(stream);
    }

    public async Task WriteAsync(IFileContentWriteContext context) {
        string filePath = GetPath(context.FileMetadata);

        // Append for chunked uploads, OpenOrCreate only for a single-part write.
        // Getting this backwards truncates large files to their last chunk.
        FileMode flags = context.WriteOptions != FileWriteOptions.SinglePart
            ? FileMode.Append
            : FileMode.OpenOrCreate;

        EnsureDirectory(filePath);

        using (var fileStream = File.Open(filePath, flags)) {
            await context.Stream.CopyToAsync(fileStream);
        }
    }

    public Task DeleteAsync(IFileContentDeleteContext context) {
        string filePath = GetPath(context.FileMetadata);
        File.Delete(filePath);
        return Task.CompletedTask;
    }

    public Task CopyAsync(IFileContentCopyMoveContext context) {
        string src = GetPath(context.SourceMetadata);
        string dst = GetPath(context.TargetMetadata);

        // The target lives under the TARGET schema's folder, which may not exist yet —
        // a copy across entity types is exactly when that happens
        EnsureDirectory(dst);
        File.Copy(src, dst);
        return Task.CompletedTask;
    }

    public Task MoveAsync(IFileContentCopyMoveContext context) {
        string src = GetPath(context.SourceMetadata);
        string dst = GetPath(context.TargetMetadata);

        EnsureDirectory(dst);
        File.Move(src, dst);
        return Task.CompletedTask;
    }
}

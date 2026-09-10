using System;
using System.IO;
using Terrasoft.Core;
using Terrasoft.Core.Entities;
using Terrasoft.Core.Factories;

/// <summary>
/// Demonstrates how to run custom code whenever a user attaches a file, by overriding the
/// platform FileUploader.
///
/// WHY NOT AN EVENT LISTENER. A listener on the file entity fires on the DB write, which for
/// a CHUNKED upload happens once per chunk — so a naive listener parses a half-written file
/// several times. FileUploader sees the upload as the platform does and tells you which
/// chunk you are on.
///
/// THE PATTERN:
///   [Override]                      register this class in place of the platform one
///   class : FileUploader            inherit the platform uploader
///   override UploadFile(IFileUploadConfig)   call base first, then your logic
///
/// [Override] (Terrasoft.Core.Factories) replaces the existing factory binding. Only one
/// package may override a given class - if two do, the last one installed wins and the other
/// silently stops running. Check before overriding a class that a base product already
/// customises.
///
/// IFileUploadConfig carries what you need to decide:
///   EntitySchemaName   which file entity is being written - ALWAYS check it first, this
///                      uploader is called for every attachment in the system
///   FileId             primary key of the file record
///   IsChunkedUpload    true for a large file split into chunks
///   IsLastChunk        true on the final chunk; the file is complete only then
///
/// So the rule is: act when (!IsChunkedUpload) or (IsChunkedUpload &amp;&amp; IsLastChunk).
///
/// Call base.UploadFile first - it performs the actual write. Custom logic before it runs
/// against a file that does not exist yet.
///
/// Keep the work short, or hand it to a background task: this code runs inside the upload
/// request, and a slow parser makes the attachment dialog hang. See HowToRunBackgroundTask.
/// </summary>
namespace Terrasoft.Configuration.FileUpload
{

	[Override]
	public class UsrFileUploader : FileUploader
	{

		private const string TargetSchemaName = "UsrApplicationFile";

		protected UserConnection UserConn { get; set; }

		private UsrApplicationFileHelper _helper;
		protected UsrApplicationFileHelper Helper => _helper ??
			(_helper = ClassFactory.Get<UsrApplicationFileHelper>(
				new ConstructorArgument("userConnection", UserConn)));

		public UsrFileUploader(UserConnection userConnection) : base(userConnection) {
			UserConn = userConnection;
		}

		public override void UploadFile(IFileUploadConfig fileUploadInfoConfig) {

			// 1. Let the platform write the file first.
			base.UploadFile(fileUploadInfoConfig);

			// 2. This uploader runs for EVERY attachment - narrow it immediately.
			if (fileUploadInfoConfig.EntitySchemaName != TargetSchemaName) {
				return;
			}

			// 3. Act once, on a complete file.
			bool isComplete = !fileUploadInfoConfig.IsChunkedUpload
				|| (fileUploadInfoConfig.IsChunkedUpload && fileUploadInfoConfig.IsLastChunk);
			if (!isComplete) {
				return;
			}

			var fileEntity = GetFileEntity(fileUploadInfoConfig.FileId);
			if (fileEntity == null) {
				return;
			}
			ProcessFile(fileEntity);
		}

		protected virtual void ProcessFile(Entity entity) {
			var fileName = entity.GetTypedColumnValue<string>("Name");
			var extension = Path.GetExtension(fileName);

			if (extension.Equals(".xlsx", StringComparison.OrdinalIgnoreCase)
				|| extension.Equals(".xls", StringComparison.OrdinalIgnoreCase)) {
				Helper.ReadFileDataToApplication(entity);
				return;
			}

			// Anything else: mark the parent record accordingly.
			var applicationId = entity.GetTypedColumnValue<Guid>("UsrApplicationId");
			Helper.SetUnsupportedFormat(applicationId);
		}

		/// <summary>
		/// Reads the file record. UseAdminRights = false keeps the query under the rights of
		/// the user who uploaded the file - see HowToControlAdminRights.
		/// </summary>
		protected Entity GetFileEntity(Guid fileId) {
			var esq = new EntitySchemaQuery(UserConn.EntitySchemaManager, TargetSchemaName);
			esq.PrimaryQueryColumn.IsAlwaysSelect = true;
			esq.UseAdminRights = false;
			esq.AddColumn("Name");
			esq.AddColumn("UsrApplication");
			return esq.GetEntity(UserConn, fileId);
		}
	}

	public class UsrApplicationFileHelper
	{
		protected UserConnection UserConnection { get; set; }

		public UsrApplicationFileHelper(UserConnection userConnection) {
			UserConnection = userConnection;
		}

		public virtual void ReadFileDataToApplication(Entity fileEntity) { }

		public virtual void SetUnsupportedFormat(Guid applicationId) { }
	}
}

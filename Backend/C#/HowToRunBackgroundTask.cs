using System;
using Terrasoft.Core;
using Terrasoft.Core.Entities;
using Terrasoft.Core.Entities.Events;
using Terrasoft.Core.Factories;
using Terrasoft.Core.Tasks;

/// <summary>
/// Demonstrates the IBackgroundTask pattern — the lightweight way to move work off the
/// request thread without going through the Quartz scheduler.
///
/// WHEN TO USE WHICH:
///   IBackgroundTask (this file)      fire-and-forget work triggered by an event or a
///                                    service call; no schedule, no persistence, no retry.
///   AppScheduler.ScheduleImmediateJob  one-shot job that survives an app restart and is
///                                    visible in the Quartz job store.
///                                    See HowToScheduleImmediateJob.
///   Quartz cron job                  recurring work. See HowToCreateQuartzScheduledJob.
///
/// THE CONTRACT. The handler class implements two interfaces:
///   IBackgroundTask&lt;TParams&gt;  — supplies Run(TParams parameters)
///   IUserConnectionRequired      — lets the platform inject a UserConnection
/// The parameter type must be a simple serialisable POCO: it is handed to a new thread,
/// so pass IDs and primitives, never an Entity or a UserConnection.
///
/// Start it with:
///   Terrasoft.Core.Tasks.Task.StartNewWithUserConnection&lt;THandler, TParams&gt;(parameters);
///
/// The handler needs a PARAMETERLESS constructor as well as the UserConnection one — the
/// platform instantiates it itself and then assigns the connection.
///
/// CAUTION. The task runs outside the request and outside any transaction of the caller.
/// A task started from a Before-event (OnInserting/OnUpdating) can therefore read the record
/// in its pre-save state or not find it at all — start background work from After-events
/// (OnInserted/OnUpdated) instead. Exceptions inside the task do not surface to the caller,
/// so log them or they vanish silently.
/// </summary>
namespace Terrasoft.Configuration
{

	// 1. The parameter object: plain data only.
	public class FileProcessingParams
	{
		public Guid FileId { get; set; }
		public string FileSchemaName { get; set; }
		public string TargetSchemaName { get; set; }
		public string TargetColumnName { get; set; }
		public Guid TargetId { get; set; }
	}

	// 2. The handler.
	public class FileProcessingTask : IBackgroundTask<FileProcessingParams>, IUserConnectionRequired
	{

		// Assigned by the platform because of IUserConnectionRequired.
		protected UserConnection UserConnection { get; set; }

		// Required by the platform.
		public FileProcessingTask() { }

		// Used when the class is resolved through the factory in ordinary code.
		public FileProcessingTask(UserConnection userConnection) {
			UserConnection = userConnection;
		}

		// The entry point of the background work.
		public void Run(FileProcessingParams parameters) {
			try {
				var esq = new Terrasoft.Core.Entities.EntitySchemaQuery(
					UserConnection.EntitySchemaManager, parameters.FileSchemaName);
				esq.AddColumn("Name");
				var fileEntity = esq.GetEntity(UserConnection, parameters.FileId);

				if (fileEntity == null) {
					return;
				}
				// ... long-running work: call an external API, parse a file, etc.
			} catch (Exception ex) {
				// Nothing above catches this - log it or it is lost.
				UserConnection.AppConnection.SystemUserConnection
					.CurrentUser.ConnectionInfo.ToString();
				throw;
			}
		}
	}

	// 3. Starting it from an After-event, where the record is already committed.
	[EntityEventListener(SchemaName = "CallFile")]
	public class CallFileEventListener : BaseEntityEventListener
	{
		public override void OnInserted(object sender, EntityAfterEventArgs e) {
			base.OnInserted(sender, e);
			var entity = (Entity)sender;

			var fileName = entity.GetTypedColumnValue<string>("Name");
			if (!fileName.EndsWith(".mp3", StringComparison.OrdinalIgnoreCase)) {
				return;
			}

			// Hands the parameters to a new thread with its own UserConnection.
			Terrasoft.Core.Tasks.Task.StartNewWithUserConnection<FileProcessingTask, FileProcessingParams>(
				new FileProcessingParams {
					FileId = entity.PrimaryColumnValue,
					FileSchemaName = "CallFile",
					TargetSchemaName = "Call",
					TargetColumnName = "UsrTranscription",
					TargetId = entity.GetTypedColumnValue<Guid>("CallId")
				});
		}
	}

	// 4. Starting it from a service or a helper, where the factory supplies the connection.
	public class TranscriptionHelper
	{
		private readonly UserConnection _userConnection;

		public TranscriptionHelper(UserConnection userConnection) {
			_userConnection = userConnection;
		}

		public virtual string TransferAudio(Guid callId, string url) {
			if (string.IsNullOrEmpty(url)) {
				return "Call URL not found";
			}
			Terrasoft.Core.Tasks.Task.StartNewWithUserConnection<FileProcessingTask, FileProcessingParams>(
				new FileProcessingParams {
					TargetSchemaName = "Call",
					TargetColumnName = "UsrTranscription",
					TargetId = callId
				});

			// Returns immediately; the caller does not wait for the work.
			return "OK";
		}
	}
}

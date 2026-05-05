using System;
using System.Collections.Generic;
using global::Common.Logging;
using Terrasoft.Core;
using Terrasoft.Core.Configuration;
using Terrasoft.Core.Scheduler;

/// <summary>
/// Demonstrates how to offload heavy work to a background job that fires immediately (once)
/// using AppScheduler.ScheduleImmediateJob&lt;T&gt;.
/// Use this pattern in web service endpoints or event listeners when the operation is too slow
/// to complete in the request thread: accept the call, schedule the job, return immediately.
/// Each call must supply a unique jobName — use a Guid suffix to avoid conflicts.
/// isSystemUser: true runs the job with admin rights, bypassing record-level security.
/// The job class must implement IJobExecutor. See HowToCreateQuartzScheduledJob for the
/// IJobExecutor implementation template and for recurring cron-based scheduling.
/// </summary>
class HowToScheduleImmediateJob {

    private const string WorkspaceName = "Default";

    // Schedule a one-shot background job with parameters
    public void OffloadToBackground(UserConnection userConnection, Guid recordId, string newValue) {
        // Each invocation needs a unique name — reusing an existing name may skip or collide
        string jobName = "MyOneTimeJob_" + Guid.NewGuid();

        // Pass everything the job needs; values must be serializable (string, Guid, int, bool, List)
        var jobParams = new Dictionary<string, object> {
            { "RecordId",  recordId },
            { "NewValue",  newValue },
            { "ContactId", userConnection.CurrentUser.ContactId }
        };

        // Read the job user from SysSettings so it can be changed without redeployment
        string jobUserName = SysSettings.GetValue(userConnection, "MyJobUserName", "Supervisor");

        // Fires once, immediately, in a separate thread managed by the Quartz scheduler
        AppScheduler.ScheduleImmediateJob<MyBackgroundJob>(
            jobName:       jobName,
            workspaceName: WorkspaceName,
            userName:      jobUserName,
            parameters:    jobParams,
            isSystemUser:  true);  // true = job ignores userName and runs as SystemUser
    }
}

// Job class executed by AppScheduler — receives the parameters dictionary
class MyBackgroundJob : IJobExecutor {

    private static readonly ILog _log = LogManager.GetLogger("MyBackgroundJob");

    public void Execute(UserConnection userConnection, IDictionary<string, object> parameters) {
        _log.InfoFormat("[MyBackgroundJob] START");

        // Read parameters passed from ScheduleImmediateJob
        var recordId  = parameters.ContainsKey("RecordId")  ? (Guid)parameters["RecordId"]    : Guid.Empty;
        var newValue  = parameters.ContainsKey("NewValue")   ? parameters["NewValue"] as string : null;
        var contactId = parameters.ContainsKey("ContactId")  ? (Guid)parameters["ContactId"]   : Guid.Empty;

        // custom logic: ESQ, Insert, Update, ProcessExecutor, etc.

        _log.InfoFormat("[MyBackgroundJob] END. recordId={0}", recordId);
    }
}

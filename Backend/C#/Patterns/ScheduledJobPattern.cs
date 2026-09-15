using System;
using System.Collections.Generic;
using global::Common.Logging;
using Terrasoft.Core;
using Terrasoft.Core.Configuration;
using Terrasoft.Core.Scheduler;

/// <summary>
/// Pattern: type-safe parameters for Quartz jobs.
///
/// Problem: AppScheduler passes parameters as Dictionary&lt;string, object&gt;.
/// Using magic strings for key names causes silent bugs — a typo in the
/// scheduler and a typo in the job go undetected until runtime.
///
/// Solution: pair each IJobExecutor with a dedicated parameters class that:
///   1. Declares all key names as private constants (single source of truth).
///   2. Exposes typed properties instead of raw object values.
///   3. Provides ToDictionary() for the scheduling side.
///   4. Provides FromDictionary() for the execution side.
///
/// Both sides use the same class, so renaming a parameter is a single change
/// that the compiler validates everywhere.
/// </summary>
namespace Terrasoft.Configuration {

    // ── Job parameters class ──────────────────────────────────────────────────

    public class MyJobParameters {

        // Key names — private so callers cannot use magic strings accidentally
        private const string RecordIdKey    = "RecordId";
        private const string NewValueKey    = "NewValue";
        private const string InitiatorIdKey = "InitiatorId";

        // Typed properties — no casting at call sites
        public Guid   RecordId    { get; set; }
        public string NewValue    { get; set; }
        public Guid   InitiatorId { get; set; }

        // Scheduling side: convert to the dictionary AppScheduler expects
        public Dictionary<string, object> ToDictionary() {
            return new Dictionary<string, object> {
                { RecordIdKey,    RecordId    },
                { NewValueKey,    NewValue    },
                { InitiatorIdKey, InitiatorId }
            };
        }

        // Execution side: reconstruct from the dictionary the job receives
        public static MyJobParameters FromDictionary(IDictionary<string, object> dict) {
            return new MyJobParameters {
                RecordId    = dict.ContainsKey(RecordIdKey)    ? (Guid)dict[RecordIdKey]      : Guid.Empty,
                NewValue    = dict.ContainsKey(NewValueKey)    ? dict[NewValueKey] as string   : null,
                InitiatorId = dict.ContainsKey(InitiatorIdKey) ? (Guid)dict[InitiatorIdKey]   : Guid.Empty
            };
        }
    }

    // ── Job implementation ────────────────────────────────────────────────────

    public class MyJob : IJobExecutor {

        private static readonly ILog _log = LogManager.GetLogger("MyJob");

        public void Execute(UserConnection userConnection,
            IDictionary<string, object> parameters) {

            // One line to get a fully typed, validated parameters object
            MyJobParameters p = MyJobParameters.FromDictionary(parameters);

            _log.InfoFormat("[MyJob] START recordId={0}", p.RecordId);

            // use p.RecordId, p.NewValue, p.InitiatorId — no casts, no magic strings

            _log.InfoFormat("[MyJob] END recordId={0}", p.RecordId);
        }
    }

    // ── Scheduler helper ──────────────────────────────────────────────────────

    public static class MyJobScheduler {

        private const string JobGroup     = "MyJobs";
        private const string WorkspaceName = "Default";

        // One-time immediate job — offload from web request / event listener
        public static void RunNow(UserConnection userConnection, MyJobParameters jobParams) {
            string jobName     = "MyJob_" + Guid.NewGuid();
            string jobUserName = SysSettings.GetValue(userConnection, "MyJobUserName", "Supervisor");

            AppScheduler.ScheduleImmediateJob<MyJob>(
                jobName:       jobName,
                workspaceName: WorkspaceName,
                userName:      jobUserName,
                parameters:    jobParams.ToDictionary(),
                isSystemUser:  true);
        }

        // Recurring job — every night at midnight
        public static void ScheduleNightly(UserConnection userConnection, MyJobParameters jobParams) {
            string jobName = "MyJob_Nightly";

            AppScheduler.RemoveJob(jobName, JobGroup);

            AppScheduler.CreateAndScheduleJob<MyJob>(
                jobName:                    jobName,
                jobGroupName:               JobGroup,
                userConnection:             userConnection,
                parameters:                 jobParams.ToDictionary(),
                isCronTrigger:              true,
                timeZoneId:                 TimeZoneInfo.Utc.Id,
                isMisFireInstructionFireNow: true,
                startDateTime:              DateTime.UtcNow,
                endDateTime:                DateTime.MaxValue,
                cronExpression:             "0 0 0 * * ?",  // every day at midnight UTC
                priority:                   5);
        }
    }
}

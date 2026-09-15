using System;
using System.Collections.Generic;
using global::Common.Logging;
using Terrasoft.Core;
using Terrasoft.Core.Applications;
using Terrasoft.Core.Scheduler;
using Terrasoft.Web.Common;

/// <summary>
/// Demonstrates how to create and schedule a recurring background job using AppScheduler (Quartz).
/// Three components are required:
///   1. AppEventListener — registers the job when the application starts.
///   2. Scheduler helper — defines the CRON schedule and calls AppScheduler.CreateAndScheduleJob.
///   3. Job class (IJobExecutor) — contains the business logic executed on each trigger.
/// Jobs are stored in the QRTZ_* database tables and survive application restarts.
/// Common CRON expressions:
///   "0 0/1 * * * ?"       every 1 minute
///   "0 0 0 * * ?"         every day at midnight
///   "0 0 9 ? * MON-FRI"   every weekday at 9 AM
/// </summary>

// ── 1. AppEventListener ───────────────────────────────────────────────────────
namespace Terrasoft.Configuration {

    public class MyJobAppEventListener : AppEventListenerBase {

        public override void OnAppStart(AppEventContext context) {
            base.OnAppStart(context);
            var appConnection = context.Application["AppConnection"] as AppConnection;
            var userConnection = appConnection?.SystemUserConnection;
            if (userConnection == null) return;

            MyScheduledJobScheduler.ScheduleEveryMinute(userConnection);
        }
    }

    // ── 2. Scheduler helper ───────────────────────────────────────────────────
    public static class MyScheduledJobScheduler {

        public const string JobGroup = "CustomJobs";
        public const string JobName  = "MyScheduledJob_EveryMinute";

        public static void ScheduleEveryMinute(UserConnection userConnection) {
            // Remove previous instance so schedule changes take effect on restart
            AppScheduler.RemoveJob(JobName, JobGroup);

            var parameters = new Dictionary<string, object> {
                { "Note", "Scheduled to run every minute" }
            };

            AppScheduler.CreateAndScheduleJob<MyScheduledJob>(
                jobName:                      JobName,
                jobGroupName:                 JobGroup,
                userConnection:               userConnection,
                parameters:                   parameters,
                isCronTrigger:                true,
                timeZoneId:                   TimeZoneInfo.Utc.Id,
                isMisFireInstructionFireNow:   true,
                startDateTime:                DateTime.UtcNow,
                endDateTime:                  DateTime.MaxValue,
                cronExpression:               "0 0/1 * * * ?",
                priority:                     5
            );
        }

        public static void Unschedule() {
            AppScheduler.RemoveJob(JobName, JobGroup);
        }
    }

    // ── 3. Job class ──────────────────────────────────────────────────────────
    public sealed class MyScheduledJob : IJobExecutor {

        private static readonly ILog _log = LogManager.GetLogger("MyScheduledJob");

        // Execute is called automatically by AppScheduler on each trigger
        public void Execute(UserConnection userConnection, IDictionary<string, object> parameters) {
            _log.InfoFormat("[MyScheduledJob] START at {0}", DateTime.UtcNow.ToString("O"));

            // userConnection is SystemUserConnection — use it for ESQ, Insert, Update, etc.
            // parameters contains the dictionary passed in CreateAndScheduleJob

            _log.InfoFormat("[MyScheduledJob] END at {0}", DateTime.UtcNow.ToString("O"));
        }
    }
}

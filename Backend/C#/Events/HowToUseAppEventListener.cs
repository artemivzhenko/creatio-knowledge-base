using Terrasoft.Core;
using Terrasoft.Core.Applications;
using Terrasoft.Web.Common;

/// <summary>
/// Demonstrates how to hook into the Creatio application lifecycle using AppEventListenerBase.
/// OnAppStart runs once when the application starts — use it to register schedulers,
/// warm up caches, or initialise static services.
/// OnAppEnd runs when the application shuts down — use it to flush queues or release resources.
/// The listener is discovered automatically by the platform; no registration step is required.
/// Use SystemUserConnection from AppEventContext — the regular user session does not exist at startup.
/// </summary>
namespace Terrasoft.Configuration {

    public class MyAppEventListener : AppEventListenerBase {

        public override void OnAppStart(AppEventContext context) {
            base.OnAppStart(context);

            var userConnection = GetSystemUserConnection(context);
            if (userConnection == null) {
                return;
            }

            // Initialise services, register scheduled jobs, warm up caches, etc.
        }

        public override void OnAppEnd(AppEventContext context) {
            base.OnAppEnd(context);

            // Release resources, flush pending queues, etc.
        }

        // Helper: extract SystemUserConnection from AppEventContext
        private UserConnection GetSystemUserConnection(AppEventContext context) {
            var appConnection = context.Application["AppConnection"] as AppConnection;
            return appConnection?.SystemUserConnection;
        }
    }
}

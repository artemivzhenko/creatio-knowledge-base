using Terrasoft.Core;
using Terrasoft.Core.Applications;

/// <summary>
/// Demonstrates when and how to use SystemUserConnection in Creatio.
/// SystemUserConnection runs with administrator rights — it bypasses row-level and column-level
/// security checks, sees all records regardless of the current user's access rights.
/// Use it in background jobs, AppEventListeners, and integration logic that must operate
/// independently of any specific logged-in user.
/// Never use it in UI-facing code where user permissions must be respected.
///
/// Two patterns:
///   1. Obtain a standalone SystemUserConnection from AppConnection — for background work.
///   2. Temporarily elevate an existing UserConnection via CreateSystemSecurityContext()
///      — for a single operation inside user-facing code that needs elevated access.
/// </summary>
class HowToUseSystemUserConnection {

    // 1. Get a standalone SystemUserConnection from AppConnection
    //    Typical usage: AppEventListener, Quartz jobs, integration handlers
    public void UseStandaloneSystemConnection(AppConnection appConnection) {
        UserConnection systemUserConnection = appConnection.SystemUserConnection;

        // All operations performed with this connection have full admin rights
        var schema = systemUserConnection.EntitySchemaManager.GetInstanceByName("Contact");
        var entity = schema.CreateEntity(systemUserConnection);
        // ...
    }

    // 2. Temporarily elevate an existing UserConnection with CreateSystemSecurityContext()
    //    The same UserConnection object is used; security is elevated only for the duration
    //    of the using block and then automatically restored to the original level
    public void ElevateForOneOperation(UserConnection userConnection) {
        using (userConnection.CreateSystemSecurityContext()) {
            // Inside this block, userConnection behaves as SystemUserConnection
            var schema = userConnection.EntitySchemaManager.GetInstanceByName("SysAdminUnit");
            var entity = schema.CreateEntity(userConnection);
            // perform privileged read/write
        }
        // After the using block, the original security level is restored
    }

    // 3. Get SystemUserConnection inside an AppEventListener (OnAppStart context)
    //    AppEventContext does not have a regular user session — always use SystemUserConnection
    public UserConnection GetFromAppEventContext(AppEventContext context) {
        var appConnection = context.Application["AppConnection"] as AppConnection;
        return appConnection?.SystemUserConnection;
    }
}

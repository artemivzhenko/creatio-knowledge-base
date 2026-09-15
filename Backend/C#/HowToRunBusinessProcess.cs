using System.Collections.Generic;
using Terrasoft.Core;
using Terrasoft.Core.Process;

/// <summary>
/// Demonstrates how to start a business process programmatically using ProcessExecutor.
/// Use this approach when custom backend logic (event listener, web service, script task)
/// needs to trigger a process as part of its execution flow.
/// Input parameters are passed as a string dictionary — keys must match the process parameter code names,
/// values must be string representations (e.g. Guid.ToString(), int.ToString()).
/// The process runs asynchronously by default; the returned ProcessDescriptor holds the process instance Id.
/// </summary>
class HowToRunBusinessProcess {

    public ProcessDescriptor StartProcess(UserConnection userConnection) {
        // ProcessExecutor is accessed through the process engine on the current connection
        IProcessExecutor processExecutor = userConnection.ProcessEngine.ProcessExecutor;

        // Input parameters — keys are process parameter code names, values are string representations
        var inputParameters = new Dictionary<string, string> {
            { "ContactId", "00000000-0000-0000-0000-000000000000" },
            { "SendEmail",  "true" }
        };

        // The schema name is the internal code of the process as set in the process designer Properties
        string processSchemaName = "MyProcessSchemaName";

        // Execute returns a ProcessDescriptor with the new process instance Id
        ProcessDescriptor descriptor = processExecutor.Execute(processSchemaName, inputParameters);

        return descriptor;
    }
}
